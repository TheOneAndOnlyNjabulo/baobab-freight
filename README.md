# Baobab Freight Assistant

A citation-grounded RAG chatbot that answers questions over a fictional South African freight & logistics
company's internal policy and compliance documents — customs, delivery SLAs, dangerous goods, claims, cross-border
documentation, and more. Every answer cites the specific document and section it came from, and the assistant
explicitly says when it doesn't know something rather than guessing.

**Live demo:** https://baobab-freight.vercel.app/

> **⚠️ Baobab Freight & Logistics is entirely fictional.** The company, its policies, routes, and every document
> in [`docs/`](./docs) were invented for this project to demonstrate RAG engineering. None of it describes a real
> business, and nothing in it is real freight, customs, or legal advice.

---

## Why this exists

This is a portfolio project built to demonstrate practical RAG engineering — not a toy demo. The interesting parts
are the retrieval quality, the citation grounding, and the explicit refusal to hallucinate when the answer isn't
in the documents. The chat UI is deliberately simple so those parts stay the focus.

## Architecture

```mermaid
flowchart LR
    subgraph Frontend["Next.js — Vercel"]
        UI[Chat UI]
    end

    subgraph Backend["FastAPI — Railway"]
        API["/chat endpoint"]
        RAG[RAG Chain<br/>LangChain]
        RateLimit[Rate limiter]
    end

    subgraph External["External services"]
        Gemini["Gemini API<br/>(embeddings + generation)"]
        Pinecone[(Pinecone<br/>vector store)]
        Neon[(Neon Postgres<br/>query log)]
    end

    UI -- "POST /chat" --> API
    API --> RateLimit
    RateLimit -- "count(*) by IP" --> Neon
    API --> RAG
    RAG -- "embed query" --> Gemini
    RAG -- "top-k similarity search" --> Pinecone
    RAG -- "citation-aware prompt" --> Gemini
    API -- "log question/answer/chunks" --> Neon
    API -- "answer + sources" --> UI

    Docs[("docs/*.md<br/>29 policy documents")] -. "offline ingestion:<br/>chunk → embed → upsert" .-> Pinecone
```

**Request flow:** the frontend calls `POST /chat` with just `{question}` — the backend derives the caller's IP
itself server-side (`X-Forwarded-For`, since a client-supplied IP would make rate limiting trivially bypassable).
It checks the IP's usage count against Neon, embeds the question with Gemini (`task_type=RETRIEVAL_QUERY`),
searches Pinecone for the top-5 most similar document chunks, and — only if the top result clears a similarity
threshold — builds a citation-aware prompt and calls Gemini to generate an answer grounded strictly in those
chunks. The question, answer, retrieved chunk IDs, IP, and latency are logged to Neon regardless of outcome
(including failures), and the answer with its source citations is returned to the frontend.

**Ingestion is offline**, not part of the live request path: a standalone script chunks every document in `docs/`
along its own section boundaries (never a fixed character count — see [`backend/scripts/ingest.py`](./backend/scripts/ingest.py)
for why that matters), embeds each chunk (`task_type=RETRIEVAL_DOCUMENT`), and upserts it to Pinecone with
metadata (`source_document`, `section`, and the raw chunk text) so a retrieved chunk can be cited and returned
directly, with no second lookup.

## Key engineering decisions

A few things worth calling out, since they're the actual substance of this project:

- **No silent truncation.** The Gemini Developer API has no way to make it *reject* oversized input — it silently
  truncates instead (confirmed empirically by sending ~19,000 tokens and getting back a normal-looking embedding
  with zero error). The ingestion script never trusts the API's limits: every chunk's real token count is verified
  locally before it's ever sent, and ingestion aborts loudly, naming the exact offending chunk, if anything is
  still too large after being split on paragraph/sentence boundaries.
- **Structure-aware chunking, not fixed-size.** Every document uses numbered `## N. Heading` sections deliberately,
  so chunks split on real semantic boundaries (section → paragraph → sentence, in that order of preference) —
  never mid-sentence, never an arbitrary character cutoff.
- **A confidence threshold gates generation, not just the prompt.** The system prompt alone tells the model to say
  "I don't know" — but retrieval always returns its top-k nearest chunks regardless of relevance, so a prompt-only
  approach still attaches irrelevant citations to an "I don't know" answer. The threshold (calibrated empirically
  against real similarity scores across in-scope, borderline, and out-of-scope test questions) short-circuits
  before the LLM is even called when nothing retrieved is actually relevant — saving a generation call and keeping
  citations honest.
- **Rate limiting can't be client-supplied.** An earlier draft of the API had the frontend send its own IP address
  in the request body — trivially bypassable by anyone who opened devtools. The backend derives it server-side
  instead.
- **The eval harness caught bugs in itself, not just the system.** Two of the eval set's expected answers were
  wrong when first written (one used a fact from the wrong section of a document, one had two keywords that could
  never both match under the scorer's AND logic) — both were found by actually reading the flagged failures rather
  than assuming the system was at fault, and fixed. See [`backend/eval/eval_results.md`](./backend/eval/eval_results.md).

## Evaluation results

29 questions, one covering every document in `docs/`, each checked against two independent metrics: whether the
expected document was retrieved in the top 5 results, and whether the generated answer contains the expected
key facts.

| Metric | Result |
|---|---|
| Retrieval hit rate (expected doc in top-5) | **29/29 (100%)** |
| Average rank when hit | 1.2 |
| Full keyword match rate | **29/29 (100%)** |
| Average keyword coverage | 100% |

Full per-question breakdown: [`backend/eval/eval_results.md`](./backend/eval/eval_results.md). Re-run it yourself
with `cd backend && python scripts/eval.py` (needs the same env vars as the app — see Setup below).

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (TypeScript) + Tailwind + shadcn/ui, deployed on Vercel |
| Backend | Python + FastAPI, deployed on Railway |
| Orchestration | LangChain — citation-aware prompt template + generation chain |
| Generation | Gemini (`gemini-3.5-flash-lite`) |
| Embeddings | Gemini (`gemini-embedding-001`) |
| Vector store | Pinecone (serverless) |
| Relational DB | Neon Postgres — query log + rate limiting (no Redis) |

## Project structure

```
docs/               29 fictional policy/compliance documents (the corpus)
frontend/           Next.js chat UI
backend/
  app/               FastAPI app: /chat endpoint, retrieval, RAG chain, DB
  scripts/           CLI tools: ingest.py, eval.py, test_retrieval.py, test_rag_chain.py
  eval/              Evaluation set + results
```

## Setup

Requires: Node.js 20+, Python 3.12+, and API keys/accounts for Gemini, Pinecone, and Neon.

**Backend**
```bash
cd backend
python -m venv .venv
.venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

Create `backend/.env`:
```
GEMINI_API_KEY=...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=baobab-freight
NEON_DATABASE_URL=postgresql://...
```

Create the query log table in Neon:
```sql
create table queries (
  id uuid primary key default gen_random_uuid(),
  question text not null,
  answer text,
  chunk_ids text[],
  ip_address text not null,
  latency_ms integer,
  created_at timestamptz not null default now()
);
```

Then run ingestion once to populate Pinecone:
```bash
python scripts/ingest.py
```

Start the API:
```bash
uvicorn app.main:app --reload --port 8123
```

**Frontend**
```bash
cd frontend
npm install
```

Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8123
```

```bash
npm run dev
```

## API

`POST /chat`

```json
// Request
{ "question": "What VAT rate applies to imports into South Africa?" }

// Response
{
  "answer": "Import VAT is levied at the standard rate of 15% ...",
  "sources": [{ "document": "Customs and VAT Compliance Guide", "section": "1" }],
  "remaining_questions": 9
}
```

10 questions per IP (derived server-side, not client-supplied), tracked via the Neon query log rather than a
separate cache layer. Returns 429 once exhausted, 502 on generation failure, 422 on an empty question.
