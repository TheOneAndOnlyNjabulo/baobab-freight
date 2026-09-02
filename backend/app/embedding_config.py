"""Shared between the ingestion script and the retrieval function - both must
agree on model and dimension, or queries silently land in the wrong vector space."""

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIMENSION = 3072
