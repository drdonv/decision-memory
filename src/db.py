from __future__ import annotations

import json
from typing import Any

import psycopg

from src.config import settings


def get_conn() -> psycopg.Connection:
    return psycopg.connect(settings.database_url)


def init_db() -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id SERIAL PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_title TEXT,
                source_url TEXT,
                author TEXT,
                created_at TIMESTAMP,
                raw_text TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS source_chunks (
                id SERIAL PRIMARY KEY,
                source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                chunk_hash TEXT NOT NULL,
                embedding JSONB
            );
            CREATE TABLE IF NOT EXISTS decisions (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                decision TEXT NOT NULL,
                context TEXT NOT NULL,
                rationale TEXT NOT NULL,
                alternatives_json JSONB NOT NULL,
                risks_json JSONB NOT NULL,
                owner TEXT,
                decided_at TIMESTAMP,
                confidence DOUBLE PRECISION NOT NULL,
                embedding JSONB
            );
            CREATE TABLE IF NOT EXISTS decision_citations (
                id SERIAL PRIMARY KEY,
                decision_id INTEGER NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
                source_chunk_id INTEGER NOT NULL REFERENCES source_chunks(id) ON DELETE CASCADE,
                quote TEXT NOT NULL,
                start_char INTEGER,
                end_char INTEGER
            );
            """
        )
        conn.commit()


def insert_source(
    source_type: str,
    raw_text: str,
    source_title: str | None = None,
    source_url: str | None = None,
    author: str | None = None,
    created_at: str | None = None,
) -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sources (source_type, source_title, source_url, author, created_at, raw_text)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (source_type, source_title, source_url, author, created_at, raw_text),
        )
        source_id = cur.fetchone()[0]
        conn.commit()
        return source_id


def insert_chunk(
    source_id: int,
    chunk_index: int,
    chunk_text: str,
    chunk_hash: str,
    embedding: list[float] | None = None,
) -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO source_chunks (source_id, chunk_index, chunk_text, chunk_hash, embedding)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (source_id, chunk_index, chunk_text, chunk_hash, json.dumps(embedding)),
        )
        chunk_id = cur.fetchone()[0]
        conn.commit()
        return chunk_id


def insert_decision(
    decision: dict[str, Any],
    embedding: list[float] | None = None,
) -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO decisions (
                title, decision, context, rationale, alternatives_json, risks_json,
                owner, decided_at, confidence, embedding
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                decision.get("title", ""),
                decision.get("decision", ""),
                decision.get("context", ""),
                decision.get("rationale", ""),
                json.dumps(decision.get("alternatives", [])),
                json.dumps(decision.get("risks", [])),
                decision.get("owner"),
                decision.get("decided_at"),
                decision.get("confidence", 0.0),
                json.dumps(embedding),
            ),
        )
        decision_id = cur.fetchone()[0]
        conn.commit()
        return decision_id


def insert_citation(
    decision_id: int,
    source_chunk_id: int,
    quote: str,
    start_char: int | None = None,
    end_char: int | None = None,
) -> int:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO decision_citations (decision_id, source_chunk_id, quote, start_char, end_char)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (decision_id, source_chunk_id, quote, start_char, end_char),
        )
        citation_id = cur.fetchone()[0]
        conn.commit()
        return citation_id
