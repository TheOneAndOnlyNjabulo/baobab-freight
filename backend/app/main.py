from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Loads backend/.env for local dev. In production (Railway) env vars are injected
# directly, and this file won't exist - load_dotenv() silently no-ops rather than
# erroring, and never overrides an already-set env var.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.rag_chain import answer_question  # noqa: E402

app = FastAPI(title="Baobab Freight Assistant API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class ChatRequest(BaseModel):
    question: str
    ip_address: str


class SourceResponse(BaseModel):
    document: str
    section: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]


@app.post("/chat")
def chat(request: ChatRequest) -> ChatResponse:
    if not request.question.strip():
        raise HTTPException(status_code=422, detail="question must not be empty")

    try:
        result = answer_question(request.question)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to generate an answer. Please try again.")

    return ChatResponse(
        answer=result.answer,
        sources=[SourceResponse(document=s.document, section=s.section) for s in result.sources],
    )
