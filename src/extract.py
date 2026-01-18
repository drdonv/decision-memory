import sys
from openai import OpenAI
import json

def extract(fpath: str):
    with open(fpath, "r") as f:
        text = f.read()
    chunks = chunk_text(text)
    for chunk in chunks:
        print(chunk)

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
    client = OpenAI()

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
        model='gpt-4o-mini',
        input=prompt + chunk
    )
    try:
        data = json.loads(response.output_text)
    except json.JSONDecodeError:
        return []
    return data["candidates"]


if __name__ == "__main__":
    extract(sys.argv[1])