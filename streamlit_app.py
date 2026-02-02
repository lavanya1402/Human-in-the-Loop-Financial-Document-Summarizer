# ========================================
# 💹 Human-in-the-Loop Financial Summarizer (Next-Level)
# ========================================

import os
import re
import time
import uuid
import tempfile
from typing import List, Tuple, Dict
from collections import Counter
from urllib.parse import urlparse

import pandas as pd
import pdfplumber
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# HuggingFace (local summarization)
from transformers import pipeline, AutoTokenizer

# -----------------------------
# 🪟 Windows tokenizer fix
# -----------------------------
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# -----------------------------
# 🌈 Streamlit Page Configuration
# -----------------------------
st.set_page_config(
    page_title="Human-in-the-Loop Financial Summarizer",
    page_icon="💹",
    layout="wide",
)

st.markdown(
    """
<style>
.block-container {max-width: 1160px;}
h1,h2,h3 {color:#0f172a;}
.summary-box{
  border-left:5px solid #2563eb;
  background:#f8fafc;
  padding:14px;
  border-radius:8px;
}
.warn{
  background:#fff7ed;
  border-left:4px solid #fb923c;
  padding:.6rem .8rem;
  border-radius:.5rem;
}
.small-note{ color:#64748b; font-size:.85rem; }
</style>
""",
    unsafe_allow_html=True,
)

# ======================================================
# ⚙️ ENV + SECRETS (local vs cloud) — SAFE, NO CRASH
# ======================================================

load_dotenv()  # local only, cloud typically ignores .env

def _safe_secrets_get(key: str, default: str = "") -> str:
    """
    Streamlit local me secrets.toml absent ho sakta hai.
    st.secrets access sometimes throws StreamlitSecretNotFoundError.
    So: try/except and fallback.
    """
    try:
        return str(st.secrets.get(key, default)).strip()
    except Exception:
        return default

def _env_get(key: str, default: str = "") -> str:
    return str(os.getenv(key, default)).strip()

def get_db_url() -> str:
    """
    Priority:
    1) Streamlit Cloud: DB_URL_POOLER (recommended)
    2) Streamlit Cloud/Local: DB_URL (generic)
    3) Local: .env DB_URL_DIRECT
    4) Local: .env DB_URL
    """
    # cloud recommended
    pooler = _safe_secrets_get("DB_URL_POOLER", "")
    if pooler:
        return pooler

    # generic secret
    secret_db = _safe_secrets_get("DB_URL", "")
    if secret_db:
        return secret_db

    # local .env preference (direct)
    direct = _env_get("DB_URL_DIRECT", "")
    if direct:
        return direct

    # fallback local env
    return _env_get("DB_URL", "")

DB_URL = get_db_url()

DEBUG_DB = (_safe_secrets_get("DEBUG_DB", "") or _env_get("DEBUG_DB", "0")).strip()
DEBUG_DB = DEBUG_DB in ("1", "true", "True", "yes", "YES")

if not DB_URL:
    st.error("❌ DB_URL missing. Add in Streamlit Secrets (cloud) or .env (local).")
    st.stop()

# ======================================================
# 🧠 SQLAlchemy Engine (production-friendly pooling)
# ======================================================

ENGINE = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_recycle=300,   # keeps connections fresh
    pool_size=3,
    max_overflow=2,
)

# ======================================================
# 🗃️ Migrations (schema_migrations + tables + indexes)
# ======================================================

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
            event_type TEXT NOT NULL,     -- APPROVE / REJECT / ERROR / etc
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

# Run migrations at startup
try:
    run_migrations()
except Exception as e:
    st.error(f"❌ Database initialization (migrations) failed: {e}")
    st.stop()

# ======================================================
# 🔎 Safe DB Debug (only when DEBUG_DB=1)
# ======================================================

def debug_db_info():
    u = urlparse(DB_URL)
    # DO NOT print password
    host = u.hostname
    port = u.port
    user = u.username
    dbname = (u.path or "").lstrip("/") or ""
    st.success("✅ DB_URL loaded")
    st.write("host:", host)
    st.write("port:", port)
    st.write("user:", user)
    st.write("database:", f"/{dbname}")

    # smoke query
    try:
        with ENGINE.connect() as conn:
            result = conn.execute(text("SELECT NOW();")).fetchone()
        st.success("✅ Database connection successful!")
        st.write("Server time:", result[0])
    except Exception as e:
        st.error("❌ Connection failed")
        st.code(str(e))

# ======================================================
# 🧠 Summarizer (Local Models)
# ======================================================

@st.cache_resource(show_spinner=False)
def get_summarizer(mode: str):
    # NOTE: t5-small needs sentencepiece. If you don't want that dependency, remove Ultra-Fast option.
    if mode == "Ultra-Fast":
        model = "t5-small"
    elif mode == "Fast":
        model = "sshleifer/distilbart-cnn-12-6"
    else:
        model = "facebook/bart-large-cnn"

    tokenizer = AutoTokenizer.from_pretrained(model, use_fast=False)
    return pipeline("summarization", model=model, tokenizer=tokenizer, device=-1)

# ======================================================
# 📄 PDF Processing
# ======================================================

def extract_text_from_pdf(path: str) -> str:
    pages = []
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            t = p.extract_text() or ""
            if t.strip():
                pages.append(t)
    return "\n".join(pages)

def clean_text(txt: str) -> str:
    txt = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", " ", txt)
    txt = re.sub(r"\s{2,}", " ", txt)
    return txt.strip()

def chunk_text(text: str, tokenizer, max_tokens: int) -> List[str]:
    words = text.split()
    chunks, current, count = [], [], 0

    for w in words:
        tokens = len(tokenizer.encode(w, add_special_tokens=False))
        if count + tokens > max_tokens and current:
            chunks.append(" ".join(current))
            current, count = [w], tokens
        else:
            current.append(w)
            count += tokens

    if current:
        chunks.append(" ".join(current))
    return chunks

# ======================================================
# 🧾 Summarization Pipeline
# ======================================================

def summarize_text(text: str, mode: str, detail: str, placeholder):
    summarizer = get_summarizer(mode)
    tokenizer = summarizer.tokenizer

    cleaned = clean_text(text)
    model_max = getattr(tokenizer, "model_max_length", 512)
    limit = int(0.85 * model_max)

    chunks = chunk_text(cleaned, tokenizer, limit) or [cleaned]

    config = {
        "Concise": (60, 30),
        "Balanced": (120, 60),
        "Detailed": (180, 90),
    }
    max_len, min_len = config[detail]

    results = []
    placeholder.info(f"📘 Processing {len(chunks)} chunk(s)…")
    start = time.time()

    for i, ch in enumerate(chunks, 1):
        out = summarizer(ch, max_length=max_len, min_length=min_len, do_sample=False)[0]["summary_text"]
        results.append(out)
        placeholder.progress(i / max(1, len(chunks)), text=f"Summarized {i}/{len(chunks)}")

    final = " ".join(results).strip()
    elapsed = int(time.time() - start)
    return final, elapsed

# ======================================================
# 📊 Scoring Logic (Dynamic)
# ======================================================

_FIN_TERMS = {
    "revenue","sales","profit","loss","ebitda","margin","cash","cash flow",
    "operating","net","expense","guidance","forecast","outlook","risk",
    "debt","interest","liquidity","dividend","capex","capital expenditure",
    "gross","yoy","qoq","growth","decline"
}
_UNCERTAIN = {"maybe","possibly","might","could","appears","seems","approximately"}
_STOPWORDS = {
    "the","a","an","and","or","of","for","to","in","on","with","is","are","was","were",
    "that","this","by","as","at","from","it","be","has","have","had","their","its","they"
}

def _tokenize(s: str):
    return re.findall(r"[A-Za-z%]+", s.lower())

def score_summary(summary: str) -> Tuple[int, bool, bool, Dict]:
    words = _tokenize(summary)
    wc = len(words)
    too_short = wc < 60
    uncertain = any(u in summary.lower() for u in _UNCERTAIN)

    score = 5.0

    coverage_hits = sum(1 for t in _FIN_TERMS if t in summary.lower())
    score += min(coverage_hits * 0.25, 2.5)

    num_hits = len(re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b", summary))
    pct_hits = summary.count("%")
    score += min(0.75 + 0.15 * min(num_hits, 5) + 0.15 * min(pct_hits, 4), 1.5)

    if uncertain:
        score -= 1.5

    if too_short:
        score -= 2.0
    elif wc > 350:
        score -= 1.0

    meaningful = [w for w in words if w not in _STOPWORDS]
    freq = Counter(meaningful)
    top = freq.most_common(5)
    dom_pen = sum(1 for w,c in top if c / max(1, len(meaningful)) > 0.06)
    score -= min(dom_pen * 0.7, 2.0)

    score = int(max(1, min(10, round(score))))

    breakdown = {
        "word_count": wc,
        "coverage_hits": coverage_hits,
        "numeric_tokens": num_hits,
        "percent_tokens": pct_hits,
        "uncertain": uncertain,
        "too_short": too_short,
        "final_score": score,
    }
    return score, uncertain, too_short, breakdown

# ======================================================
# 💾 Database Inserts
# ======================================================

def insert_row(table: str, payload: dict):
    with ENGINE.begin() as conn:
        if table == "approved":
            conn.execute(text("""
            INSERT INTO public.approved_summaries
            (id, original_text, summary, score, flagged_uncertain, flagged_too_short, approved_by, feedback)
            VALUES (:id,:o,:s,:sc,:u,:t,:by,:fb)
            """), payload)
        else:
            conn.execute(text("""
            INSERT INTO public.rejected_summaries
            (id, original_text, rejected_summary, score, flagged_uncertain, flagged_too_short, feedback, rejected_by)
            VALUES (:id,:o,:s,:sc,:u,:t,:fb,:by)
            """), payload)

# ======================================================
# 🚀 UI
# ======================================================

st.title("Human-in-the-Loop Financial Summarizer")
st.caption("Local • Private • Auditable • Supabase-backed")

# Optional debug panel
if DEBUG_DB:
    with st.expander("🔎 Supabase Connection Debug (safe)"):
        debug_db_info()

mode = st.sidebar.radio("Speed", ["Ultra-Fast", "Fast", "Quality"], index=1, key="speed_mode")
detail = st.sidebar.select_slider("Detail", ["Concise","Balanced","Detailed"], value="Balanced", key="detail_level")
st.sidebar.markdown("---")
st.sidebar.info("Made with ❤️ by **Lavanya Srivastava**")

uploaded = st.file_uploader("📂 Upload a PDF (text-based)", type=["pdf"])

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded.read())
        pdf_path = tmp.name

    with st.spinner("Extracting text…"):
        text_data = extract_text_from_pdf(pdf_path)

    if not text_data.strip():
        st.error("⚠️ No readable text detected in this PDF (scanned image PDF will not work).")
        st.stop()

    st.success("✅ PDF uploaded and text extracted.")

    if st.button("🧠 Generate Summary", type="primary"):
        holder = st.empty()
        summary, elapsed = summarize_text(
            text_data,
            st.session_state["speed_mode"],
            st.session_state["detail_level"],
            holder
        )

        score, uncertain, too_short, breakdown = score_summary(summary)

        st.session_state["doc_text"] = text_data
        st.session_state["summary"] = summary
        st.session_state["score"] = score
        st.session_state["uncertain"] = uncertain
        st.session_state["too_short"] = too_short
        st.session_state["breakdown"] = breakdown
        st.session_state["elapsed"] = elapsed

# Render if we have a summary in state
if "summary" in st.session_state and st.session_state["summary"]:
    summary = st.session_state["summary"]
    text_data = st.session_state["doc_text"]
    score = st.session_state["score"]
    uncertain = st.session_state["uncertain"]
    too_short = st.session_state["too_short"]
    breakdown = st.session_state["breakdown"]
    elapsed = st.session_state["elapsed"]

    st.markdown("### 📋 Generated Summary")
    st.markdown(f"<div class='summary-box'>{summary}</div>", unsafe_allow_html=True)
    st.caption(f"Completed in {elapsed}s — Mode: {st.session_state['speed_mode']}, Detail: {st.session_state['detail_level']}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Score", f"{score}/10")
    c2.metric("Uncertain Language", "Yes" if uncertain else "No")
    c3.metric("Too Short", "Yes" if too_short else "No")

    with st.expander("🔍 Score breakdown"):
        st.json(breakdown)

    st.divider()
    st.markdown("### ✅ Review & Store")
    st.caption("Choose Approve/Reject and submit. Reject will go to rejected_summaries.")

    with st.form("review_form", clear_on_submit=False):
        reviewer = st.text_input("Your Name", key="reviewer_name")
        decision = st.radio("Decision", ["Approve", "Reject"], horizontal=True, key="decision_choice")
        feedback = st.text_area("Feedback / Reason (required)", key="review_feedback")
        submitted = st.form_submit_button("📤 Submit Review")

    if submitted:
        decision = st.session_state["decision_choice"]
        reviewer = st.session_state["reviewer_name"]
        feedback = st.session_state["review_feedback"]

        if not reviewer.strip():
            st.error("Please enter your name.")
            st.stop()
        if not feedback.strip():
            st.error("Please provide feedback / reason.")
            st.stop()

        doc_id = str(uuid.uuid4())
        payload = {
            "id": doc_id,
            "o": text_data,
            "s": summary,
            "sc": int(score),
            "u": bool(uncertain),
            "t": bool(too_short),
            "by": reviewer.strip(),
            "fb": feedback.strip(),
        }

        try:
            if decision == "Approve":
                insert_row("approved", payload)
                log_event("APPROVE", reviewer.strip(), doc_id=doc_id, score=int(score), message=feedback.strip())
                st.success("✅ Saved to approved_summaries")
            else:
                insert_row("rejected", payload)
                log_event("REJECT", reviewer.strip(), doc_id=doc_id, score=int(score), message=feedback.strip())
                st.warning("❌ Saved to rejected_summaries")

            st.session_state["_refresh_key"] = str(uuid.uuid4())
            st.rerun()

        except Exception as e:
            # audit error too
            try:
                log_event("ERROR", reviewer.strip(), doc_id=doc_id, score=int(score), message=str(e)[:500])
            except Exception:
                pass
            st.error(f"❌ DB insert failed: {e}")

# ======================================================
# 📊 History (Approved + Rejected)
# ======================================================

st.markdown("---")
st.markdown("### 📊 Review History")

refresh_token = st.session_state.get("_refresh_key", "init")

def load_history(_token: str) -> pd.DataFrame:
    with ENGINE.connect() as conn:
        return pd.read_sql("""
            WITH hist AS (
              SELECT id::text AS id, summary AS text, score,
                     approved_by AS reviewer, feedback,
                     approved_at AS ts, 'Approved' AS status
              FROM public.approved_summaries
              UNION ALL
              SELECT id::text AS id, rejected_summary AS text, score,
                     rejected_by AS reviewer, feedback,
                     rejected_at AS ts, 'Rejected' AS status
              FROM public.rejected_summaries
            )
            SELECT * FROM hist
            ORDER BY ts DESC NULLS LAST, id DESC;
        """, conn)

try:
    df = load_history(refresh_token)
    st.dataframe(df, use_container_width=True, key=f"hist_{refresh_token}")
except Exception as e:
    st.error(f"History load failed: {e}")

if st.button("↻ Refresh history"):
    st.session_state["_refresh_key"] = str(uuid.uuid4())
    st.rerun()

# ======================================================
# 🧾 Audit Trail (Next Level)
# ======================================================

st.markdown("### 🧾 Audit Trail (events)")
with st.expander("Show audit events"):
    try:
        with ENGINE.connect() as conn:
            df_audit = pd.read_sql("""
                SELECT event_type, reviewer, doc_id::text AS doc_id, score, message, created_at
                FROM public.audit_events
                ORDER BY created_at DESC
                LIMIT 50;
            """, conn)
        st.dataframe(df_audit, use_container_width=True)
    except Exception as e:
        st.error(f"Audit load failed: {e}")

st.markdown("<div class='small-note'>— Made with ❤️ by Lavanya Srivastava</div>", unsafe_allow_html=True)
