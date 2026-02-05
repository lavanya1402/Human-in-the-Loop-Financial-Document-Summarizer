# app/db.py
from __future__ import annotations

import os
from urllib.parse import urlparse

import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# -----------------------------
# Secrets + ENV helpers
# -----------------------------
def _sget(key: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(key, default)).strip()
    except Exception:
        return default

def _eget(key: str, default: str = "") -> str:
    return str(os.getenv(key, default)).strip()

def is_cloud() -> bool:
    # Streamlit Cloud sets these; local usually doesn't.
    return bool(_eget("STREAMLIT_SERVER_PORT") or _eget("STREAMLIT_CLOUD") or _sget("STREAMLIT_CLOUD"))

def get_debug_flag() -> bool:
    v = _sget("DEBUG_DB", "") or _eget("DEBUG_DB", "0")
    return str(v).strip().lower() in ("1", "true", "yes", "y")

def get_db_urls() -> dict:
    """
    Provide 2 URLs:
    - DB_URL_POOLER: for normal app queries (cloud recommended)
    - DB_URL_MIGRATIONS: for DDL/migrations (direct 5432)
    Also allow local .env fallback:
    - DB_URL (pooler or direct)
    - DB_URL_DIRECT (direct 5432)
    """
    pooler = _sget("DB_URL_POOLER", "") or _eget("DB_URL_POOLER", "") or _eget("DB_URL", "")
    migrations = _sget("DB_URL_MIGRATIONS", "") or _eget("DB_URL_MIGRATIONS", "") or _eget("DB_URL_DIRECT", "")
    return {"pooler": pooler, "migrations": migrations}

def _parse_db_info(url: str) -> dict:
    u = urlparse(url)
    return {
        "host": u.hostname,
        "port": u.port,
        "user": u.username,
        "db": u.path,
        "is_pooler": bool(u.hostname and "pooler.supabase.com" in u.hostname),
    }

def _make_engine(db_url: str) -> Engine:
    connect_args = {
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=3,
        max_overflow=2,
        pool_timeout=30,
        connect_args=connect_args,
    )

def _smoke_test(engine: Engine) -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1;")).fetchone()

@st.cache_resource(show_spinner=False)
def get_engine_and_info() -> tuple[Engine, Engine | None, dict]:
    """
    ENGINE: used for queries
      - cloud: prefer pooler
      - local: can still use pooler or direct; we just pick pooler if provided

    MIGRATIONS_ENGINE: used for CREATE TABLE / DDL
      - must be direct 5432 if provided (recommended)
    """
    urls = get_db_urls()
    pooler = urls["pooler"]
    migrations_url = urls["migrations"]

    if not pooler:
        st.error("❌ DB_URL_POOLER missing. Set it in Streamlit Secrets (cloud) or .env (local).")
        st.stop()

    # ENGINE (pooler)
    try:
        engine = _make_engine(pooler)
        _smoke_test(engine)
        info = _parse_db_info(pooler)
        info["selected"] = "pooler"
    except Exception as e:
        st.error(f"❌ Pooler connection failed: {e}")
        st.stop()

    # MIGRATIONS_ENGINE (direct) optional but strongly recommended
    migrations_engine = None
    if migrations_url:
        try:
            migrations_engine = _make_engine(migrations_url)
            _smoke_test(migrations_engine)
        except Exception:
            # Don't stop the app; just warn. We'll fallback to ENGINE for DDL (not ideal).
            migrations_engine = None

    return engine, migrations_engine, info

ENGINE, MIGRATIONS_ENGINE, DB_INFO = get_engine_and_info()

# Backward-compatible exports (for older imports)
def get_engine() -> Engine:
    return ENGINE

def get_migrations_engine() -> Engine | None:
    return MIGRATIONS_ENGINE

def show_db_debug_ui():
    if not get_debug_flag():
        return
    with st.expander("🔐 DB Debug (safe)", expanded=False):
        st.write("selected:", DB_INFO.get("selected"))
        st.write("host:", DB_INFO.get("host"))
        st.write("port:", DB_INFO.get("port"))
        st.write("user:", DB_INFO.get("user"))
        st.write("db:", DB_INFO.get("db"))
        st.write("pooler:", DB_INFO.get("is_pooler"))
