# keep_supabase_alive_pg.py
import os
import time
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DB_URL = os.getenv("DB_URL")

def ping():
    try:
        with psycopg2.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("select 1;")
        print("[✓] Postgres ping OK")
    except Exception as e:
        print("[✗] DB ping failed:", e)

if __name__ == "__main__":
    while True:
        ping()
        time.sleep(int(os.getenv("PING_INTERVAL_SECONDS", "600")))
