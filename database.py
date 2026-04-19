import psycopg2
from psycopg2.extensions import connection
import streamlit as st

def get_connection() -> connection:
    """
    Establishes and returns a connection to the PostgreSQL database.
    Returns None if the connection fails.
    """
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
        st.error(f"Database connection error: {e}")
        return None