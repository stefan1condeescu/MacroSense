import streamlit as st
from ui.config import configure_page

configure_page()

from ui.pages.admin_routes import render_admin_routes
from ui.pages.auth_page import render_auth_page
from ui.pages.user_routes import render_user_routes


if "role" not in st.session_state:
    st.session_state["role"] = None

if st.session_state["role"] is None:
    render_auth_page()
elif st.session_state["role"] == "admin":
    render_admin_routes()
elif st.session_state["role"] == "user":
    render_user_routes()
