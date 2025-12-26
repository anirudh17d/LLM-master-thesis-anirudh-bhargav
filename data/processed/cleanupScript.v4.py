import json
from pathlib import Path

INPUT = Path("fine-tuning-training-data.v4.jsonl")
OUTPUT = Path("fine-tuning-training-data.v4.cleaned.jsonl")

KEEP_SYNTAX_SHEETS = {"fs1_py3122", "fs2_py3123"}

n_in = 0
n_out = 0
n_dropped = 0

with INPUT.open("r", encoding="utf-8") as fin, OUTPUT.open("w", encoding="utf-8") as fout:
    for line in fin:
        line = line.strip()
        if not line:
            continue
        n_in += 1
        ex = json.loads(line)

        sheet = ex.get("source_sheet", "")
        msgs = ex.get("messages", [])
        user_q = msgs[1]["content"] if len(msgs) > 1 else ""

        if "syntax or language-level changes" in user_q.lower():
            if sheet not in KEEP_SYNTAX_SHEETS:
                n_dropped += 1
                continue

        fout.write(json.dumps(ex, ensure_ascii=False) + "\n")
        n_out += 1

print("Input examples:", n_in)
print("Kept examples:", n_out)
print("Dropped examples:", n_dropped)
