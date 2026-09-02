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


def _keyword_matches(keyword: str, answer_lower: str) -> bool:
    """A keyword may list interchangeable phrasings separated by '|' (e.g. an
    acronym and its expansion, both used interchangeably in the source docs) -
    any one of them counts as a match, since penalizing the model for picking
    one correct phrasing over another tests the eval set, not the system."""
    return any(alt.strip().lower() in answer_lower for alt in keyword.split("|"))


@dataclass
class CaseResult:
    case: EvalCase
    retrieval_hit: bool
    retrieval_rank: int | None
    answer: str
    matched_keywords: list[str]
    missed_keywords: list[str]
    not_found_correct: bool | None = None

    @property
    def keyword_coverage(self) -> float:
        total = len(self.case.expected_keywords)
        return len(self.matched_keywords) / total if total else 1.0

    @property
    def full_keyword_match(self) -> bool:
        return len(self.missed_keywords) == 0

    @property
    def passed(self) -> bool:
        if self.case.expects_not_found:
            return bool(self.not_found_correct)
        return self.retrieval_hit and self.full_keyword_match


def run_case(case: EvalCase) -> CaseResult:
    chunks = retrieve(case.question, top_k=TOP_K)
    retrieved_docs = {c.source_document for c in chunks}

    if case.expects_not_found:
        result = answer_question(case.question, top_k=TOP_K)
        not_found_correct = len(result.sources) == 0 and len(result.chunk_ids) == 0
        return CaseResult(
            case=case,
            retrieval_hit=False,
            retrieval_rank=None,
            answer=result.answer,
            matched_keywords=[],
            missed_keywords=[],
            not_found_correct=not_found_correct,
        )

    if case.expected_documents:
        retrieval_hit = all(doc in retrieved_docs for doc in case.expected_documents)
        retrieval_rank = None
    else:
        retrieval_rank = next(
            (i for i, c in enumerate(chunks, start=1) if c.source_document == case.expected_document),
            None,
        )
        retrieval_hit = retrieval_rank is not None

    result = answer_question(case.question, top_k=TOP_K)
    answer_lower = result.answer.lower()
    matched = [kw for kw in case.expected_keywords if _keyword_matches(kw, answer_lower)]
    missed = [kw for kw in case.expected_keywords if kw not in matched]

    return CaseResult(
        case=case,
        retrieval_hit=retrieval_hit,
        retrieval_rank=retrieval_rank,
        answer=result.answer,
        matched_keywords=matched,
        missed_keywords=missed,
    )


def format_report(results: list[CaseResult]) -> str:
    n = len(results)
    passed = sum(1 for r in results if r.passed)

    single_doc = [r for r in results if not r.case.expects_not_found and not r.case.expected_documents]
    multi_doc = [r for r in results if r.case.expected_documents]
    not_found = [r for r in results if r.case.expects_not_found]

    retrieval_hits = sum(1 for r in single_doc if r.retrieval_hit)
    full_matches = sum(1 for r in single_doc if r.full_keyword_match)
    avg_coverage = sum(r.keyword_coverage for r in single_doc) / len(single_doc) if single_doc else float("nan")
    ranked_hits = [r.retrieval_rank for r in single_doc if r.retrieval_rank is not None]
    avg_rank = sum(ranked_hits) / len(ranked_hits) if ranked_hits else float("nan")

    multi_hits = sum(1 for r in multi_doc if r.retrieval_hit)
    not_found_correct = sum(1 for r in not_found if r.not_found_correct)

    lines = [
        "# Evaluation Results",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "## Summary",
        "",
        f"- Cases passed overall: {passed}/{n} ({passed / n:.0%})",
        "",
        f"**Single-document cases ({len(single_doc)})** — one document answers the question:",
        f"- Retrieval hit rate (expected doc in top-{TOP_K}): {retrieval_hits}/{len(single_doc)} ({retrieval_hits / len(single_doc):.0%})",
        f"- Average rank when hit: {avg_rank:.1f}",
        f"- Full keyword match rate: {full_matches}/{len(single_doc)} ({full_matches / len(single_doc):.0%})",
        f"- Average keyword coverage: {avg_coverage:.0%}",
        "",
        f"**Multi-document cases ({len(multi_doc)})** — the question spans two documents:",
        f"- All expected docs retrieved in top-{TOP_K}: {multi_hits}/{len(multi_doc)} ({multi_hits / len(multi_doc):.0%})"
        if multi_doc else "- (none)",
        "",
        f"**Not-found cases ({len(not_found)})** — correct behavior is the low-confidence fallback, not a guess:",
        f"- Correctly declined to answer: {not_found_correct}/{len(not_found)} ({not_found_correct / len(not_found):.0%})"
        if not_found else "- (none)",
        "",
        "## Per-question results",
        "",
        "| # | Question | Expected | Retrieval | Keywords / behavior |",
        "|---|---|---|---|---|",
    ]

    for i, r in enumerate(results, start=1):
        question_short = r.case.question if len(r.case.question) <= 60 else r.case.question[:57] + "..."

        if r.case.expects_not_found:
            expected_cell = "*(none — out of scope)*"
            retrieval_cell = "n/a"
            behavior_cell = "correctly declined" if r.not_found_correct else "**answered anyway**"
        elif r.case.expected_documents:
            expected_cell = "; ".join(r.case.expected_documents)
            retrieval_cell = "all hit" if r.retrieval_hit else "**miss**"
            behavior_cell = "n/a"
        else:
            expected_cell = r.case.expected_document or ""
            retrieval_cell = f"hit (rank {r.retrieval_rank})" if r.retrieval_hit else "**miss**"
            behavior_cell = (
                "all matched" if r.full_keyword_match else f"missed: {', '.join(r.missed_keywords)}"
            )

        lines.append(f"| {i} | {question_short} | {expected_cell} | {retrieval_cell} | {behavior_cell} |")

    return "\n".join(lines) + "\n"


def main() -> None:
    results: list[CaseResult] = []
    start = time.perf_counter()

    for i, case in enumerate(EVAL_SET, start=1):
        print(f"[{i}/{len(EVAL_SET)}] {case.question}")
        result = run_case(case)
        status = "OK" if result.passed else "CHECK"
        if case.expects_not_found:
            detail = "declined" if result.not_found_correct else "answered anyway"
        elif case.expected_documents:
            detail = "all docs hit" if result.retrieval_hit else "doc(s) missed"
        else:
            detail = (f"retrieval={'hit' if result.retrieval_hit else 'MISS'} "
                      f"keywords={len(result.matched_keywords)}/{len(case.expected_keywords)}")
        print(f"    {detail} [{status}]")
        results.append(result)

    elapsed = time.perf_counter() - start
    report = format_report(results)
    RESULTS_PATH.write_text(report, encoding="utf-8")

    passed = sum(1 for r in results if r.passed)
    print(f"\nDone in {elapsed:.0f}s. Report written to {RESULTS_PATH}")
    print(f"Cases passed: {passed}/{len(results)}")


if __name__ == "__main__":
    main()
