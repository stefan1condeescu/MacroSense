import streamlit as st
import hashlib
from database import get_connection

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, password, full_name, height, age, gender, goal):
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO users (email, password_hash, full_name, height_cm, age, gender, goal) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (email, hash_password(password), full_name, height, age, gender, goal)
            )
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Eroare la creare cont (Email-ul ar putea exista deja): {e}")
            return False
        finally:
            conn.close()
    return False

def authenticate_user(email, password):
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, full_name FROM users WHERE email = %s AND password_hash = %s", 
            (email, hash_password(password))
        )
        user = cursor.fetchone()
        conn.close()
        return user
    return None