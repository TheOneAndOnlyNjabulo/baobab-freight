"""
Evaluation harness: runs every case in eval/eval_set.py through retrieval and the
full RAG chain, scores retrieval accuracy and answer keyword coverage, and writes
a markdown report to eval/eval_results.md (linked from the README, step 15).

Run manually via CLI:
    cd backend
    .venv/Scripts/python.exe scripts/eval.py

Two independent metrics, on purpose:
  - Retrieval hit: did the expected document appear anywhere in the top-5 chunks
    retrieved for this question? This isolates retrieval quality from generation
    quality - a wrong answer with a retrieval hit means the prompt/model is the
    problem, not the vector search.
  - Keyword coverage: what fraction of the expected keywords appear in the
    generated answer. Deliberately simple substring matching, not semantic
    similarity or an LLM judge - keeps the eval script's own correctness legible
    without introducing a second model's judgment as a dependency.
"""

import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from app.rag_chain import answer_question  # noqa: E402
from app.retrieval import retrieve  # noqa: E402
from eval.eval_set import EVAL_SET, EvalCase  # noqa: E402

TOP_K = 5
RESULTS_PATH = BACKEND_DIR / "eval" / "eval_results.md"


@dataclass
class CaseResult:
    case: EvalCase
    retrieval_hit: bool
    retrieval_rank: int | None
    answer: str
    matched_keywords: list[str]
    missed_keywords: list[str]

    @property
    def keyword_coverage(self) -> float:
        total = len(self.case.expected_keywords)
        return len(self.matched_keywords) / total if total else 1.0

    @property
    def full_keyword_match(self) -> bool:
        return len(self.missed_keywords) == 0


def run_case(case: EvalCase) -> CaseResult:
    chunks = retrieve(case.question, top_k=TOP_K)
    retrieval_rank = next(
        (i for i, c in enumerate(chunks, start=1) if c.source_document == case.expected_document),
        None,
    )

    result = answer_question(case.question, top_k=TOP_K)
    answer_lower = result.answer.lower()
    matched = [kw for kw in case.expected_keywords if kw.lower() in answer_lower]
    missed = [kw for kw in case.expected_keywords if kw not in matched]

    return CaseResult(
        case=case,
        retrieval_hit=retrieval_rank is not None,
        retrieval_rank=retrieval_rank,
        answer=result.answer,
        matched_keywords=matched,
        missed_keywords=missed,
    )


def format_report(results: list[CaseResult]) -> str:
    n = len(results)
    retrieval_hits = sum(1 for r in results if r.retrieval_hit)
    full_matches = sum(1 for r in results if r.full_keyword_match)
    avg_coverage = sum(r.keyword_coverage for r in results) / n
    ranked_hits = [r.retrieval_rank for r in results if r.retrieval_rank is not None]
    avg_rank = sum(ranked_hits) / len(ranked_hits) if ranked_hits else float("nan")

    lines = [
        "# Evaluation Results",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "## Summary",
        "",
        f"- Questions evaluated: {n}",
        f"- Retrieval hit rate (expected doc in top-{TOP_K}): {retrieval_hits}/{n} ({retrieval_hits / n:.0%})",
        f"- Average rank when hit: {avg_rank:.1f}",
        f"- Full keyword match rate: {full_matches}/{n} ({full_matches / n:.0%})",
        f"- Average keyword coverage: {avg_coverage:.0%}",
        "",
        "## Per-question results",
        "",
        "| # | Question | Expected doc | Retrieval | Keywords |",
        "|---|---|---|---|---|",
    ]

    for i, r in enumerate(results, start=1):
        retrieval_cell = f"hit (rank {r.retrieval_rank})" if r.retrieval_hit else "**miss**"
        keyword_cell = (
            "all matched"
            if r.full_keyword_match
            else f"missed: {', '.join(r.missed_keywords)}"
        )
        question_short = r.case.question if len(r.case.question) <= 60 else r.case.question[:57] + "..."
        lines.append(
            f"| {i} | {question_short} | {r.case.expected_document} | {retrieval_cell} | {keyword_cell} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    results: list[CaseResult] = []
    start = time.perf_counter()

    for i, case in enumerate(EVAL_SET, start=1):
        print(f"[{i}/{len(EVAL_SET)}] {case.question}")
        result = run_case(case)
        status = "OK" if result.retrieval_hit and result.full_keyword_match else "CHECK"
        print(f"    retrieval={'hit' if result.retrieval_hit else 'MISS'} "
              f"keywords={len(result.matched_keywords)}/{len(case.expected_keywords)} [{status}]")
        results.append(result)

    elapsed = time.perf_counter() - start
    report = format_report(results)
    RESULTS_PATH.write_text(report, encoding="utf-8")

    print(f"\nDone in {elapsed:.0f}s. Report written to {RESULTS_PATH}")
    retrieval_hits = sum(1 for r in results if r.retrieval_hit)
    full_matches = sum(1 for r in results if r.full_keyword_match)
    print(f"Retrieval hit rate: {retrieval_hits}/{len(results)}")
    print(f"Full keyword match rate: {full_matches}/{len(results)}")


if __name__ == "__main__":
    main()
