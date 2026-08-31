import html
import streamlit as st
from ui.language import translate
from ui.page_theme import apply_page_theme, get_admin_page_theme
from ui.pages.admin_catalog_pages import render_admin_activity_catalog_page, render_admin_food_catalog_page


ADMIN_PAGES = {
    "food_catalog": {
        "label": "Food management",
        "render": render_admin_food_catalog_page,
    },
    "activity_catalog": {
        "label": "Activity management",
        "render": render_admin_activity_catalog_page,
    },
}
ADMIN_MENU_OPTIONS = tuple(ADMIN_PAGES)


def build_admin_identity_html(email: str) -> str:
    """Builds non-clickable sidebar identity text for administrators."""
    safe_email = html.escape(str(email or "-"), quote=True)
    return (
        '<div class="admin-auth-card">'
        "<span>Autentificat ca:</span>"
        f"<strong>{safe_email}</strong>"
        "</div>"
    )


def display_admin_page_name(page_id: str) -> str:
    """Return the translated label for a stable administrator page ID."""
    page = ADMIN_PAGES.get(page_id)
    if page is None:
        return page_id
    return translate(str(page["label"]))


def _render_selected_admin_page(page_id: str) -> None:
    ADMIN_PAGES[page_id]["render"]()


def render_admin_routes() -> None:
    st.sidebar.title("Panou Administrator")
    st.sidebar.markdown(
        build_admin_identity_html(st.session_state.get("logged_in_email")),
        unsafe_allow_html=True,
    )

    selected_page = st.sidebar.selectbox(
        translate("Admin menu"),
        options=list(ADMIN_PAGES),
        format_func=display_admin_page_name,
        key="admin_main_menu",
    )
    apply_page_theme(get_admin_page_theme(selected_page))
    _render_selected_admin_page(selected_page)

    st.sidebar.divider()
    if st.sidebar.button("Deconectare", width="stretch", type="tertiary"):
        st.session_state.clear()
        st.rerun()
