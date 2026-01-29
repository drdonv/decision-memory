# Decision Memory

Decision Memory captures the reasoning behind team decisions and keeps it
searchable. It turns messy discussions (Slack threads, PR comments, meeting
notes) into clean "Decision Cards" that include the decision, rationale,
alternatives, risks, and citations back to the original text.

## What you get
- Decision cards, not raw chatter
- Citations for every claim to reduce hallucinations
- A lightweight pipeline to ingest text and extract decisions

## Typical consumer flow
1. Provide a source (text + optional metadata).
2. Extract decision cards.
3. Search decisions later by asking "Why did we choose X?"

## Quick start (prototype CLI)
This repo includes a simple extractor that reads a text file and emits decision
cards as JSON.

1) Install dependencies:
```
pip install -r requirements.txt
```

2) Create `keys.env` with:
```
OPENAI_API_KEY=...
DATABASE_URL=postgresql://localhost:5432/decision_memory
```

3) Run extraction:
```
python -m src.extract \
  --file path/to/source.txt \
  --source-type slack \
  --source-title "Slack #infra thread" \
  --source-url "https://example.com" \
  --author "Jane Doe"
```

The command prints an array of decision cards to stdout.

## Status
This is an early prototype focused on extraction and storage. The interface is
intentionally minimal while the decision-capture workflow is validated.
