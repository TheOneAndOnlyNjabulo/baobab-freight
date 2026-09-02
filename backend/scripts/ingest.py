"""
Offline ingestion pipeline: reads docs/*.md, chunks each document by its numbered
sections, embeds each chunk with Gemini, and upserts the vectors to Pinecone.

Run manually via CLI:
    cd backend
    .venv/Scripts/python.exe scripts/ingest.py

This is NOT part of the live request path (see CLAUDE.md step 3) - it's a standalone
script you re-run whenever docs/ changes.

A note on why this script is more careful than it looks: the Gemini Developer API
(a bare API key, not Vertex) has no way to ask it to reject oversized input - the
`auto_truncate` config flag only exists in Vertex/Enterprise mode. Empirically, an
input of ~19,000 tokens sent to embed_content() on the Developer API succeeds with
no error and returns a normal-looking embedding - meaning the model silently embedded
a truncated version of the text with zero signal that anything was cut. So this script
never trusts the API to catch an oversized chunk; every chunk's real token count is
checked locally with count_tokens() BEFORE it is sent, and ingestion aborts loudly if
a chunk is still too big after splitting.
"""

import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pinecone import Pinecone, ServerlessSpec

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
DOCS_DIR = REPO_ROOT / "docs"

sys.path.insert(0, str(BACKEND_DIR))
from app.embedding_config import EMBED_DIMENSION, EMBED_MODEL  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")

# gemini-embedding-001's documented max input is 2048 tokens. Target well under
# that so a chunk still has room even if the real tokenizer disagrees slightly
# with a rough estimate, and hard-fail if anything ever gets close to the real max.
MAX_INPUT_TOKENS = 2048
CHUNK_TARGET_TOKENS = 1200

EMBED_BATCH_SIZE = 20
PINECONE_CLOUD = "aws"
PINECONE_REGION = "us-east-1"

SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.+)$")
TITLE_RE = re.compile(r"^#\s+(.+)$")


@dataclass
class Chunk:
    doc_slug: str
    source_document: str
    section: str
    text: str


def parse_document(path: Path) -> tuple[str, list[tuple[str, str, str]]]:
    """Returns (title, sections) where sections is [(number, heading, body)]."""
    lines = path.read_text(encoding="utf-8").splitlines()

    title_match = TITLE_RE.match(lines[0]) if lines else None
    if not title_match:
        raise ValueError(f"{path.name}: expected an H1 title on the first line")
    title = title_match.group(1).strip()

    sections: list[tuple[str, str, str]] = []
    current_num: str | None = None
    current_heading: str | None = None
    current_body: list[str] = []

    def flush():
        if current_num is not None:
            sections.append((current_num, current_heading, "\n".join(current_body).strip()))

    for line in lines[1:]:
        match = SECTION_RE.match(line)
        if match:
            flush()
            current_num, current_heading = match.group(1), match.group(2).strip()
            current_body = []
        elif current_num is not None:
            current_body.append(line)
    flush()

    if not sections:
        raise ValueError(f"{path.name}: no '## N. Heading' sections found")

    return title, sections


def split_on_boundary(text: str, pattern: re.Pattern) -> list[str]:
    pieces = [p.strip() for p in pattern.split(text) if p.strip()]
    return pieces


PARAGRAPH_RE = re.compile(r"\n\s*\n")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def pack_pieces(pieces: list[str], max_tokens: int, count_tokens) -> list[str]:
    """Greedily join consecutive pieces into groups, each under max_tokens, without
    ever reordering or dropping a piece. Never merges across a piece that alone
    exceeds max_tokens - that piece is returned on its own (caller decides whether
    to split it further)."""
    groups: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for piece in pieces:
        piece_tokens = count_tokens(piece)
        if current and current_tokens + piece_tokens > max_tokens:
            groups.append("\n\n".join(current))
            current, current_tokens = [], 0
        current.append(piece)
        current_tokens += piece_tokens

    if current:
        groups.append("\n\n".join(current))

    return groups


def chunk_section_body(body: str, max_tokens: int, count_tokens) -> list[str]:
    """Split a section body into pieces that each fit under max_tokens, always
    breaking on paragraph or sentence boundaries - never mid-sentence, mid-word."""
    if count_tokens(body) <= max_tokens:
        return [body]

    paragraphs = split_on_boundary(body, PARAGRAPH_RE)
    groups = pack_pieces(paragraphs, max_tokens, count_tokens)

    # A single paragraph might itself be over the limit (e.g. one long bullet
    # list with no blank lines inside it) - fall back to sentence packing for
    # any group that's still too big.
    final: list[str] = []
    for group in groups:
        if count_tokens(group) <= max_tokens:
            final.append(group)
            continue
        sentences = split_on_boundary(group, SENTENCE_RE)
        final.extend(pack_pieces(sentences, max_tokens, count_tokens))

    return final


def build_chunks(client: genai.Client) -> list[Chunk]:
    def count_tokens(text: str) -> int:
        return client.models.count_tokens(model=EMBED_MODEL, contents=text).total_tokens

    doc_paths = sorted(DOCS_DIR.glob("*.md"))
    if not doc_paths:
        raise RuntimeError(f"No .md files found in {DOCS_DIR}")

    chunks: list[Chunk] = []
    for path in doc_paths:
        title, sections = parse_document(path)
        doc_slug = path.stem

        for number, heading, body in sections:
            full_section_text = f"{number}. {heading}\n\n{body}".strip()
            pieces = chunk_section_body(full_section_text, CHUNK_TARGET_TOKENS, count_tokens)

            if len(pieces) == 1:
                chunks.append(Chunk(doc_slug, title, number, pieces[0]))
            else:
                for i, piece in enumerate(pieces, start=1):
                    chunks.append(Chunk(doc_slug, title, f"{number}.{i}", piece))

    # Hard defense-in-depth check: verify every chunk is under the model's real
    # max BEFORE any embedding call is made. Since the Developer API silently
    # truncates instead of erroring (confirmed empirically - see module docstring),
    # this is the only thing standing between "content is silently cut" and
    # ingestion failing loudly and pointing at the exact offending chunk.
    oversized = [
        (c.doc_slug, c.section, count_tokens(c.text))
        for c in chunks
        if count_tokens(c.text) > MAX_INPUT_TOKENS
    ]
    if oversized:
        details = "\n".join(f"  - {slug} section {sec}: {tok} tokens" for slug, sec, tok in oversized)
        raise RuntimeError(
            f"{len(oversized)} chunk(s) exceed the {MAX_INPUT_TOKENS}-token embedding "
            f"limit even after splitting - refusing to embed, since the API would "
            f"silently truncate them:\n{details}"
        )

    return chunks


def embed_with_retry(client: genai.Client, texts: list[str], max_attempts: int = 5) -> list[list[float]]:
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.embed_content(
                model=EMBED_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=EMBED_DIMENSION,
                ),
            )
            embeddings = [e.values for e in response.embeddings]
            if len(embeddings) != len(texts):
                raise RuntimeError(
                    f"Embedding API returned {len(embeddings)} vectors for "
                    f"{len(texts)} inputs - refusing to upsert misaligned data."
                )
            return embeddings
        except errors.APIError as e:
            is_rate_limited = getattr(e, "code", None) == 429
            if is_rate_limited and attempt < max_attempts:
                wait = 2**attempt
                print(f"  rate limited, retrying in {wait}s (attempt {attempt}/{max_attempts})")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("unreachable")


def ensure_index(pc: Pinecone, index_name: str) -> None:
    existing = {idx["name"] for idx in pc.list_indexes()}
    if index_name in existing:
        return
    print(f"Creating Pinecone index '{index_name}' (dimension={EMBED_DIMENSION}, metric=cosine)...")
    pc.create_index(
        name=index_name,
        dimension=EMBED_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
    )
    while not pc.describe_index(index_name).status["ready"]:
        time.sleep(1)


def main() -> None:
    gemini_key = os.environ.get("GEMINI_API_KEY")
    pinecone_key = os.environ.get("PINECONE_API_KEY")
    index_name = os.environ.get("PINECONE_INDEX_NAME")
    if not gemini_key or not pinecone_key or not index_name:
        print(
            "Missing GEMINI_API_KEY, PINECONE_API_KEY, or PINECONE_INDEX_NAME "
            f"in {BACKEND_DIR / '.env'}",
            file=sys.stderr,
        )
        sys.exit(1)

    client = genai.Client(api_key=gemini_key)

    print(f"Parsing and chunking documents from {DOCS_DIR}...")
    chunks = build_chunks(client)
    print(f"Built {len(chunks)} chunks from {len(set(c.doc_slug for c in chunks))} documents.")

    pc = Pinecone(api_key=pinecone_key)
    ensure_index(pc, index_name)
    index = pc.Index(index_name)

    total_upserted = 0
    for batch_start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + EMBED_BATCH_SIZE]
        print(f"Embedding chunks {batch_start + 1}-{batch_start + len(batch)} of {len(chunks)}...")
        vectors = embed_with_retry(client, [c.text for c in batch])

        upsert_payload = [
            {
                "id": f"{c.doc_slug}::{c.section}",
                "values": vector,
                "metadata": {
                    "source_document": c.source_document,
                    "section": c.section,
                    "text": c.text,
                },
            }
            for c, vector in zip(batch, vectors)
        ]
        index.upsert(vectors=upsert_payload)
        total_upserted += len(upsert_payload)

    print(f"Done. Upserted {total_upserted} vectors to Pinecone index '{index_name}'.")


if __name__ == "__main__":
    main()
