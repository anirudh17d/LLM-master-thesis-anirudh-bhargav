#!/usr/bin/env python3
import json
from pathlib import Path

# -------------------------------------------------------------------
# Configuration
# This script must be placed in and run from the "processed" folder.
# -------------------------------------------------------------------
CURRENT_DIR = Path(__file__).resolve().parent
FACTSHEET_FILE = CURRENT_DIR / "python_factsheets.jsonl"
OUTPUT_FILE = CURRENT_DIR / "fine-tuning-training-data.jsonl"

SYSTEM_PROMPT = (
    "You are a helpful Python programming assistant. "
    "Answer concisely and accurately based on the Python release information."
)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def load_factsheets(path: Path):
    sheets = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                sheets.append(json.loads(line))
    return sheets


def simple_sentence_split(text: str):
    """Basic sentence splitter."""
    import re
    text = text.replace("\n", " ")
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in parts if s.strip()]


def summarize_notes_for_answer(notes: str, max_sentences: int = 4):
    """Use the first few sentences as the grounded answer."""
    sentences = simple_sentence_split(notes)
    if not sentences:
        return "No detailed information is available in the factsheet."
    return " ".join(sentences[:max_sentences])


def generate_questions_for_sheet(sheet: dict):
    """Generate questions based on sheet type and title."""
    title = sheet.get("topic_title", "this Python topic")
    version = sheet.get("version", "")
    topic_type = sheet.get("topic_type", "")

    base_questions = [
        f"What is the main purpose of {title}?",
        f"When was {title} released and what does it focus on?",
        f"What kind of changes were included in {title}?",
        f"How many bugfixes or improvements are mentioned for {title}?",
        f"Which areas of the interpreter or standard library were affected in {title}?",
        f"Why is {title} important in the Python release cycle?",
        f"What regressions or stability issues were addressed in {title}?",
        f"Were any documentation or build-system changes mentioned in {title}?",
        f"Summarize the changes described in {title}.",
        f"What does {title} suggest about the stability of Python {version}?",
        f"How does {title} compare this release to the previous one?",
    ]

    extra_questions = []

    if "security" in topic_type.lower():
        extra_questions.extend([
            f"Which CVEs or security vulnerabilities are discussed in {title}?",
            f"Which modules were impacted by the security fixes mentioned in {title}?",
            f"What security hardening changes were included in the release described in {title}?",
        ])

    if "pep" in topic_type.lower():
        extra_questions.extend([
            f"Which PEPs targeting Python {version} had status updates in {title}?",
            f"What wording changes in Accepted PEPs are mentioned in {title}?",
            f"What does {title} describe about PEP lifecycle changes from alpha to beta?",
        ])

    if "release-engineering" in topic_type.lower() or "blocker" in title.lower():
        extra_questions.extend([
            f"What are release blockers according to {title}?",
            f"What issues were considered release blockers for Python {version}?",
            f"Which regressions or crashes were resolved before the release described in {title}?",
        ])

    # Deduplicate questions
    seen = set()
    all_q = base_questions + extra_questions
    deduped = []
    for q in all_q:
        if q not in seen:
            seen.add(q)
            deduped.append(q)

    return deduped


def build_training_entry(question: str, answer: str, sheet_id: str):
    """Build final training example in chat-style JSONL format."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ],
        "source_sheet": sheet_id,
    }


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
def main():
    print(f"Loading factsheets from: {FACTSHEET_FILE}")
    sheets = load_factsheets(FACTSHEET_FILE)
    print(f"Loaded {len(sheets)} factsheets.")

    num_examples = 0

    with OUTPUT_FILE.open("w", encoding="utf-8") as out_f:
        for sheet in sheets:
            sheet_id = sheet.get("sheet_id", "unknown_sheet")
            notes = sheet.get("detailed_notes", "")
            questions = generate_questions_for_sheet(sheet)

            # Summarize detailed_notes once for consistent answer style
            base_answer = summarize_notes_for_answer(notes, max_sentences=4)

            for q in questions:
                answer = base_answer
                entry = build_training_entry(q, answer, sheet_id)
                out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                num_examples += 1

    print(f"Generated {num_examples} Q&A training examples.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
