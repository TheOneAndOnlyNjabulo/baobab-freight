"""
Manual test script for the RAG chain - run via CLI:
    cd backend
    .venv/Scripts/python.exe scripts/test_rag_chain.py

Includes a couple of in-scope questions and one deliberately out-of-scope
question, to eyeball whether the citation-aware prompt actually declines to
guess when the retrieved context doesn't answer the question. Note: the
hard numeric low-confidence threshold (skip the LLM call entirely below a
score cutoff) is step 12, not this step - here we're only checking that the
prompt-level instruction does something reasonable on its own.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from app.rag_chain import answer_question  # noqa: E402

SAMPLE_QUESTIONS = [
    "What VAT rate applies to imports into South Africa?",
    "How long do I have to report damaged goods, and what happens if I miss the window?",
    "What's the weather like in Cape Town today?",  # deliberately out of scope
]


def main() -> None:
    for question in SAMPLE_QUESTIONS:
        print(f"\n=== {question}")
        result = answer_question(question)
        print(result.answer)
        print("\nSources:")
        for s in result.sources:
            print(f"  - {s.document} §{s.section}")


if __name__ == "__main__":
    main()
