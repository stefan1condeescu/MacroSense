"""Simple session-based language selection for the MacroSense UI."""

import streamlit as st

from ui.translations_ro import ROMANIAN_TRANSLATIONS


LANGUAGE_SESSION_KEY = "language"
DEFAULT_LANGUAGE = "ro"
SUPPORTED_LANGUAGES = ("en", "ro")


def initialize_language() -> str:
    """Ensure the session contains a supported language and return it."""
    language = st.session_state.get(LANGUAGE_SESSION_KEY)
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE
        st.session_state[LANGUAGE_SESSION_KEY] = language
    return language


def translate(source_text: str) -> str:
    """Translate English UI source text using the active session language."""
    if initialize_language() == "ro":
        return ROMANIAN_TRANSLATIONS.get(source_text, source_text)
    return source_text
