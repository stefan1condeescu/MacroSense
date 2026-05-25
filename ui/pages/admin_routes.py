import html
import streamlit as st
from ui.page_theme import apply_page_theme, get_admin_page_theme
from ui.pages.admin_catalog_pages import render_admin_activity_catalog_page, render_admin_food_catalog_page


def build_admin_identity_html(email: str) -> str:
    """Builds non-clickable sidebar identity text for administrators."""
    safe_email = html.escape(str(email or "-"), quote=True)
    return (
        '<div class="admin-auth-card">'
        "<span>Autentificat ca:</span>"
        f"<strong>{safe_email}</strong>"
        "</div>"
    )


def render_admin_routes() -> None:
    st.sidebar.title("Panou Administrator")
    st.sidebar.markdown(
        build_admin_identity_html(st.session_state.get("logged_in_email")),
        unsafe_allow_html=True,
    )

    menu = ["Gestiune Alimente", "Gestiune Activități"]
    choice = st.sidebar.selectbox("Meniu Admin", menu)
    apply_page_theme(get_admin_page_theme(choice))

    if choice == "Gestiune Alimente":
        render_admin_food_catalog_page()
    elif choice == "Gestiune Activități":
        render_admin_activity_catalog_page()

    st.sidebar.divider()
    if st.sidebar.button("Deconectare", width="stretch", type="tertiary"):
        st.session_state.clear()
        st.rerun()
