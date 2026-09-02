"""
Standalone retrieval function: query in, top-k chunks out.

Embeds the query with the same model and dimension used at ingestion time
(see embedding_config.py) but with task_type="RETRIEVAL_QUERY" instead of
"RETRIEVAL_DOCUMENT" - Gemini's embedding model optimizes the vector differently
depending on which side of the retrieval it's told it's on, so using the wrong
task_type here would silently degrade match quality without raising any error.
"""

import os
from dataclasses import dataclass

from google import genai
from google.genai import types
from pinecone import Pinecone

from app.embedding_config import EMBED_DIMENSION, EMBED_MODEL

_gemini_client: genai.Client | None = None
_pinecone_index = None


@dataclass
class RetrievedChunk:
    id: str
    source_document: str
    section: str
    text: str
    score: float


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        api_key = os.environ.get("PINECONE_API_KEY")
        index_name = os.environ.get("PINECONE_INDEX_NAME")
        if not api_key or not index_name:
            raise RuntimeError("PINECONE_API_KEY / PINECONE_INDEX_NAME are not set")
        _pinecone_index = Pinecone(api_key=api_key).Index(index_name)
    return _pinecone_index


def retrieve(query: str, top_k: int = 5) -> list[RetrievedChunk]:
    """Embed `query` and return the top_k most similar chunks from Pinecone,
    ranked by descending similarity score."""
    if not query or not query.strip():
        raise ValueError("query must be non-empty")

    client = _get_gemini_client()
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=[query],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBED_DIMENSION,
        ),
    )
    query_vector = response.embeddings[0].values

    index = _get_pinecone_index()
    result = index.query(vector=query_vector, top_k=top_k, include_metadata=True)

    return [
        RetrievedChunk(
            id=match["id"],
            source_document=match["metadata"]["source_document"],
            section=match["metadata"]["section"],
            text=match["metadata"]["text"],
            score=match["score"],
        )
        for match in result["matches"]
    ]
