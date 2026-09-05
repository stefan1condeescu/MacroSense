"""Simple session-based language selection for the MacroSense UI."""

import os

import streamlit as st

from ui.translations_ro import ROMANIAN_TRANSLATIONS


LANGUAGE_SESSION_KEY = "language"
DEFAULT_LANGUAGE_ENV_VAR = "MACROSENSE_DEFAULT_LANGUAGE"
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "ro")
LANGUAGE_LABELS = {
    "en": "English",
    "ro": "Română",
}


def get_configured_default_language() -> str:
    """Return a supported language from local configuration or English."""
    configured_language = os.getenv(
        DEFAULT_LANGUAGE_ENV_VAR,
        DEFAULT_LANGUAGE,
    ).strip().lower()
    if configured_language in SUPPORTED_LANGUAGES:
        return configured_language
    return DEFAULT_LANGUAGE


def initialize_language() -> str:
    """Ensure the session contains a supported language and return it."""
    language = st.session_state.get(LANGUAGE_SESSION_KEY)
    if language not in SUPPORTED_LANGUAGES:
        language = get_configured_default_language()
        st.session_state[LANGUAGE_SESSION_KEY] = language
    return language


def display_language_name(language_code: str) -> str:
    """Keep each language's native name recognizable in either UI language."""
    return LANGUAGE_LABELS.get(language_code, language_code)


def render_language_selector() -> str:
    """Render the global language selector and return its stable code."""
    initialize_language()
    selected_language = st.sidebar.segmented_control(
        translate("Language"),
        options=SUPPORTED_LANGUAGES,
        format_func=display_language_name,
        key=LANGUAGE_SESSION_KEY,
        required=True,
        width="stretch",
    )
    if selected_language in SUPPORTED_LANGUAGES:
        return selected_language
    return initialize_language()


def clear_session_preserving_language() -> None:
    """Clear authentication and navigation state without changing language."""
    selected_language = initialize_language()
    st.session_state.clear()
    st.session_state[LANGUAGE_SESSION_KEY] = selected_language


def translate(source_text: str, **format_values: object) -> str:
    """Translate English UI source text and insert optional dynamic values."""
    if initialize_language() == "ro":
        translated_text = ROMANIAN_TRANSLATIONS.get(source_text, source_text)
    else:
        translated_text = source_text
    if format_values:
        return translated_text.format(**format_values)
    return translated_text
