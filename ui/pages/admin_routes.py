import streamlit as st
from ui.pages.admin_catalog_pages import render_admin_activity_catalog_page, render_admin_food_catalog_page


def render_admin_routes() -> None:
    st.sidebar.title("Panou Administrator")
    st.sidebar.info(f"Autentificat ca:\n{st.session_state['logged_in_email']}")

    menu = ["Gestiune Alimente", "Gestiune Activități"]
    choice = st.sidebar.selectbox("Meniu Admin", menu)

    if choice == "Gestiune Alimente":
        render_admin_food_catalog_page()
    elif choice == "Gestiune Activități":
        render_admin_activity_catalog_page()

    st.sidebar.divider()
    if st.sidebar.button("Deconectare", width="stretch", type="tertiary"):
        st.session_state.clear()
        st.rerun()
