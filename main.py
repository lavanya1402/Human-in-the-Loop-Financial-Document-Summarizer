"""
Note about environment files and virtual environments:

- The real .env file (containing secret keys and database credentials) is excluded from version control
  using .gitignore to keep sensitive data safe.

- The virtual environment folder (venv) is also excluded to avoid pushing bulky dependencies.

- However, we include an .env.example file in the repository as a template.
  It contains example environment variable keys (without secrets) to guide contributors
  in creating their own .env file with proper configuration.

This approach helps keep secrets safe while making setup easier for collaborators.
"""
import os
import uuid
import psycopg2
import openai
import pdfplumber
from dotenv import load_dotenv

# ✅ Load environment variables from .env file
load_dotenv()

# ✅ Get API Key and DB Connection String
openai.api_key = os.getenv("OPENAI_API_KEY")
DB_CONNECTION_STRING = os.getenv("DB_URL")

# ✅ Debug check (can be removed in production)
if not openai.api_key:
    raise Exception("❌ OPENAI_API_KEY is missing! Check your .env file.")
if not DB_CONNECTION_STRING:
    raise Exception("❌ DB_URL is missing! Check your .env file.")

def connect_db():
    print("🔗 Connecting to DB...")
    return psycopg2.connect(DB_CONNECTION_STRING)

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

def generate_summary(text):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize this financial document professionally."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content

def score_summary(summary, original_text):
    flagged_uncertain = any(word in summary.lower() for word in ["maybe", "probably", "i think"])
    flagged_too_short = len(summary.split()) < 25

    key_topics = ["asset allocation", "sip", "tax", "portfolio", "emotional", "risk", "monitor", "rebalance"]
    coverage_hits = sum(1 for topic in key_topics if topic in summary.lower())
    coverage_score = min(coverage_hits, 4)

    sentences = [s.strip() for s in summary.split(".") if s.strip()]
    avg_len = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
    clarity_score = 3 if 10 <= avg_len <= 20 else 2 if avg_len > 0 else 1

    grammar_issues = ["  ", "..", " ,", ",,", " ."]
    language_score = 2 if any(issue in summary for issue in grammar_issues) else 3

    total_score = coverage_score + clarity_score + language_score
    return total_score, flagged_uncertain, flagged_too_short

def store_summary(table, data):
    conn = connect_db()
    cur = conn.cursor()
    if table == "approved_summaries":
        cur.execute("""
            INSERT INTO approved_summaries 
            (id, original_text, summary, score, flagged_uncertain, flagged_too_short, approved_by, feedback)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()), data['original'], data['summary'], data['score'],
            data['uncertain'], data['too_short'], data['reviewer'], data.get('feedback')
        ))
    else:
        cur.execute("""
            INSERT INTO rejected_summaries 
            (id, original_text, rejected_summary, score, flagged_uncertain, flagged_too_short, feedback, rejected_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()), data['original'], data['summary'], data['score'],
            data['uncertain'], data['too_short'], data['feedback'], data['reviewer']
        ))
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Data saved to DB.")

def main():
    pdf_path = "snapshots/uploads/investment_strategy.pdf"
    print(f"📄 Extracting text from {pdf_path}...")
    original_text = extract_text_from_pdf(pdf_path)

    print("🧠 Generating summary...")
    summary = generate_summary(original_text)

    score, uncertain, too_short = score_summary(summary, original_text)

    print("\n📋 Generated Summary:\n")
    print(summary)
    print(f"\n🔍 Score: {score}/10 | Uncertain: {uncertain} | Too Short: {too_short}")

    decision = input("\n✅ Do you approve the summary? (approve/reject): ").strip().lower()
    reviewer = input("👤 Your name: ").strip()

    if decision == "approve":
        store_summary("approved_summaries", {
            "original": original_text,
            "summary": summary,
            "score": score,
            "uncertain": uncertain,
            "too_short": too_short,
            "reviewer": reviewer
        })
    else:
        feedback = input("📝 Please describe what needs improvement: ").strip()
        store_summary("rejected_summaries", {
            "original": original_text,
            "summary": summary,
            "score": score,
            "uncertain": uncertain,
            "too_short": too_short,
            "feedback": feedback,
            "reviewer": reviewer
        })

if __name__ == "__main__":
    main()
