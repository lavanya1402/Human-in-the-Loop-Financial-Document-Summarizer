# app/migrations.py
from sqlalchemy import text
from app.db import ENGINE

MIGRATIONS = [
    {
        "id": "001_init_tables",
        "sql": """
        CREATE TABLE IF NOT EXISTS public.approved_summaries (
            id UUID PRIMARY KEY,
            original_text TEXT NOT NULL,
            summary TEXT NOT NULL,
            score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 10),
            flagged_uncertain BOOLEAN DEFAULT FALSE,
            flagged_too_short BOOLEAN DEFAULT FALSE,
            approved_by TEXT NOT NULL,
            feedback TEXT,
            approved_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS public.rejected_summaries (
            id UUID PRIMARY KEY,
            original_text TEXT NOT NULL,
            rejected_summary TEXT NOT NULL,
            score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 10),
            flagged_uncertain BOOLEAN DEFAULT FALSE,
            flagged_too_short BOOLEAN DEFAULT FALSE,
            feedback TEXT NOT NULL,
            rejected_by TEXT NOT NULL,
            rejected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
    },
    {
        "id": "002_audit_events",
        "sql": """
        CREATE TABLE IF NOT EXISTS public.audit_events (
            id UUID PRIMARY KEY,
            event_type TEXT NOT NULL,     -- APPROVE / REJECT / etc
            reviewer TEXT NOT NULL,
            doc_id UUID,
            score INTEGER,
            message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
    },
    {
        "id": "003_indexes",
        "sql": """
        CREATE INDEX IF NOT EXISTS idx_approved_time ON public.approved_summaries (approved_at DESC);
        CREATE INDEX IF NOT EXISTS idx_rejected_time ON public.rejected_summaries (rejected_at DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_time ON public.audit_events (created_at DESC);
        """,
    },
]

def run_migrations():
    with ENGINE.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.schema_migrations (
            id TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """))

        applied = {r[0] for r in conn.execute(text("SELECT id FROM public.schema_migrations")).fetchall()}

        for m in MIGRATIONS:
            if m["id"] in applied:
                continue
            conn.execute(text(m["sql"]))
            conn.execute(text("INSERT INTO public.schema_migrations (id) VALUES (:id)"), {"id": m["id"]})
