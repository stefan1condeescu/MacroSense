import streamlit as st
from database import get_connection

st.title("MacroSense")
st.write("Se verifică legătura cu PostgreSQL...")

# Încercăm să ne conectăm
conn = get_connection()

if conn:
    st.success("Conexiunea la baza de date a reușit cu succes! 🎉")
    conn.close() # E o practică bună să închidem ușa după ce am terminat