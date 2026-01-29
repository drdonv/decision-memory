import argparse
import hashlib
import json
import sys

from openai import OpenAI

from src.config import settings
from src.db import (
    init_db,
    insert_chunk,
    insert_citation,
    insert_decision,
    insert_source,
)
from src.embeddings import embed_text

def extract(
    fpath: str,
    source_type: str,
    source_title: str | None,
    source_url: str | None,
    author: str | None,
) -> list[dict]:
    with open(fpath, "r", encoding="utf-8") as f:
        text = f.read()

    init_db()
    source_id = insert_source(
        source_type=source_type,
        source_title=source_title,
        source_url=source_url,
        author=author,
        raw_text=text,
    )

    results: list[dict] = []
    chunks = chunk_text(text)
    for index, chunk in enumerate(chunks):
        chunk_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
        chunk_id = insert_chunk(
            source_id=source_id,
            chunk_index=index,
            chunk_text=chunk,
            chunk_hash=chunk_hash,
        )
        candidates = detect_candidates(chunk)
        for candidate in candidates:
            decision = extract_decision(candidate, chunk)
            if not decision:
                continue
            decision_text = " ".join(
                [
                    decision.get("decision", ""),
                    decision.get("context", ""),
                    decision.get("rationale", ""),
                ]
            ).strip()
            embedding = embed_text(decision_text) if decision_text else None
            decision_id = insert_decision(decision, embedding=embedding)
            for citation in decision.get("citations", []):
                insert_citation(
                    decision_id=decision_id,
                    source_chunk_id=chunk_id,
                    quote=citation.get("quote", ""),
                )
            results.append(decision)

    return results

# Improve chunking with chunk overlapping, paragraph accumulation (till the 2500 char limit)

def chunk_text(text: str) -> list[str]:
    # Split on paragraphs and at a max char size of 2500 chars
    paragraphs = text.split("\n\n")
    chunks = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        while len(paragraph) > 2500:
            chunk = paragraph[:2500]
            chunks.append(chunk)
            paragraph = paragraph[2500:]

        chunks.append(paragraph)

    return chunks

# Detect parts of text that are potential decision candidates
def detect_candidates(chunk: str) -> list[dict]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    client = OpenAI(api_key=settings.openai_api_key)

    prompt = """
    You are an agent designed to identify decision-like statements.

    A candidate must include at least ONE of:
    1) Explicit decision language (e.g., "we decided", "we'll go with", "ship X")
    2) Alternatives comparison (e.g., "X vs Y", "we rejected Y because...")
    3) Tradeoff/risk acceptance tied to a choice (risk alone is NOT enough)

    Return JSON exactly in this shape:
    {
    "candidates": [
        {
        "candidate_id": "c1",
        "quote": "direct quote that indicates a decision",
        "reason": "why this looks like a decision",
        "supporting_quotes": ["...", "..."]
        }
    ]
    }

    Rules:
    - Quotes must be verbatim from the text
    - Keep quotes <= 25 words
    - If none, return in this shape:
        {
        "candidates": []
        }

    Text:
    """.strip()

    response = client.responses.create(
        model=settings.openai_chat_model,
        input=prompt + "\n\n" + chunk,
    )
    try:
        data = json.loads(response.output_text)
    except json.JSONDecodeError:
        return []
    return data.get("candidates", [])

# Turn a candidate into a decision card that we can add to a db
def extract_decision(candidate: dict, chunk: str) -> dict:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    client = OpenAI(api_key=settings.openai_api_key)
    EXTRACTION_PROMPT = """
    You are an information extraction engine. You must not invent facts.
    Only use the provided text. If info is missing, output null or [].
    Always include citations as direct short quotes from the text.

    Candidate quote:
    {candidate_quote}

    Context:
    {context_text}

    Return JSON exactly in this shape:
    {{
    "title": "...",
    "decision": "...",
    "context": "...",
    "rationale": "...",
    "alternatives": ["...", "..."],
    "risks": ["...", "..."],
    "owner": null,
    "decided_at": null,
    "confidence": 0.0,
    "citations": [
        {{"quote": "...", "note": "supports decision"}},
        {{"quote": "...", "note": "supports rationale"}}
    ]
    }}

    Rules:
    - decision must be one sentence
    - alternatives/risks can be []
    - citations must be verbatim quotes from provided text
    - if not enough support, lower confidence and leave fields empty rather than guessing
    """

    prompt = EXTRACTION_PROMPT.format(
        candidate_quote=candidate["quote"],
        context_text=chunk
    )

    response = client.responses.create(
        model=settings.openai_chat_model,
        input=prompt,
    )
    try:
        data = json.loads(response.output_text)
    except json.JSONDecodeError:
        return {}
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract decision cards from a text file.")
    parser.add_argument("--file", required=True, help="Path to the source text file.")
    parser.add_argument(
        "--source-type",
        required=True,
        help="Source type (slack, github_pr, meeting_notes, notion).",
    )
    parser.add_argument("--source-title", help="Optional source title.")
    parser.add_argument("--source-url", help="Optional source URL.")
    parser.add_argument("--author", help="Optional author.")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    decisions = extract(
        fpath=args.file,
        source_type=args.source_type,
        source_title=args.source_title,
        source_url=args.source_url,
        author=args.author,
    )
    print(json.dumps(decisions, indent=2))