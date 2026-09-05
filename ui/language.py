"""Simple session-based language selection for the MacroSense UI."""

import base64
import os
from functools import lru_cache
from pathlib import Path

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
TRANSLATED_SELECTIONS_KEY = "_translated_selection_keys"


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
    # Keep this value independent of the removed, older selector widget's lifecycle.
    st.session_state[LANGUAGE_SESSION_KEY] = language
    return language


def display_language_name(language_code: str) -> str:
    """Keep each language's native name recognizable in either UI language."""
    return LANGUAGE_LABELS.get(language_code, language_code)


def translated_selection_key(key: str) -> str:
    """Register a choice whose displayed options change with the language."""
    keys = st.session_state.setdefault(TRANSLATED_SELECTIONS_KEY, set())
    keys.add(key)
    return key


def change_language(language_code: str) -> None:
    """Preserve selected values and send their new labels to the browser."""
    if language_code not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language_code}")

    # Read all selections while their previous-language deserializers are active.
    selections = {
        key: st.session_state[key]
        for key in st.session_state.get(TRANSLATED_SELECTIONS_KEY, ())
        if key in st.session_state
    }
    # Explicit assignment tells Streamlit to refresh each browser-side selection.
    for key, value in selections.items():
        st.session_state[key] = value
    st.session_state[LANGUAGE_SESSION_KEY] = language_code


def normalize_navigation_selection(key: str, pages: dict) -> None:
    """Recover an older session containing a displayed label instead of an ID."""
    selected_page = st.session_state.get(key)
    if selected_page is None or selected_page in pages:
        return
    for page_id, page in pages.items():
        source_label = page["label"] if isinstance(page, dict) else page
        if selected_page in (
            source_label,
            ROMANIAN_TRANSLATIONS.get(source_label, source_label),
        ):
            st.session_state[key] = page_id
            return
    st.session_state[key] = next(iter(pages))


@lru_cache(maxsize=2)
def _flag_image_label(language_code: str) -> str:
    """Use bundled flag pictures without external requests or emoji rendering."""
    flag_name = {"en": "gb", "ro": "ro"}[language_code]
    flag_path = Path(__file__).resolve().parents[1] / "assets" / "flags" / f"{flag_name}.svg"
    encoded_flag = base64.b64encode(flag_path.read_bytes()).decode("ascii")
    return f"![{display_language_name(language_code)}](data:image/svg+xml;base64,{encoded_flag})"


def render_language_selector() -> str:
    """Render two compact, accessible flag buttons and return the language code."""
    selected_language = initialize_language()
    with st.sidebar.container(key="language_selector", horizontal=True, gap="small"):
        for language_code in SUPPORTED_LANGUAGES:
            st.button(
                _flag_image_label(language_code),
                key=f"language_{language_code}",
                help=display_language_name(language_code),
                type="primary" if language_code == selected_language else "secondary",
                on_click=change_language,
                args=(language_code,),
                width="content",
            )
    return selected_language


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
