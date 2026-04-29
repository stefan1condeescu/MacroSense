import streamlit as st
from ui.pages.activity_journal_page import render_activity_journal_page
from ui.pages.custom_meals_page import render_custom_meals_page
from ui.pages.dashboard_page import render_dashboard_page
from ui.pages.food_journal_page import render_food_journal_page
from ui.pages.user_catalog_pages import render_user_activity_catalog_page, render_user_food_catalog_page
from ui.pages.weight_journal_page import render_weight_journal_page


def render_user_routes() -> None:
    st.sidebar.title(f"Salut, {st.session_state['user_full_name']}!")

    menu = ["Acasă", "Jurnal Alimentar", "Jurnal Activități", "Jurnal Greutate", "Mese Personalizate", "Catalog Alimente", "Catalog Activități"]
    choice = st.sidebar.selectbox("Meniu Principal", menu)

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
    elif choice == "Catalog Alimente":
        render_user_food_catalog_page()
    elif choice == "Catalog Activități":
        render_user_activity_catalog_page()

    st.sidebar.divider()
    if st.sidebar.button("Deconectare", width="stretch", type="tertiary"):
        st.session_state.clear()
        st.rerun()
