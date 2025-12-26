import json
import re
from pathlib import Path

INPUT = Path("fine-tuning-training-data.jsonl")
OUTPUT = Path("fine-tuning-training-data.cleaned.jsonl")

def clean_markdown_preserve(text: str) -> str:
    # Remove bold/italic markers but keep the actual words
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)  # **bold** or __bold__
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)      # *italic* or _italic_
    # Do NOT touch headings (#), bullets (-, *), or newlines here
    return text

with INPUT.open("r", encoding="utf-8") as fin, OUTPUT.open("w", encoding="utf-8") as fout:
    for line in fin:
        line = line.strip()
        if not line:
            continue
        ex = json.loads(line)
        for msg in ex.get("messages", []):
            msg["content"] = clean_markdown_preserve(msg["content"])
        fout.write(json.dumps(ex, ensure_ascii=False) + "\n")
