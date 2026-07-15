import os

import psycopg2
from psycopg2.extensions import connection
import streamlit as st


def _get_setting(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    try:
        value = st.secrets.get(name)
    except Exception:
        return default

    return value or default


def get_connection() -> connection | None:
    """
    Establishes and returns a connection to the PostgreSQL database.
    Returns None if the connection fails.
    """
    password = _get_setting("DB_PASSWORD")
    if not password:
        st.error(
            "Database configuration error: set DB_PASSWORD in the environment "
            "or in .streamlit/secrets.toml."
        )
        return None

    try:
        conn = psycopg2.connect(
            dbname=_get_setting("DB_NAME", "macrosense_db"),
            user=_get_setting("DB_USER", "postgres"),
            password=password,
            host=_get_setting("DB_HOST", "localhost"),
            port=_get_setting("DB_PORT", "5432"),
        )
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None
