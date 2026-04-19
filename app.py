import streamlit as st
from models.authentication import User, Admin
from models.tracking import FoodItem, Activity

# ==========================================
# UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="MacroSense", layout="centered")

# ==========================================
# SESSION STATE MANAGEMENT
# ==========================================
# Initialize role if it doesn't exist
if 'role' not in st.session_state:
    st.session_state['role'] = None

# ==========================================
# GUEST ROUTING (NOT LOGGED IN)
# ==========================================
if st.session_state['role'] is None:
    
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
                # 1. Frontend Validation
                if not email.strip() or not password.strip() or not full_name.strip():
                    st.warning("Te rog să completezi toate câmpurile obligatorii (Email, Parolă, Nume complet)!")
                elif len(password) < 6:
                    st.warning("Parola trebuie să conțină cel puțin 6 caractere!")
                # Improved email validation
                elif "@" not in email or email.count("@") != 1 or "." not in email.split("@")[1]:
                    st.warning("Te rog introdu o adresă de email validă!")
                else:
                    # 2. Proceed with registration if validation passes
                    new_user = User(email, full_name, height, age, gender, goal)
                    if new_user.register(password):
                        st.success("Cont creat cu succes! Te poți autentifica acum.")
                    else:
                        st.error("Eroare la creare. Probabil acest email există deja.")
    
    elif choice == "Autentificare":
        st.subheader("Intră în contul tău")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Parolă", type="password")
            submit_login = st.form_submit_button("Login")
            
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
                            st.rerun()
                        else:
                            st.error("Email sau parolă incorecte.")
# ==========================================
# ADMIN ROUTING
# ==========================================
elif st.session_state['role'] == 'admin':
    
    st.sidebar.title("Panou Administrator")
    st.sidebar.info(f"Autentificat ca:\n{st.session_state['logged_in_email']}")
    
    menu = ["Gestiune Alimente", "Gestiune Activități"]
    choice = st.sidebar.selectbox("Meniu Admin", menu)

    if choice == "Gestiune Alimente":
        st.header("🍎 Gestiune Catalog Alimente")
        with st.expander("➕ Adaugă un aliment nou", expanded=True):
            with st.form("add_food_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Denumire aliment")
                    category = st.selectbox("Categorie", ["Fructe", "Legume", "Carne", "Lactate", "Cereale", "Dulciuri", "Altele"])
                    calories = st.number_input("Calorii (per 100g)", min_value=0.0, step=1.0)
                with col2:
                    protein = st.number_input("Proteine (g)", min_value=0.0, step=0.1)
                    carbs = st.number_input("Carbohidrați (g)", min_value=0.0, step=0.1)
                    fats = st.number_input("Grăsimi (g)", min_value=0.0, step=0.1)
                
                submit_food = st.form_submit_button("Salvează Alimentul")
                
                if submit_food:
                    new_food = FoodItem(name, calories, protein, carbs, fats, category)
                    if new_food.save():
                        st.success(f"Alimentul '{name}' a fost adăugat cu succes!")
                    else:
                        st.error("Eroare la adăugarea alimentului.")

        st.subheader("Baza de date nutrițională")
        df_foods = FoodItem.get_all_as_dataframe()
        if not df_foods.empty:
            st.dataframe(df_foods, width='stretch')
        else:
            st.info("Catalogul este gol.")

    elif choice == "Gestiune Activități":
        st.header("🏃‍♂️ Gestiune Catalog Activități")
        with st.expander("➕ Adaugă o activitate nouă", expanded=True):
            with st.form("add_activity_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Denumire activitate")
                    category = st.selectbox("Categorie", ["Cardio", "Forță", "Flexibilitate", "Sport de echipă"])
                with col2:
                    met = st.number_input("Coeficient MET", min_value=0.9, step=0.1, help="Ex: Alergat = 8.0")
                
                submit_act = st.form_submit_button("Salvează Activitatea")
                
                if submit_act:
                    new_activity = Activity(name, met, category)
                    if new_activity.save():
                        st.success(f"Activitatea '{name}' a fost adăugată cu succes!")
                    else:
                        st.error("Eroare la adăugarea activității.")

        st.subheader("Lista activităților disponibile")
        df_activities = Activity.get_all_as_dataframe()
        if not df_activities.empty:
            st.dataframe(df_activities, width='stretch')
        else:
            st.info("Catalogul de activități este gol.")
            
    # Admin Logout Button
    st.sidebar.divider()
    if st.sidebar.button("Deconectare", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==========================================
# USER ROUTING
# ==========================================
elif st.session_state['role'] == 'user':
    
    st.sidebar.title(f"Salut, {st.session_state['user_full_name']}!")
    
    menu = ["Acasă", "Catalog Alimente", "Catalog Activități"]
    choice = st.sidebar.selectbox("Meniu Principal", menu)
        
    if choice == "Acasă":
        st.title("🏠 Dashboard")
        st.success("Autentificare realizată cu succes!")
        st.info("Aici vom construi jurnalele și graficele tale.")
        
    elif choice == "Catalog Alimente":
        st.header("🍎 Catalog Alimente")
        st.subheader("Baza de date nutrițională")
        df_foods = FoodItem.get_all_as_dataframe()
        if not df_foods.empty:
            st.dataframe(df_foods, width='stretch')
        else:
            st.info("Catalogul este gol în acest moment. Administratorul va adăuga date în curând.")

    elif choice == "Catalog Activități":
        st.header("🏃‍♂️ Catalog Activități Fizice")
        st.subheader("Lista activităților disponibile")
        df_activities = Activity.get_all_as_dataframe()
        if not df_activities.empty:
            st.dataframe(df_activities, width='stretch')
        else:
            st.info("Catalogul de activități este gol în acest moment.")
            
    # User Logout Button
    st.sidebar.divider()
    if st.sidebar.button("Deconectare", use_container_width=True):
        st.session_state.clear()
        st.rerun()