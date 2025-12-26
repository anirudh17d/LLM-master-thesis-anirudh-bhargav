#!/usr/bin/env python3
import json
import re
from pathlib import Path

# -------------------------------------------------------------------
# Config: run this script from the "processed" folder
# -------------------------------------------------------------------
CURRENT_DIR = Path(__file__).resolve().parent
FACTSHEET_FILE = CURRENT_DIR / "python_factsheets.jsonl"
OUTPUT_FILE = CURRENT_DIR / "fine-tuning-training-data.v2.jsonl"

SYSTEM_PROMPT = (
    "You are a helpful Python programming assistant. "
    "Answer concisely and accurately based on the Python release information."
)

# -------------------------------------------------------------------
# Basic helpers
# -------------------------------------------------------------------

def load_factsheets(path: Path):
    sheets = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            sheets.append(json.loads(line))
    return sheets


def simple_sentence_split(text: str):
    """Very simple sentence splitter, good enough for our notes."""
    text = text.replace("\n", " ")
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in parts if s.strip()]


def clean_markdown_preserve(text: str) -> str:
    """Remove bold/italic markers but keep words and structure."""
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)  # **bold** or __bold__
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)      # *italic* or _italic_
    return text


# -------------------------------------------------------------------
# Build sentence buckets per sheet
# -------------------------------------------------------------------

def build_sentence_buckets(notes: str):
    """
    Take detailed_notes and bucket sentences by topic:
    - summary (first sentences)
    - security
    - cves
    - pep
    - blockers
    - regressions / stability
    - modules / stdlib
    - comparison / series context
    """
    notes = clean_markdown_preserve(notes)
    sentences = simple_sentence_split(notes)

    buckets = {
        "summary": [],
        "security": [],
        "cve": [],
        "pep": [],
        "blocker": [],
        "regression": [],
        "modules": [],
        "comparison": [],
    }

    for s in sentences:
        lower = s.lower()
        added = False

        if any(k in lower for k in ["security", "vulnerab", "hardening"]):
            buckets["security"].append(s)
            added = True
        if "cve-" in lower or "cve " in lower:
            buckets["cve"].append(s)
            added = True
        if "pep " in lower or "pep-" in lower:
            buckets["pep"].append(s)
            added = True
        if "release blocker" in lower or "blocker" in lower:
            buckets["blocker"].append(s)
            added = True
        if any(k in lower for k in ["regression", "stability", "crash", "race condition"]):
            buckets["regression"].append(s)
            added = True
        if any(k in lower for k in ["module", "standard library", "stdlib"]):
            buckets["modules"].append(s)
            added = True
        if any(k in lower for k in ["compare", "previous release", "follow-up", "maintenance release"]):
            buckets["comparison"].append(s)
            added = True

        # If it didn't match any special bucket, leave it for summary/general
        if not added:
            buckets["summary"].append(s)

    # If summary is empty, at least put first 2 sentences there
    if not buckets["summary"] and sentences:
        buckets["summary"] = sentences[:2]

    return buckets


# -------------------------------------------------------------------
# Question templates
# -------------------------------------------------------------------

def natural_version_label(sheet):
    """
    Try to get a nice 'Python 3.12.2' style label instead of the full topic_title.
    """
    version = sheet.get("version")
    if version:
        return f"Python {version}"
    title = sheet.get("topic_title", "this Python release")
    return title


def generate_questions_for_sheet(sheet: dict):
    """
    Generate more natural, user-style questions for a sheet.
    Also inject your key evaluation-style questions per sheet_id.
    """
    sheet_id = sheet.get("sheet_id", "")
    label = natural_version_label(sheet)
    title = sheet.get("topic_title", label)
    version = sheet.get("version", "")
    topic_type = sheet.get("topic_type", "")

    # Generic natural questions
    base_questions = [
        f"What changed in {label}?",
        f"What is {label} and what does this release focus on?",
        f"Is {label} mainly a bugfix release or does it add new features?",
        f"What kind of improvements and bugfixes are included in {label}?",
        f"When was {label} released and why is it important?",
        f"How does {label} compare to the previous release in the same series?",
        f"What does {label} tell us about the stability of the {version} series?",
        f"Which parts of the standard library or interpreter were most affected in {label}?",
        f"Summarize the main goals of {label}.",
    ]

    extra = []

    # Topic-specific questions
    if "security" in topic_type.lower():
        extra += [
            f"Which security fixes or advisories are mentioned in {label}?",
            f"Did {label} address any CVEs or vulnerabilities?",
            f"What kind of security hardening was done in {label}?",
        ]

    if "pep" in topic_type.lower():
        extra += [
            f"Which PEPs related to Python {version} changed status according to {title}?",
            f"What does {title} say about how PEPs evolved between the alpha and beta phases of Python {version}?",
            f"What wording changes in Accepted PEPs are highlighted in {title}?",
        ]

    if "release-engineering" in topic_type.lower() or "blocker" in title.lower():
        extra += [
            f"What are release blockers in the context of {label}, and why do they matter?",
            f"What kinds of issues were considered release blockers for {label}?",
            f"Which regressions or crashes were resolved before {label} was released?",
        ]

    # Your explicit evaluation questions mapped by sheet_id
    eval_qs = {
        "fs1_py3122": [
            "What was added in Python 3.12.2 released in March 2024?"
        ],
        "fs2_py3123": [
            "What specific bug fixes and security advisories were included in Python 3.12.3, released in April 2024?"
        ],
        "fs4_py312x_mid2024_cves": [
            "Which CVEs were fixed in Python 3.12.x during mid-2024, and which modules were impacted?"
        ],
        "fs5_peps_314_status_delta": [
            "Which PEPs targeting Python 3.14 changed status between alpha and beta, and what changed in their Accepted wording?"
        ],
        "fs6_3131_release_blockers": [
            "What were the documented release blockers and notable open issues before the Python 3.13.1 release, and which of them were resolved by the time 3.13.1 shipped?"
        ],
        # For 3.13.1 / 3.13.2 combined question, we could add a custom
        # pair later if you want a single multi-release question.
    }

    if sheet_id in eval_qs:
        extra += eval_qs[sheet_id]

    # Deduplicate while preserving order
    seen = set()
    questions = []
    for q in base_questions + extra:
        if q not in seen:
            seen.add(q)
            questions.append(q)

    return questions


# -------------------------------------------------------------------
# Answer selection: map question -> bucket -> sentences
# -------------------------------------------------------------------

def classify_question(question: str):
    """Map question to a bucket key."""
    q = question.lower()
    if any(k in q for k in ["security", "cve", "vulnerab", "advisories"]):
        return "security"
    if "pep" in q or "accepted wording" in q or "changed status" in q:
        return "pep"
    if "release blocker" in q or "blocker" in q:
        return "blocker"
    if any(k in q for k in ["regression", "crash", "stability"]):
        return "regression"
    if any(k in q for k in ["module", "standard library"]):
        return "modules"
    if any(k in q for k in ["compare", "previous release"]):
        return "comparison"
    # Fallback: generic summary
    return "summary"


def build_answer_for_question(question: str, buckets: dict):
    """
    Build an answer by selecting 2–4 sentences from the bucket,
    falling back to summary if needed.
    """
    bucket_key = classify_question(question)
    candidates = buckets.get(bucket_key, [])

    if not candidates:
        candidates = buckets.get("summary", [])

    if not candidates:
        return "The available release notes do not contain enough information to answer this question."

    # Take first few sentences from the chosen bucket
    selected = candidates[:4]
    answer = " ".join(selected)
    return answer


# -------------------------------------------------------------------
# Build final training entries
# -------------------------------------------------------------------

def build_training_entry(question: str, answer: str, sheet_id: str):
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
            buckets = build_sentence_buckets(notes)
            questions = generate_questions_for_sheet(sheet)

            for q in questions:
                answer = build_answer_for_question(q, buckets)
                entry = build_training_entry(q, answer, sheet_id)
                out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                num_examples += 1

    print(f"Generated {num_examples} Q&A training examples.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
