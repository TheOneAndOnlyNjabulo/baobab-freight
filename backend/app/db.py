"""
Neon query log. Every /chat attempt is logged here - including failed ones (answer
NULL, chunk_ids empty) - so a failed request still counts as a used attempt rather
than giving a free retry, and so failures are visible in the same table used for
rate limiting (step 8) and the future eval/monitoring project (see CLAUDE.md notes).

The connection string already points at a Neon pooled endpoint (the "-pooler"
hostname, PgBouncer-backed), so opening a fresh connection per request is the
correct, intended usage - no extra client-side pool needed on top of it.
"""

import os

import psycopg


def _connect() -> psycopg.Connection:
    database_url = os.environ.get("NEON_DATABASE_URL")
    if not database_url:
        raise RuntimeError("NEON_DATABASE_URL is not set")
    return psycopg.connect(database_url)


def log_query(
    question: str,
    answer: str | None,
    chunk_ids: list[str],
    ip_address: str,
    latency_ms: int,
) -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into queries (question, answer, chunk_ids, ip_address, latency_ms)
                values (%s, %s, %s, %s, %s)
                """,
                (question, answer, chunk_ids, ip_address, latency_ms),
            )
