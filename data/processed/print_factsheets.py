#!/usr/bin/env python3
import json
from pathlib import Path

# Script location (processed/)
CURRENT_DIR = Path(__file__).resolve().parent

# File in the same folder
FACTSHEET_FILE = CURRENT_DIR / "python_factsheets.jsonl"

def main():
    if not FACTSHEET_FILE.exists():
        print(f"ERROR: File not found -> {FACTSHEET_FILE}")
        return

    with FACTSHEET_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            sheet = json.loads(line)
            print("-" * 80)
            print("SHEET:", sheet.get("sheet_id", "UNKNOWN"))
            print(sheet.get("detailed_notes", "NO detailed_notes FIELD FOUND"))
            print("\n")

if __name__ == "__main__":
    main()
