import streamlit as st
from auth import create_user, authenticate_user

st.set_page_config(page_title="MacroSense", layout="centered")
st.title("MacroSense - Nutriție & Fitness")

# Sistemul de rutare a paginilor
menu = ["Autentificare", "Creare Cont"]
choice = st.sidebar.selectbox("Navigație", menu)

if choice == "Creare Cont":
    st.subheader("Creează un profil nou")
    with st.form("register_form", clear_on_submit=True):
        email = st.text_input("Adresă Email")
        password = st.text_input("Parolă", type="password")
        full_name = st.text_input("Nume complet")
        
        col1, col2 = st.columns(2)
        with col1:
            height = st.number_input("Înălțime (cm)", min_value=100.0, max_value=250.0, step=0.1)
            age = st.number_input("Vârstă", min_value=10, max_value=120, step=1)
        with col2:
            gender = st.selectbox("Sex", ["M", "F"])
            goal = st.selectbox("Obiectiv", ["slăbire", "menținere", "creștere"])
            
        submit = st.form_submit_button("Înregistrează-te")
        
        if submit:
            if create_user(email, password, full_name, height, age, gender, goal):
                st.success("Cont creat cu succes! Mergi la Autentificare pentru a te loga.")

elif choice == "Autentificare":
    st.subheader("Intră în contul tău")
    email = st.text_input("Email")
    password = st.text_input("Parolă", type="password")
    
    if st.button("Login"):
        user = authenticate_user(email, password)
        if user:
            st.success(f"Autentificare reușită! Bun venit, {user[1]}!")
            # Salvăm ID-ul utilizatorului în memoria aplicației
            st.session_state['user_id'] = user[0]
            st.session_state['user_name'] = user[1]
        else:
            st.error("Email sau parolă incorecte.")