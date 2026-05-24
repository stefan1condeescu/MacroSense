import streamlit as st
from ui.pages.activity_journal_page import (
    ACTIVITY_JOURNAL_DATE_KEY,
    render_activity_journal_page,
)
from ui.pages.custom_meals_page import render_custom_meals_page
from ui.pages.dashboard_page import render_dashboard_page
from ui.pages.food_journal_page import FOOD_JOURNAL_DATE_KEY, render_food_journal_page
from ui.pages.user_catalog_pages import render_user_activity_catalog_page, render_user_food_catalog_page
from ui.pages.weight_journal_page import (
    WEIGHT_LOG_ADD_DATE_KEY_PREFIX,
    render_weight_journal_page,
)
from ui.pages.what_if_page import render_what_if_page


USER_MENU_OPTIONS = [
    "Acasă",
    "Jurnal Alimentar",
    "Jurnal Activități",
    "Jurnal Greutate",
    "Mese Personalizate",
    "Simulator What-if",
    "Catalog Alimente",
    "Catalog Activități",
]
USER_LAST_RENDERED_PAGE_KEY = "user_last_rendered_page"
JOURNAL_DATE_SELECTOR_KEYS = {
    FOOD_JOURNAL_DATE_KEY,
    ACTIVITY_JOURNAL_DATE_KEY,
    "weight_log_add_date",
}
JOURNAL_DATE_SELECTOR_PREFIXES = (WEIGHT_LOG_ADD_DATE_KEY_PREFIX,)


def render_user_routes() -> None:
    st.sidebar.title(f"Salut, {st.session_state['user_full_name']}!")

    choice = st.sidebar.radio("Meniu Principal", USER_MENU_OPTIONS, key="user_main_menu")

    last_rendered_page = st.session_state.get(USER_LAST_RENDERED_PAGE_KEY)
    if last_rendered_page is None:
        st.session_state[USER_LAST_RENDERED_PAGE_KEY] = choice
    elif last_rendered_page != choice:
        _reset_journal_date_selectors()
        st.session_state[USER_LAST_RENDERED_PAGE_KEY] = choice
        st.rerun()

    page_slot = st.empty()
    with page_slot.container():
        _render_selected_user_page(choice)

    st.sidebar.divider()
    if st.sidebar.button("Deconectare", width="stretch", type="tertiary"):
        st.session_state.clear()
        st.rerun()


def _reset_journal_date_selectors() -> None:
    for key in list(st.session_state.keys()):
        if key in JOURNAL_DATE_SELECTOR_KEYS or key.startswith(
            JOURNAL_DATE_SELECTOR_PREFIXES
        ):
            del st.session_state[key]


def _render_selected_user_page(choice: str) -> None:
    if choice == "Acasă":
        render_dashboard_page()
    elif choice == "Jurnal Alimentar":
        render_food_journal_page()
    elif choice == "Jurnal Activități":
        render_activity_journal_page()
    elif choice == "Jurnal Greutate":
        render_weight_journal_page()
    elif choice == "Mese Personalizate":
        render_custom_meals_page()
    elif choice == "Simulator What-if":
        render_what_if_page()
    elif choice == "Catalog Alimente":
        render_user_food_catalog_page()
    elif choice == "Catalog Activități":
        render_user_activity_catalog_page()
