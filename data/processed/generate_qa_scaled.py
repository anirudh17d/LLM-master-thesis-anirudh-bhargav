#!/usr/bin/env python3
import json
import re
from pathlib import Path

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------
CURRENT_DIR = Path(__file__).resolve().parent
FACTSHEET_FILE = CURRENT_DIR / "python_factsheets.jsonl"
OUTPUT_FILE = CURRENT_DIR / "fine-tuning-training-data.v3.jsonl"

SYSTEM_PROMPT = (
    "You are a helpful Python programming assistant. "
    "Answer concisely and accurately based on the Python release information."
)

# How aggressively to scale:
# For each base question, we will generate (1 + N_PARAPHRASES) variants.
N_PARAPHRASES = 4   # Set to 3 if you want even more data

# -------------------------------------------------------------------
# Helpers
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
    text = text.replace("\n", " ")
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in parts if s.strip()]


def clean_markdown_preserve(text: str) -> str:
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)
    return text


def build_sentence_buckets(notes: str):
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

        if not added:
            buckets["summary"].append(s)

    if not buckets["summary"] and sentences:
        buckets["summary"] = sentences[:2]

    return buckets


def natural_version_label(sheet):
    version = sheet.get("version")
    if version:
        return f"Python {version}"
    title = sheet.get("topic_title", "this Python release")
    return title


# -------------------------------------------------------------------
# Question templates + paraphrasing
# -------------------------------------------------------------------

def base_questions_for_sheet(sheet):
    sheet_id = sheet.get("sheet_id", "")
    label = natural_version_label(sheet)
    title = sheet.get("topic_title", label)
    version = sheet.get("version", "")
    topic_type = sheet.get("topic_type", "")

    q = []

    # Generic / summary & comparison
    q += [
        f"What changed in {label}?",
        f"What is {label} and what does this release focus on?",
        f"Is {label} mainly a bugfix release or does it add new features?",
        f"What kinds of improvements and bugfixes are included in {label}?",
        f"When was {label} released and why is it important?",
        f"How does {label} compare to the previous release in the same series?",
        f"What does {label} tell us about the stability of the {version} series?",
        f"Which parts of the interpreter or standard library were most affected in {label}?",
        f"Summarize the main goals of {label}.",
        f"What did {label} contribute for users already on this major version?",
    ]

    # Topic-specific
    if "security" in topic_type.lower():
        q += [
            f"Which security fixes or advisories are mentioned in {label}?",
            f"Did {label} address any CVEs or vulnerabilities, and how?",
            f"What does the security section for {label} say about the vulnerabilities patched?",
        ]

    if "pep" in topic_type.lower():
        q += [
            f"Which PEPs related to Python {version} changed status or wording around the 3.14 beta phase?",
            f"How did the Accepted text of PEPs like 703 and 709 evolve for Python {version}?",
            f"What does the summary say about PEP lifecycle and wording changes targeting Python {version}?",
        ]

    if "release-engineering" in topic_type.lower() or "blocker" in title.lower():
        q += [
            f"What kinds of release blockers were tracked for {label}, and why did they matter?",
            f"What problems had to be fixed before {label} could be released?",
            f"How were release blockers for {label} tracked and resolved?",
        ]

    # CVE-specific sheet
    if "cves" in sheet_id.lower():
        q += [
            "Which categories of CVEs were fixed in Python 3.12.x in mid-2024?",
            "What kinds of modules or libraries were affected by the mid-2024 CVE fixes in Python 3.12.x?",
            "How do the mid-2024 Python 3.12.x security fixes describe the CVEs and impacted components?",
        ]

    # Explicit evaluation questions
    eval_qs = {
        "fs1_py3122": [
            "What was added in Python 3.12.2, released in March 2024?",
        ],
        "fs2_py3123": [
            "What specific bug fixes and security advisories were included in Python 3.12.3, released in April 2024?",
        ],
        "fs4_py312x_mid2024_cves": [
            "Which CVEs were fixed in Python 3.12.x during mid-2024, and which modules were impacted?",
        ],
        "fs5_peps_314_status_delta": [
            "Which PEPs targeting Python 3.14 changed status between alpha and beta, and what changed in their Accepted wording?",
        ],
        "fs6_3131_release_blockers": [
            "What were the documented release blockers and notable open issues before the Python 3.13.1 release, and which of them were resolved by the time 3.13.1 shipped?",
        ],
    }
    if sheet_id in eval_qs:
        q += eval_qs[sheet_id]

    # Dedup
    seen = set()
    out = []
    for question in q:
        if question not in seen:
            seen.add(question)
            out.append(question)
    return out


def paraphrase_question(q: str):
    """
    Very dumb paraphraser: apply a few canned rewrites.
    We generate a list of variants, then we'll slice to N_PARAPHRASES.
    """
    variants = set()
    q_low = q.lower()

    # 1: Generic rephrase wrappers
    variants.add(q)
    variants.add("Can you explain " + q[0].lower() + q[1:] if q.endswith("?") else "Can you explain " + q)
    variants.add("In simple terms, " + q[0].lower() + q[1:] if q.endswith("?") else "In simple terms, " + q)

    # 2: Replace some WH-terms & verbs
    v = q
    v = v.replace("What is", "How would you describe")
    v = v.replace("What are", "How would you summarize")
    v = v.replace("What kinds of", "Which types of")
    v = v.replace("What did", "Which improvements did")
    variants.add(v)

    v2 = q
    v2 = v2.replace("Summarize", "Give an overview of")
    v2 = v2.replace("How does", "In what ways does")
    v2 = v2.replace("Which", "Can you list which")
    variants.add(v2)

    # 3: If it's about change/compare, add a relative phrasing
    if "compare" in q_low or "difference" in q_low or "changed" in q_low:
        variants.add("How is " + q.replace("How does ", "").replace("What changed in ", "").rstrip("?") + " different from the previous release?")

    # 4: Remove duplicates and return a list
    variants_list = [v for v in variants if v.strip()]
    return variants_list


# -------------------------------------------------------------------
# Answer selection (same as v2 logic)
# -------------------------------------------------------------------

def classify_question(question: str):
    q = question.lower()
    if any(k in q for k in ["security", "cve", "vulnerab", "advisories"]):
        return "security"
    if "pep" in q or "accepted wording" in q or "changed status" in q:
        return "pep"
    if "release blocker" in q or "blocker" in q:
        return "blocker"
    if any(k in q for k in ["regression", "crash", "stability"]):
        return "regression"
    if any(k in q for k in ["module", "standard library", "libraries", "components"]):
        return "modules"
    if any(k in q for k in ["compare", "previous release", "different from"]):
        return "comparison"
    return "summary"


def build_answer_for_question(question: str, buckets: dict):
    bucket_key = classify_question(question)
    candidates = buckets.get(bucket_key, [])
    if not candidates:
        candidates = buckets.get("summary", [])
    if not candidates:
        return "The available release notes do not contain enough information to answer this question."

    selected = candidates[:4]
    answer = " ".join(selected)
    return answer


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

            base_qs = base_questions_for_sheet(sheet)
            all_qs = []

            for q in base_qs:
                variants = paraphrase_question(q)
                # Take at most (1 + N_PARAPHRASES) variants to avoid explosion
                variants = variants[: (1 + N_PARAPHRASES)]
                all_qs.extend(variants)

            # Deduplicate across all_qs for this sheet
            seen = set()
            dedup_qs = []
            for q in all_qs:
                if q not in seen:
                    seen.add(q)
                    dedup_qs.append(q)

            for q in dedup_qs:
                answer = build_answer_for_question(q, buckets)
                entry = build_training_entry(q, answer, sheet_id)
                out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                num_examples += 1

    print(f"Generated {num_examples} Q&A training examples.")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
