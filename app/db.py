# app/db.py
from urllib.parse import urlparse
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import get_db_urls, is_cloud, get_debug_flag

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
    """
    Production pooling:
    - small pool sizes (Streamlit reruns a lot)
    - pre_ping avoids stale conns
    - recycle avoids long-idle broken links
    - keepalives help on some networks (psycopg2 supports these args)
    """
    connect_args = {
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        # Optional safety: uncomment if you want query timeout protection
        # "options": "-c statement_timeout=15000",
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
def get_engine_and_info():
    """
    Auto-switch:
      - On cloud: prefer pooler; fallback to direct (rarely works)
      - On local: prefer direct; fallback to pooler if provided
    """
    urls = get_db_urls()
    pooler = urls["pooler"]
    direct = urls["direct"]

    order = []
    if is_cloud():
        if pooler: order.append(("pooler", pooler))
        if direct: order.append(("direct", direct))
    else:
        if direct: order.append(("direct", direct))
        if pooler: order.append(("pooler", pooler))

    if not order:
        st.error("❌ DB URL missing. Set DB_URL_POOLER (cloud) and/or DB_URL_DIRECT (local).")
        st.stop()

    last_err = None
    for label, url in order:
        try:
            eng = _make_engine(url)
            _smoke_test(eng)
            info = _parse_db_info(url)
            info["selected"] = label
            return eng, info
        except Exception as e:
            last_err = e

    st.error(f"❌ Could not connect using any DB URL. Last error: {last_err}")
    st.stop()

ENGINE, DB_INFO = get_engine_and_info()

def show_db_debug_ui():
    """
    Safe debug: only show when DEBUG_DB enabled.
    Shows host/port/user only (no passwords).
    """
    if not get_debug_flag():
        return

    with st.expander("🔐 DB Debug (safe)", expanded=False):
        st.write("selected:", DB_INFO.get("selected"))
        st.write("host:", DB_INFO.get("host"))
        st.write("port:", DB_INFO.get("port"))
        st.write("user:", DB_INFO.get("user"))
        st.write("db:", DB_INFO.get("db"))
        st.write("pooler:", DB_INFO.get("is_pooler"))
