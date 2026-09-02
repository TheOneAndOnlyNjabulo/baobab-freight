"""
RAG chain: retrieval -> citation-aware prompt template -> Gemini generation.

Uses LangChain (ChatPromptTemplate + ChatGoogleGenerativeAI) for the prompt/
generation half of the chain; retrieval itself reuses retrieval.py directly
rather than going through a LangChain VectorStore wrapper, since we already
have a working, tested retrieve() function talking to Pinecone/Gemini
directly (step 4).
"""

import os
from dataclasses import dataclass

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from app.retrieval import RetrievedChunk, retrieve

GENERATION_MODEL = "gemini-3.5-flash-lite"

SYSTEM_PROMPT = """You are the Baobab Freight Assistant, a support chatbot for Baobab Freight & \
Logistics, a fictional South African freight and logistics company. Answer the user's question \
using ONLY the context below, drawn from Baobab's internal policy and compliance documents.

Rules:
- Base your answer strictly on the provided context. Do not use outside knowledge, and do not \
assume anything the context does not state.
- When you state a specific fact (a number, deadline, rate, permit, or requirement), name the \
document it comes from, e.g. "(See the Delivery SLA Policy - General Terms document.)"
- If the context does not contain enough information to answer the question, say so explicitly \
and clearly. Do not guess or fabricate an answer.
- Be concise and direct."""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)

_llm: ChatGoogleGenerativeAI | None = None
_chain = None


@dataclass
class Source:
    document: str
    section: str


@dataclass
class RagResult:
    answer: str
    sources: list[Source]
    chunk_ids: list[str]


def _format_context(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(
        f"[Document: {c.source_document}, Section {c.section}]\n{c.text}" for c in chunks
    )


def _dedupe_sources(chunks: list[RetrievedChunk]) -> list[Source]:
    seen: set[tuple[str, str]] = set()
    sources: list[Source] = []
    for c in chunks:
        key = (c.source_document, c.section)
        if key not in seen:
            seen.add(key)
            sources.append(Source(document=c.source_document, section=c.section))
    return sources


def _get_chain():
    global _llm, _chain
    if _chain is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        _llm = ChatGoogleGenerativeAI(model=GENERATION_MODEL, google_api_key=api_key)
        _chain = _prompt | _llm | StrOutputParser()
    return _chain


def answer_question(question: str, top_k: int = 5) -> RagResult:
    chunks = retrieve(question, top_k=top_k)
    chain = _get_chain()
    answer = chain.invoke({"context": _format_context(chunks), "question": question})
    return RagResult(
        answer=answer,
        sources=_dedupe_sources(chunks),
        chunk_ids=[c.id for c in chunks],
    )
