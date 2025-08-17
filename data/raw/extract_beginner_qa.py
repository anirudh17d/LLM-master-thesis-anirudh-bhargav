import pandas as pd
import json
import os
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from tqdm import tqdm
import warnings

# 🚫 Suppress unnecessary BeautifulSoup warnings
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

print("⏳ Script started...")

# 📁 Define paths
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.abspath(os.path.join(script_dir, ".."))
questions_path = os.path.join(base_dir, "raw", "Questions.csv")
answers_path = os.path.join(base_dir, "raw", "Answers.csv")
output_path = os.path.join(base_dir, "processed", "qa_dataset.jsonl")

print("📂 Loading CSV files...")
questions_df = pd.read_csv(questions_path, encoding="ISO-8859-1", usecols=["Id", "Title", "Body"])
answers_df = pd.read_csv(answers_path, encoding="ISO-8859-1", usecols=["ParentId", "Body"])

print(f"✅ Loaded {len(questions_df)} questions and {len(answers_df)} answers")

# 🔍 Filter beginner-style questions
beginner_keywords = [
    "beginner", "basic", "starting", "first program", "how to", "new to", 
    "simple", "explain", "understand", "easy", "introduction", "step by step"
]

def is_beginner_question(text):
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in beginner_keywords)

print("🔍 Filtering beginner questions...")

filtered_questions = []
for _, row in tqdm(questions_df.iterrows(), total=len(questions_df)):
    title = BeautifulSoup(str(row.get("Title", "")), "lxml").get_text()
    body = BeautifulSoup(str(row.get("Body", "")), "lxml").get_text()
    if is_beginner_question(title) or is_beginner_question(body):
        filtered_questions.append({
            "Id": row["Id"],
            "Title": title.strip(),
            "Body": body.strip()
        })

print(f"✅ Found {len(filtered_questions)} beginner-style questions")

# 🔗 Match answers
answers_df["Body"] = answers_df["Body"].apply(lambda x: BeautifulSoup(str(x), "lxml").get_text().strip())

qa_pairs = []
for q in tqdm(filtered_questions, desc="🔗 Matching answers"):
    matched_answers = answers_df[answers_df["ParentId"] == q["Id"]]
    if not matched_answers.empty:
        qa_pairs.append({
            "question": f"{q['Title']} {q['Body']}",
            "answer": matched_answers.iloc[0]["Body"]
        })

print(f"✅ Merged with answers: {len(qa_pairs)} Q&A pairs")

# 💾 Save to JSONL
print(f"💾 Saving to {output_path}...")
with open(output_path, "w", encoding="utf-8") as f:
    for pair in qa_pairs:
        f.write(json.dumps(pair, ensure_ascii=False) + "\n")

print(f"✅ Done! Saved {len(qa_pairs)} Q&A pairs to {output_path}")
