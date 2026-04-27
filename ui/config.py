from pathlib import Path
import streamlit as st


def load_local_css(file_name: str) -> None:
    """Loads local CSS styles if the asset file exists."""
    css_path = Path(__file__).resolve().parents[1] / file_name
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def configure_page() -> None:
    """Applies Streamlit page configuration and project CSS."""
    st.set_page_config(page_title="MacroSense", layout="centered")
    load_local_css("assets/style.css")
