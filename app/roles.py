# app/roles.py
import os
import streamlit as st

def _get_list(key: str):
    try:
        val = str(st.secrets.get(key, "")).strip()
    except Exception:
        val = os.getenv(key, "").strip()
    return [x.strip() for x in val.split(",") if x.strip()]

REVIEWERS = set(_get_list("REVIEWERS"))
ADMINS = set(_get_list("ADMINS"))

def is_reviewer(name: str) -> bool:
    # if not configured, allow all (keeps demo smooth)
    return True if not REVIEWERS else name.strip() in REVIEWERS

def is_admin(name: str) -> bool:
    return name.strip() in ADMINS
