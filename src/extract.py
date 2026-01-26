import sys
from openai import OpenAI
import json

def extract(fpath: str):
    with open(fpath, "r", encoding="utf-8") as f:
        text = f.read()
    chunks = chunk_text(text)
    for chunk in chunks:
        candidates = detect_candidates(chunk)
        for candidate in candidates:
            decision = extract_decision(candidate, chunk)
            print(decision)

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
        input=prompt + "\n\n" + chunk
    )
    try:
        data = json.loads(response.output_text)
    except json.JSONDecodeError:
        return []
    return data["candidates"]

# Turn a candidate into a decision card that we can add to a db
def extract_decision(candidate: dict, chunk: str) -> dict:
    client = OpenAI()
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
        model='gpt-4o-mini',
        input=prompt
    )
    try:
        data = json.loads(response.output_text)
    except json.JSONDecodeError:
        return {}
    return data

if __name__ == "__main__":
    extract(sys.argv[1])