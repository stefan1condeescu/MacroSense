import psycopg2
import streamlit as st

def get_connection():
    try:
        conn = psycopg2.connect(
            dbname="macrosense_db",
            user="postgres",
            password="9999",  
            host="localhost",
            port="5432"
        )
        return conn
    except Exception as e:
        st.error(f"Eroare la conectarea la baza de date: {e}")
        return None