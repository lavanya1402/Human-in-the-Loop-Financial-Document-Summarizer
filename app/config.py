# app/config.py
import os
import streamlit as st
from dotenv import load_dotenv


load_dotenv()  # local support; safe on cloud too

def _safe_secrets_get(key: str, default: str = "") -> str:
    """Streamlit secrets read that won't crash locally if secrets.toml is missing."""
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        return default
    return default

def is_cloud() -> bool:
    """
    Heuristic: if Streamlit secrets exist (cloud commonly uses it),
    or if Streamlit sets headless env.
    """
    try:
        if hasattr(st, "secrets") and len(st.secrets) > 0:
            return True
    except Exception:
        pass
    return os.getenv("STREAMLIT_SERVER_HEADLESS", "").lower() in ("true", "1")

def get_debug_flag() -> bool:
    # Turn debug on only when explicitly enabled (never by default)
    val = _safe_secrets_get("DEBUG_DB", "") or os.getenv("DEBUG_DB", "")
    return str(val).strip().lower() in ("1", "true", "yes", "on")

def get_db_urls() -> dict:
    """
    Provide both URLs so we can fallback:
    - DB_URL_POOLER: for cloud (IPv4)
    - DB_URL_DIRECT: for local (IPv6)
    You can set either one; DB_URL is supported too for backward compatibility.
    """
    pooler = (
        _safe_secrets_get("DB_URL_POOLER", "").strip()
        or os.getenv("DB_URL_POOLER", "").strip()
    )
    direct = (
        _safe_secrets_get("DB_URL_DIRECT", "").strip()
        or os.getenv("DB_URL_DIRECT", "").strip()
    )

    # Backward compatibility: if user set only DB_URL, treat it as "whatever they gave"
    generic = (
        _safe_secrets_get("DB_URL", "").strip()
        or os.getenv("DB_URL", "").strip()
    )

    # If only DB_URL is given, try to infer whether it is pooler/direct
    if generic and not pooler and not direct:
        if "pooler.supabase.com" in generic or ":6543" in generic:
            pooler = generic
        else:
            direct = generic

    return {"pooler": pooler, "direct": direct}
