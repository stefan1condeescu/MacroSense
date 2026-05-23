import streamlit as st
from ui.pages.activity_journal_page import render_activity_journal_page
from ui.pages.custom_meals_page import render_custom_meals_page
from ui.pages.dashboard_page import render_dashboard_page
from ui.pages.food_journal_page import render_food_journal_page
from ui.pages.user_catalog_pages import render_user_activity_catalog_page, render_user_food_catalog_page
from ui.pages.weight_journal_page import render_weight_journal_page
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


def render_user_routes() -> None:
    st.sidebar.title(f"Salut, {st.session_state['user_full_name']}!")

    choice = st.sidebar.radio("Meniu Principal", USER_MENU_OPTIONS, key="user_main_menu")

    last_rendered_page = st.session_state.get(USER_LAST_RENDERED_PAGE_KEY)
    if last_rendered_page is None:
        st.session_state[USER_LAST_RENDERED_PAGE_KEY] = choice
    elif last_rendered_page != choice:
        st.session_state[USER_LAST_RENDERED_PAGE_KEY] = choice
        st.rerun()

    page_slot = st.empty()
    with page_slot.container():
        _render_selected_user_page(choice)

    st.sidebar.divider()
    if st.sidebar.button("Deconectare", width="stretch", type="tertiary"):
        st.session_state.clear()
        st.rerun()


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
