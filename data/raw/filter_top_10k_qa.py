import json
from pathlib import Path

# Paths
input_path = Path("../processed/qa_dataset.jsonl")  # Adjust if you move it
output_path = Path("../processed/qa_dataset_top10k.jsonl")

# Configurable filters
MIN_Q_LEN = 20
MIN_A_LEN = 50
MAX_Q_LEN = 300
MAX_A_LEN = 1000

seen_questions = set()
filtered = []

print("📂 Filtering top 10,000 Q&A pairs...")
with open(input_path, "r", encoding="utf-8") as infile:
    for line in infile:
        try:
            item = json.loads(line)
            q = item.get("question", "").strip()
            a = item.get("answer", "").strip()

            # Length-based filters
            if len(q) < MIN_Q_LEN or len(a) < MIN_A_LEN:
                continue
            if len(q) > MAX_Q_LEN or len(a) > MAX_A_LEN:
                continue

            # Remove any leftover markup
            if "<" in a or ">" in a:
                continue

            # Skip duplicates
            if q.lower() in seen_questions:
                continue

            seen_questions.add(q.lower())
            filtered.append({"question": q, "answer": a})

            if len(filtered) >= 10_000:
                break

        except json.JSONDecodeError:
            continue  # Skip corrupted lines

# Save
with open(output_path, "w", encoding="utf-8") as outfile:
    for item in filtered:
        outfile.write(json.dumps(item) + "\n")

print(f"✅ Saved {len(filtered)} filtered Q&A pairs to {output_path}")
