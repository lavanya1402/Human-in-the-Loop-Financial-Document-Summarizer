# db_smoke.py
import os, uuid, psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DB_URL")
print("DB_URL host:", DB_URL.split("@")[-1] if DB_URL and "@" in DB_URL else DB_URL)

sql_insert = """
INSERT INTO public.approved_summaries
(id, original_text, summary, score, flagged_uncertain, flagged_too_short, approved_by, feedback, approved_at)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NOW());
"""

sql_select = "SELECT id, approved_by, approved_at FROM public.approved_summaries ORDER BY approved_at DESC LIMIT 3;"

try:
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql_insert, (
        str(uuid.uuid4()),
        "SMOKE ORIGINAL",
        "SMOKE SUMMARY ROW",
        9, False, False,
        "SMOKE-TEST", "inserted via smoke test"
    ))
    print("Insert OK")
    cur.execute(sql_select)
    for r in cur.fetchall():
        print("Row:", r)
    cur.close(); conn.close()
except Exception as e:
    print("ERROR:", e)
