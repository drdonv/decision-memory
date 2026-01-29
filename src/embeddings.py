from __future__ import annotations

from openai import OpenAI

from src.config import settings


def embed_text(text: str) -> list[float]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text,
    )
    return list(response.data[0].embedding)
