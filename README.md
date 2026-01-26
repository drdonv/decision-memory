# Decision Memory — Memory Bank (for builders + LLM copilots)

## What is this?
Decision Memory captures and preserves a team's *decision reasoning* from messy discussions (Slack threads, PR comments, meeting notes). It extracts "Decision Cards" with:
- the decision made
- why it was made (rationale)
- alternatives considered
- risks/tradeoffs accepted
- who/when (if available)
- citations to source snippets (to prevent hallucination + allow verification)

This is NOT model training. The model stays fixed. We improve by:
- ingesting more source text
- better extraction prompts + schemas
- better retrieval (embeddings)
- better confidence + citation handling

## Product principles
1. **Truth over fluency**: if uncertain, say so and lower confidence.
2. **Every claim cites sources**: show the exact snippet(s) used.
3. **Atomic unit = decision** (not messages).
4. **No magic strategy**: we extract what humans already decided.

## User flows
### Flow A: Ingest + Extract
User pastes text (or uploads) and tags it:
- source_type: slack | github_pr | meeting_notes | notion
- source_url: optional
- timestamp: optional
System:
- chunks text
- runs decision detection + extraction
- stores sources + decisions + links between them

### Flow B: Ask "Why did we choose X?"
User asks a question.
System:
- embeds the question
- retrieves top-k relevant decisions
- returns a synthesized answer referencing 1–3 decision cards + citations

## Data model (MVP)
We store 3 things:
1) Raw source chunks
2) Extracted decision cards
3) Vector embeddings for retrieval

### Tables (SQLite for MVP, Postgres for market-ready)

#### sources
- id (pk)
- source_type (text)
- source_title (text, optional)  # e.g., "Slack #infra thread"
- source_url (text, optional)
- author (text, optional)
- created_at (datetime, optional)
- raw_text (text)

#### source_chunks
- id (pk)
- source_id (fk)
- chunk_index (int)
- chunk_text (text)
- chunk_hash (text)             # stable dedupe
- embedding (blob/text)         # optional depending on embedding approach

#### decisions
- id (pk)
- title (text)
- decision (text)               # one-sentence canonical decision
- context (text)                # what problem
- rationale (text)              # why
- alternatives_json (text)      # JSON array
- risks_json (text)             # JSON array
- owner (text, optional)
- decided_at (datetime, optional)
- confidence (float 0..1)
- embedding (blob/text)         # embed decision+context+rationale

#### decision_citations
- id (pk)
- decision_id (fk)
- source_chunk_id (fk)
- quote (text)                  # short direct snippet used
- start_char (int, optional)
- end_char (int, optional)

> MVP simplification: you can skip source_chunks and store a single raw_text per source + quotes as citations.
> Better: chunking helps retrieval + keeps token sizes manageable.

## Retrieval strategy (MVP)
Embed and search over **decisions** first (fast, high-signal).
- Query embedding vs decision embedding
- Return top 5 decisions
- Then show citations (quotes + source url)

Optional improvement:
- If confidence low or no good match, also search source_chunks and propose "possible decisions" or show relevant raw snippets.

## Extraction strategy (2-step, reduces hallucinations)
### Step 1: Detect decision candidates (cheap)
Prompt LLM: identify segments that contain decisions (or decision-like statements).
Return spans or quoted lines.

### Step 2: Extract structured decision card (strict JSON)
Give only the candidate text + nearby context.
Return a JSON object with fields + citations.

### Confidence heuristic
Initialize confidence from:
- explicit decision verbs ("we decided", "let's go with", "ship X")
- presence of rationale
- presence of alternatives/tradeoffs
- number of supporting citations
Scale 0.2..0.95 (avoid 1.0)

## Prompts (copy/paste)

### System prompt (shared)
You are an information extraction engine. You must not invent facts.
Only use the provided text. If info is missing, output null or [].
Always include citations as direct short quotes from the text.

### Prompt: Decision Candidate Detection
Input: chunk_text
Output JSON:
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
- Keep quotes <= 25 words each
- Only include if there is clear evidence
- If none, return empty list

### Prompt: Decision Card Extraction
Input: candidate quote + surrounding text + metadata
Output JSON:
{
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
    {"quote": "...", "note": "supports decision"},
    {"quote": "...", "note": "supports rationale"}
  ]
}

Rules:
- decision must be one sentence
- alternatives/risks can be []
- citations must be verbatim quotes from provided text
- if not enough support, lower confidence and leave fields empty rather than guessing

### Prompt: Q&A / Synthesis (optional)
Input: user_question + top decisions (with citations)
Output:
- 2–4 sentence answer
- bullet list of relevant decision cards
- include citations (quotes)

Rule: If uncertain, say "I may be missing context" and point to citations.

## API endpoints (suggested)
- POST /sources
  body: {source_type, source_title?, source_url?, raw_text, created_at?, author?}
- POST /sources/{id}/extract
  kicks off extraction for that source, stores decisions
- GET /decisions?query=...
  returns list of decisions (search by embeddings or keyword)
- GET /decisions/{id}
  returns full decision + citations + source metadata

## Minimal UI
- Page 1: Paste source text + metadata + "Extract decisions"
- Page 2: List of Decision Cards (title, confidence, decided_at)
- Search box: "Why did we choose X?"
- Decision detail: decision, rationale, tradeoffs, citations with link to source_url

## Demo script (what to show a founder)
1. Paste a realistic Slack/PR thread (preloaded example in /examples).
2. Click "Extract"
3. Show 3 decision cards created with confidence + citations.
4. Ask: "Why did we choose Redis over DynamoDB?"
5. Show answer + the decision card + citations.

## Guardrails (important)
- Never output a decision without at least 1 supporting citation quote.
- Never fabricate dates/owners.
- Keep quotes short; do not leak entire private threads.
- Offer "needs more context" if confidence low.

## Repo structure (suggested)
- app/
  - main.py (FastAPI)
  - db.py
  - models.py
  - extract.py
  - retrieve.py
  - prompts.py
  - templates/ (if using server-rendered pages)
- examples/
  - slack_thread_1.txt
  - pr_discussion_1.txt
- README.md
- MEMORY_BANK.md (this file)

## Tech stack notes (2026 market-ready)
- Backend: FastAPI (keep)
- DB: SQLite for MVP, Postgres for market-ready
- Retrieval: pgvector when moving to Postgres
- Embeddings: use a reputable API provider; keep swappable interfaces
- UI: minimal, demo-friendly frontend (server-rendered or minimal React)
- Ops: background jobs + basic observability once real users exist

## Next improvements (NOT for MVP)
- Slack/GitHub integrations
- Conflict detection ("this decision contradicts that one")
- Decision timeline + evolution
- Multi-agent "Decision Debate" validator
- Advanced infra hardening (queues, auth, SSO)
