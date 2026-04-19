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
    st.sidebar.title("MacroSense")
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
                
            submit_register = st.form_submit_button("Înregistrează-te")
            
            if submit_register:
                # OOP Integration: Instantiate a User object
                new_user = User(email, full_name, height, age, gender, goal)
                if new_user.register(password):
                    st.success("Cont creat cu succes! Mergi la Autentificare pentru a te loga.")
                else:
                    st.error("Eroare la creare. Probabil acest email există deja.")

    elif choice == "Autentificare":
        st.subheader("Intră în contul tău")
        
        # Wrapping login inside a form to prevent Streamlit refresh issues
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Parolă", type="password")
            submit_login = st.form_submit_button("Login")
            
            if submit_login:
                print(f"DEBUG: Incercare login pentru adresa {email}...") # We will see this in VS Code terminal
                account = UserAccount(email)
                
                # Verify password against the database
                if account.authenticate(password):
                    print("DEBUG: Parola este corecta. Preiau datele de profil...")
                    # Fetch full user profile data
                    logged_user = User.get_user_by_email(email)
                    
                    if logged_user:
                        print("DEBUG: Date preluate cu succes. Schimbam interfata!")
                        st.session_state['logged_in_email'] = logged_user.email
                        st.session_state['user_full_name'] = logged_user.full_name
                        st.rerun()
                    else:
                        print("DEBUG: Eroare la preluarea obiectului User din BD.")
                        st.error("Eroare: Autentificarea a reușit, dar nu pot prelua datele!")
                else:
                    print("DEBUG: Autentificare esuata. Parola sau email gresit.")
                    st.error("Email sau parolă incorecte.")

else:
    # --- LOGGED IN MENU ---
    st.sidebar.title(f"Salut, {st.session_state['user_full_name']}!")
    
    # Meniul noului utilizator logat
    menu = ["Acasă", "Deconectare"]
    choice = st.sidebar.selectbox("Meniu Principal", menu)
        
    if choice == "Acasă":
        st.title("🏠 Dashboard")
        st.success("Autentificare realizată cu succes!")
        st.info("Aici vom construi jurnalele și graficele tale. Acesta este ecranul tău principal.")
        
    elif choice == "Deconectare":
        st.session_state.clear()
        st.rerun()