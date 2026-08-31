import streamlit as st
from ui.config import configure_page
from ui.language import initialize_language
from ui.pages.admin_routes import render_admin_routes
from ui.pages.auth_page import render_auth_page
from ui.pages.user_routes import render_user_routes

configure_page()
initialize_language()

APP_LAST_RENDERED_ROLE_KEY = "app_last_rendered_role"

if "role" not in st.session_state:
    st.session_state["role"] = None

if APP_LAST_RENDERED_ROLE_KEY not in st.session_state:
    st.session_state[APP_LAST_RENDERED_ROLE_KEY] = st.session_state["role"]

current_role = st.session_state["role"]
if st.session_state.get(APP_LAST_RENDERED_ROLE_KEY) != current_role:
    st.session_state[APP_LAST_RENDERED_ROLE_KEY] = current_role
    st.rerun()

route_slot = st.empty()
with route_slot.container():
    if current_role is None:
        render_auth_page()
    elif current_role == "admin":
        render_admin_routes()
    elif current_role == "user":
        render_user_routes()
