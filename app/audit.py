# app/audit.py
import uuid
from sqlalchemy import text
from app.db import ENGINE

def log_event(event_type: str, reviewer: str, doc_id=None, score=None, message=None):
    payload = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "reviewer": reviewer,
        "doc_id": str(doc_id) if doc_id else None,
        "score": score,
        "message": message,
    }

    with ENGINE.begin() as conn:
        conn.execute(text("""
            INSERT INTO public.audit_events (id, event_type, reviewer, doc_id, score, message)
            VALUES (:id, :event_type, :reviewer, :doc_id, :score, :message)
        """), payload)
