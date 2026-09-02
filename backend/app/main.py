import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Loads backend/.env for local dev. In production (Railway) env vars are injected
# directly, and this file won't exist - load_dotenv() silently no-ops rather than
# erroring, and never overrides an already-set env var.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.db import count_queries_for_ip, log_query  # noqa: E402
from app.rag_chain import answer_question  # noqa: E402

app = FastAPI(title="Baobab Freight Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://baobab-freight.vercel.app"],
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

RATE_LIMIT_PER_IP = 10


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class ChatRequest(BaseModel):
    question: str


class SourceResponse(BaseModel):
    document: str
    section: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    remaining_questions: int


def _get_client_ip(request: Request) -> str:
    """The IP is used for rate limiting, so it must be derived server-side - a
    client-supplied ip_address in the request body would let anyone bypass the
    limit by just sending a different value each time. Railway (and most PaaS
    hosts) put the app behind a proxy, so the real client IP arrives via
    X-Forwarded-For, not request.client.host (which would be the proxy's own
    address)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.post("/chat")
def chat(request: Request, body: ChatRequest) -> ChatResponse:
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")

    ip_address = _get_client_ip(request)

    used = count_queries_for_ip(ip_address)
    if used >= RATE_LIMIT_PER_IP:
        raise HTTPException(
            status_code=429,
            detail=f"You've used all {RATE_LIMIT_PER_IP} questions for this session.",
        )

    start = time.perf_counter()
    try:
        result = answer_question(body.question)
    except Exception:
        latency_ms = int((time.perf_counter() - start) * 1000)
        log_query(
            question=body.question,
            answer=None,
            chunk_ids=[],
            ip_address=ip_address,
            latency_ms=latency_ms,
        )
        raise HTTPException(status_code=502, detail="Failed to generate an answer. Please try again.")

    latency_ms = int((time.perf_counter() - start) * 1000)
    log_query(
        question=body.question,
        answer=result.answer,
        chunk_ids=result.chunk_ids,
        ip_address=ip_address,
        latency_ms=latency_ms,
    )

    return ChatResponse(
        answer=result.answer,
        sources=[SourceResponse(document=s.document, section=s.section) for s in result.sources],
        remaining_questions=RATE_LIMIT_PER_IP - (used + 1),
    )
