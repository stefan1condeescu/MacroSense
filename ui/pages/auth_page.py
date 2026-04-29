import streamlit as st
from models.authentication import Admin, User
from models.tracking import WeightLog

def render_auth_page() -> None:
    st.sidebar.title("MacroSense")
    menu = ["Autentificare", "Creare Cont"]
    choice = st.sidebar.selectbox("Navigație", menu)
    
    if choice == "Creare Cont":
        st.subheader("Creează un profil nou")
        with st.form("register_form"):
            email = st.text_input("Adresă Email")
            password = st.text_input("Parolă", type="password")
            full_name = st.text_input("Nume complet")
            col1, col2 = st.columns(2)
            with col1:
                height = st.number_input("Înălțime (cm)", min_value=100.0, max_value=250.0, step=0.1)
                weight = st.number_input(
                    "Greutate curentă (kg)",
                    value=70.0,
                    step=0.1,
                    help=(
                        "Greutatea trebuie să fie între "
                        f"{WeightLog.MIN_WEIGHT_KG:.0f} și {WeightLog.MAX_WEIGHT_KG:.0f} kg."
                    )
                )
                age = st.number_input("Vârstă", min_value=10, max_value=120, step=1)
            with col2:
                gender = st.selectbox("Sex", ["M", "F"])
                goal = st.selectbox("Obiectiv", ["slăbire", "menținere", "creștere"])
            submit_register = st.form_submit_button("Înregistrează-te", width="stretch", type="primary")
    
        if submit_register:
            if not email.strip() or not password.strip() or not full_name.strip():
                st.warning("Te rog să completezi toate câmpurile obligatorii (Email, Parolă, Nume complet)!")
            elif len(password) < 6:
                st.warning("Parola trebuie să conțină cel puțin 6 caractere!")
            elif "@" not in email or email.count("@") != 1 or "." not in email.split("@")[1]:
                st.warning("Te rog introdu o adresă de email validă!")
            elif not WeightLog.MIN_WEIGHT_KG <= float(weight) <= WeightLog.MAX_WEIGHT_KG:
                st.error(
                    "Greutatea trebuie să fie între "
                    f"{WeightLog.MIN_WEIGHT_KG:.0f} și {WeightLog.MAX_WEIGHT_KG:.0f} kg."
                )
            else:
                new_user = User(email, full_name, height, age, gender, goal)
                if new_user.register(password, weight):
                    st.success("Cont creat cu succes! Te poți autentifica acum.")
                else:
                    st.error("Eroare la creare. Probabil acest email există deja.")
       
    elif choice == "Autentificare":
        st.subheader("Intră în contul tău")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Parolă", type="password")
            submit_login = st.form_submit_button("Login", type="primary")
            
            if submit_login:
                # Frontend Validation for Login
                if not email.strip() or not password.strip():
                    st.warning("Te rog să introduci adresa de email și parola.")
                else:
                    # 1. Attempt to authenticate as Admin
                    admin_account = Admin(email)
                    if admin_account.authenticate(password):
                        st.session_state['role'] = 'admin'
                        st.session_state['logged_in_email'] = admin_account.email
                        st.session_state['admin_access_level'] = admin_account.access_level
                        st.rerun()
                    else:
                        # 2. Attempt to authenticate as standard User
                        user_account = User(email)
                        if user_account.authenticate(password):
                            st.session_state['role'] = 'user'
                            st.session_state['logged_in_email'] = user_account.email
                            st.session_state['user_full_name'] = user_account.full_name
                            st.session_state['user_id'] = user_account.id
                            st.rerun()
                        else:
                            st.error("Email sau parolă incorecte.")
