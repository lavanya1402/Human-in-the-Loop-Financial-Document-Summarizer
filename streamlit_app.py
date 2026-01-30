# ========================================
# 💹 Human-in-the-Loop Financial Summarizer
# ========================================

import os
import re
import time
import uuid
import tempfile
from typing import List, Tuple, Dict
from collections import Counter

import pandas as pd
import pdfplumber
from sqlalchemy import create_engine, text
import streamlit as st
from dotenv import load_dotenv
from transformers import pipeline, AutoTokenizer

# --------- tokenizer “Already borrowed” fix on Windows ----------
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# -----------------------------
# 🌈 Streamlit Page Configuration
# -----------------------------
st.set_page_config(page_title="Financial Doc Summarizer", page_icon="💹", layout="wide")
st.markdown(
    """
<style>
.block-container {max-width: 1160px;}
h1,h2,h3 {color:#0f172a;}
hr {border:none; border-top:1px solid #e2e8f0; margin:1.2rem 0;}
div.stButton > button { background:#2563eb; color:#fff; font-weight:600; border-radius:8px; height:3rem; }
div.stButton > button:hover{ background:#1e40af; }
.summary-box{ border-left:5px solid #2563eb; background:#f8fafc; padding:14px; border-radius:8px; }
.warn{ background:#fff7ed; border-left:4px solid #fb923c; padding:.6rem .8rem; border-radius:.5rem; }
.small-note{ color:#64748b; font-size:.85rem; }
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# ⚙️ Env & DB
# -----------------------------
load_dotenv()
DB_URL = os.getenv("DB_URL")
if not DB_URL:
    st.error("DB_URL not found. Add it to your .env (with ?sslmode=require for Supabase).")
    st.stop()

ENGINE = create_engine(DB_URL, pool_pre_ping=True)

# -----------------------------
# 🧠 Summarizer (local + free)
# -----------------------------
@st.cache_resource(show_spinner=False)
def get_summarizer(mode: str):
    if mode == "Ultra-Fast":
        model_name = "t5-small"
    elif mode == "Fast":
        model_name = "sshleifer/distilbart-cnn-12-6"
    else:
        model_name = "facebook/bart-large-cnn"
    tok = AutoTokenizer.from_pretrained(model_name, use_fast=False)
    return pipeline("summarization", model=model_name, tokenizer=tok, device=-1)

# -----------------------------
# 📄 PDF → text
# -----------------------------
def extract_text_from_pdf(path: str) -> str:
    parts = []
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            t = p.extract_text() or ""
            if t.strip():
                parts.append(t)
    return "\n".join(parts)

def clean_text(txt: str) -> str:
    txt = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", " ", txt)
    txt = re.sub(r"\s{2,}", " ", txt)
    return txt.strip()

def chunk_text(text: str, tokenizer, max_tokens: int) -> List[str]:
    words, chunks, cur, cur_tok = text.split(), [], [], 0
    enc = tokenizer.encode
    for w in words:
        t = len(enc(w, add_special_tokens=False))
        if cur_tok + t > max_tokens and cur:
            chunks.append(" ".join(cur)); cur, cur_tok = [w], t
        else:
            cur.append(w); cur_tok += t
    if cur: chunks.append(" ".join(cur))
    return chunks

# -----------------------------
# 🧾 Summarize with chunking
# -----------------------------
def summarize_text(text: str, mode: str, detail: str, placeholder):
    summarizer = get_summarizer(mode)
    tok = summarizer.tokenizer

    cleaned = clean_text(text)
    model_max = getattr(tok, "model_max_length", 512)
    safe_limit = int(0.85 * model_max)
    chunks = chunk_text(cleaned, tok, safe_limit) or [cleaned]

    cfg = {"Concise": (60, 30), "Balanced": (120, 60), "Detailed": (160, 80)}
    max_len, min_len = cfg[detail]

    placeholder.info(f"📘 Processing {len(chunks)} chunk(s)…")
    out, start = [], time.time()

    for i, ch in enumerate(chunks, 1):
        s = summarizer(ch, max_length=max_len, min_length=min_len, do_sample=False)[0]["summary_text"]
        out.append(s)
        placeholder.progress(i / max(1, len(chunks)), text=f"Summarized {i}/{len(chunks)}")

    combined = " ".join(out)
    if len(combined.split()) > 220:
        combined = summarizer(combined, max_length=240, min_length=120, do_sample=False)[0]["summary_text"]

    return combined.strip(), int(time.time() - start)

# -----------------------------
# 📊 Strict Scoring + Breakdown
# -----------------------------
_FINANCE_TERMS = {
    "revenue","sales","profit","loss","ebitda","margin","cash","cash flow",
    "operating","net","expense","guidance","forecast","outlook","risk",
    "debt","interest","liquidity","dividend","capex","capital expenditure",
    "gross","yoy","qoq","growth","decline"
}
_UNCERTAIN_WORDS = {"maybe","possibly","i think","it seems","appears","could be","might","approximately"}
_STOPWORDS = {
    "the","a","an","and","or","of","for","to","in","on","with","is","are","was","were",
    "that","this","by","as","at","from","it","be","has","have","had","their","its","they"
}
def _tokenize(s: str):
    return re.findall(r"[A-Za-z%]+", s.lower())

def score_summary(summary: str) -> Tuple[float, bool, bool, Dict[str,float|int|bool]]:
    words = _tokenize(summary)
    wc = len(words)
    too_short = wc < 60
    sentences = max(1, summary.count(".") + summary.count("!") + summary.count("?"))
    avg_sent_len = wc / sentences

    breakdown: Dict[str, float|int|bool] = {}
    score = 6.0  # baseline

    coverage_hits = sum(1 for t in _FINANCE_TERMS if t in summary.lower())
    coverage_points = min(coverage_hits * 0.25, 2.5)
    score += coverage_points

    num_hits = len(re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b", summary))
    pct_hits = summary.count("%")
    numeric_points = min(0.75 + 0.15 * min(num_hits, 5) + 0.15 * min(pct_hits, 4), 1.5)
    score += numeric_points

    if 12 <= avg_sent_len <= 22:
        clarity_adj = 0.8
    elif avg_sent_len > 28:
        clarity_adj = -1.0
    elif avg_sent_len < 8:
        clarity_adj = -0.6
    else:
        clarity_adj = 0.0
    score += clarity_adj

    meaningful = [w for w in words if w not in _STOPWORDS]
    freq = Counter(meaningful)
    top = freq.most_common(5)
    dom_pen = sum(1 for w,c in top if c / max(1, len(meaningful)) > 0.06)
    repetition_penalty = min(dom_pen * 0.7, 2.0)
    score -= repetition_penalty

    uncertain = any(u in summary.lower() for u in _UNCERTAIN_WORDS)
    uncertainty_penalty = 1.5 if uncertain else 0.0
    score -= uncertainty_penalty

    if too_short:
        length_penalty = 2.0
    elif wc > 350:
        length_penalty = 1.0
    else:
        length_penalty = 0.0
    score -= length_penalty

    redundant_penalty = 0.5 if re.search(r"not only .* but also", summary.lower()) else 0.0
    score -= redundant_penalty

    score = max(1.0, min(10.0, round(score, 1)))

    breakdown.update({
        "word_count": wc,
        "sentences": sentences,
        "avg_sentence_len": round(avg_sent_len, 1),
        "coverage_hits": coverage_hits,
        "coverage_points": round(coverage_points, 2),
        "numeric_tokens": num_hits,
        "percent_tokens": pct_hits,
        "numeric_points": round(numeric_points, 2),
        "clarity_adj": round(clarity_adj, 2),
        "repetition_penalty": round(repetition_penalty, 2),
        "uncertain": uncertain,
        "uncertainty_penalty": round(uncertainty_penalty, 2),
        "length_penalty": round(length_penalty, 2),
        "redundant_penalty": round(redundant_penalty, 2),
        "final_score": score,
        "too_short": too_short,
    })
    return score, uncertain, too_short, breakdown

# -----------------------------
# 🗃️ DDL + I/O
# -----------------------------
def ensure_tables():
    with ENGINE.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.approved_summaries(
          id uuid PRIMARY KEY,
          original_text text NOT NULL,
          summary text NOT NULL,
          score int NOT NULL,
          flagged_uncertain boolean DEFAULT FALSE,
          flagged_too_short boolean DEFAULT FALSE,
          approved_by text NOT NULL,
          feedback text,
          approved_at timestamptz NOT NULL DEFAULT NOW()
        );"""))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS public.rejected_summaries(
          id uuid PRIMARY KEY,
          original_text text NOT NULL,
          rejected_summary text NOT NULL,
          score int NOT NULL,
          flagged_uncertain boolean DEFAULT FALSE,
          flagged_too_short boolean DEFAULT FALSE,
          feedback text NOT NULL,
          rejected_by text NOT NULL,
          rejected_at timestamptz NOT NULL DEFAULT NOW()
        );"""))
ensure_tables()

def insert_approved(payload: dict) -> tuple[bool, str | None, dict | None]:
    """Insert via SQLAlchemy and return the saved row."""
    try:
        new_id = str(uuid.uuid4())
        with ENGINE.begin() as conn:
            row = conn.execute(
                text("""
                    INSERT INTO public.approved_summaries
                      (id, original_text, summary, score, flagged_uncertain, flagged_too_short, approved_by, feedback, approved_at)
                    VALUES (:id,:orig,:sum,:score,:unc,:short,:by,:fb, NOW())
                    RETURNING id::text AS id, approved_by, score, feedback, approved_at
                """),
                dict(
                    id=new_id,
                    orig=payload["original"],
                    sum=payload["summary"],
                    score=int(payload["score"]),
                    unc=bool(payload["uncertain"]),
                    short=bool(payload["too_short"]),
                    by=payload["reviewer"].strip(),
                    fb=payload.get("reason", None),
                ),
            ).mappings().first()
        return True, None, dict(row)
    except Exception as e:
        return False, str(e), None

def insert_rejected(payload: dict) -> tuple[bool, str | None, dict | None]:
    try:
        new_id = str(uuid.uuid4())
        with ENGINE.begin() as conn:
            row = conn.execute(
                text("""
                    INSERT INTO public.rejected_summaries
                      (id, original_text, rejected_summary, score, flagged_uncertain, flagged_too_short, feedback, rejected_by, rejected_at)
                    VALUES (:id,:orig,:sum,:score,:unc,:short,:fb,:by, NOW())
                    RETURNING id::text AS id, rejected_by AS reviewer, score, feedback, rejected_at AS ts
                """),
                dict(
                    id=new_id,
                    orig=payload["original"],
                    sum=payload["summary"],
                    score=int(payload["score"]),
                    unc=bool(payload["uncertain"]),
                    short=bool(payload["too_short"]),
                    fb=payload["reason"].strip(),
                    by=payload["reviewer"].strip(),
                ),
            ).mappings().first()
        return True, None, dict(row)
    except Exception as e:
        return False, str(e), None

def save_review(decision: str, payload: dict):
    return insert_approved(payload) if decision == "Approve" else insert_rejected(payload)

# -----------------------------
# 🚀 App UI
# -----------------------------
st.title("Human-in-the-Loop Financial Summarizer")
st.caption("Accurate summaries for financial PDFs — local, private, and free.")

mode = st.sidebar.radio("Speed", ["Ultra-Fast","Fast","Quality"], index=0, key="mode")
detail = st.sidebar.select_slider("Detail", ["Concise","Balanced","Detailed"], value="Balanced", key="detail")
st.sidebar.markdown("---")
st.sidebar.info("Made with ❤️ by **Lavanya Srivastava**")

uploaded = st.file_uploader("📂 Upload a financial PDF", type=["pdf"])
doc_text = ""
if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded.read()); pdf_path = tmp.name
    with st.spinner("Extracting text…"):
        doc_text = extract_text_from_pdf(pdf_path)

if uploaded and not doc_text:
    st.error("⚠️ No readable text detected in this PDF.")

if uploaded and doc_text:
    st.success("✅ PDF uploaded and processed.")

    if st.button("🧠 Generate Summary", type="primary"):
        holder = st.empty()
        summary, elapsed = summarize_text(doc_text, st.session_state.mode, st.session_state.detail, holder)
        score, uncertain, too_short, breakdown = score_summary(summary)

        st.markdown("### 📋 Generated Summary")
        st.markdown(f"<div class='summary-box'>{summary}</div>", unsafe_allow_html=True)
        st.caption(f"Completed in {elapsed}s — Mode: {st.session_state.mode}, Detail: {st.session_state.detail}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Score", f"{score}/10")
        c2.metric("Uncertain Language", "Yes" if uncertain else "No")
        c3.metric("Too Short", "Yes" if too_short else "No")

        with st.expander("🔍 Why this score? (breakdown)", expanded=True):
            st.markdown(
                f"""
- **Word count / sentences / avg sentence length**: `{breakdown['word_count']}` / `{breakdown['sentences']}` / `{breakdown['avg_sentence_len']}`
- **Financial coverage hits**: `{breakdown['coverage_hits']}` → **+{breakdown['coverage_points']}**
- **Numbers / % tokens**: `{breakdown['numeric_tokens']}` / `{breakdown['percent_tokens']}` → **+{breakdown['numeric_points']}**
- **Clarity adjustment**: **{breakdown['clarity_adj']}**
- **Repetition penalty**: **-{breakdown['repetition_penalty']}**
- **Uncertainty present**: `{breakdown['uncertain']}` → **-{breakdown['uncertainty_penalty']}**
- **Length penalty**: **-{breakdown['length_penalty']}**
- **Redundant phrase penalty**: **-{breakdown['redundant_penalty']}**

**Final score**: **{breakdown['final_score']} / 10**
"""
            )

        st.divider()
        st.markdown("### ✅ Review & Store")
        st.caption("✅ To approve: fill **Your Name**, write a **Reason**, and if score < 7, tick **Approve anyway**.")

        with st.form(key="review_form", clear_on_submit=False):
            reviewer = st.text_input("Your Name")
            decision = st.radio("Decision", ["Approve","Reject"], horizontal=True)
            reason = st.text_area("Comment / Reason (required)", placeholder="Write a short, specific reason…")
            low_score = score < 7.0
            override_ok = True
            if decision == "Approve" and low_score:
                st.markdown(
                    "<div class='warn'>⚠️ This summary scored below 7. Tick the box to approve anyway.</div>",
                    unsafe_allow_html=True,
                )
                override_ok = st.checkbox("Approve anyway (override low score)")

            submitted = st.form_submit_button("📤 Submit Review", type="primary")

        if submitted:
            if not reviewer.strip():
                st.error("Please enter your name.")
            elif not reason.strip():
                st.error("Please provide a comment/reason.")
            elif decision == "Approve" and low_score and not override_ok:
                st.error("Low score approval requires ticking 'Approve anyway'.")
            else:
                ok, err, row = save_review(decision, {
                    "original": doc_text,
                    "summary": summary,
                    "score": breakdown["final_score"],
                    "uncertain": breakdown["uncertain"],
                    "too_short": breakdown["too_short"],
                    "reviewer": reviewer,
                    "reason": reason,
                })
                if ok:
                    st.success(
                        f"✅ Saved to DB. Row ID: `{row.get('id','?')}` | "
                        f"by: {row.get('approved_by') or row.get('reviewer')} | "
                        f"time: {row.get('approved_at') or row.get('ts')}"
                    )
                    st.session_state["_refresh_key"] = str(uuid.uuid4())
                    st.rerun()
                else:
                    st.error(f"❌ DB insert failed: {err}")

# -----------------------------
# 📜 History (always fresh)
# -----------------------------
st.markdown("---")
st.markdown("### 📊 Summary Review History")

refresh_token = st.session_state.get("_refresh_key", "init")

def load_history(_token: str) -> pd.DataFrame:
    with ENGINE.connect() as conn:
        return pd.read_sql(
            """
            WITH hist AS (
              SELECT id::text AS id, summary AS text, score, approved_by AS reviewer,
                     feedback, approved_at AS ts, 'Approved' AS status
              FROM public.approved_summaries
              UNION ALL
              SELECT id::text AS id, rejected_summary AS text, score, rejected_by AS reviewer,
                     feedback, rejected_at AS ts, 'Rejected' AS status
              FROM public.rejected_summaries
            )
            SELECT * FROM hist
            ORDER BY ts DESC NULLS LAST, id DESC;
            """,
            conn,
        )

try:
    df_hist = load_history(refresh_token)
    st.dataframe(df_hist, use_container_width=True, key=f"hist_{refresh_token}")
except Exception as e:
    st.error(f"History load error: {e}")

if st.button("↻ Refresh history"):
    st.session_state["_refresh_key"] = str(uuid.uuid4())
    st.rerun()

st.markdown("---")
st.markdown("**— Made with ❤️ by Lavanya Srivastava**")
