import streamlit as st
from models.authentication import User, UserAccount

# ==========================================
# UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="MacroSense", layout="centered")

# ==========================================
# SESSION STATE MANAGEMENT
# ==========================================
if 'logged_in_email' not in st.session_state:
    
    # --- GUEST MENU (LOGIN / REGISTER) ---
    st.title("MacroSense")
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
                # OOP Integration: Instantiate a User object
                new_user = User(email, full_name, height, age, gender, goal)
                if new_user.register(password):
                    st.success("Cont creat cu succes! Mergi la Autentificare pentru a te loga.")
                else:
                    st.error("Eroare la creare. Probabil acest email există deja.")

    elif choice == "Autentificare":
        st.subheader("Intră în contul tău")
        email = st.text_input("Email")
        password = st.text_input("Parolă", type="password")
        
        if st.button("Login"):
            # OOP Integration: Instantiate a generic UserAccount to authenticate
            account = UserAccount(email)
            if account.authenticate(password):
                # Fetch full user details after successful auth
                logged_user = User.get_user_by_email(email)
                if logged_user:
                    st.session_state['logged_in_email'] = logged_user.email
                    st.session_state['user_full_name'] = logged_user.full_name
                    st.rerun()
            else:
                st.error("Email sau parolă incorecte.")

else:
    # --- LOGGED IN MENU ---
    st.sidebar.title(f"Salut, {st.session_state['user_full_name']}!")
    menu = ["Deconectare"]
    choice = st.sidebar.selectbox("Meniu Principal", menu)
        
    if choice == "Deconectare":
        st.session_state.clear()
        st.rerun()