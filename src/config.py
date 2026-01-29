from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    database_url: str
    openai_api_key: str | None
    openai_chat_model: str
    openai_embedding_model: str


def _load_env() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / "keys.env")
    load_dotenv(repo_root / ".env")


def load_settings() -> Settings:
    _load_env()
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql://localhost:5432/decision_memory",
        ),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        openai_embedding_model=os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        ),
    )


settings = load_settings()
