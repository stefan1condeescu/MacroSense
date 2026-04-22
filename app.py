import streamlit as st
import datetime
from database import get_connection
from models.authentication import User, Admin
from models.tracking import FoodItem, Activity, FoodLog, DailyLog

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
                weight = st.number_input("Greutate curentă (kg)", min_value=30.0, max_value=300.0, step=0.1)
                age = st.number_input("Vârstă", min_value=10, max_value=120, step=1)
            with col2:
                gender = st.selectbox("Sex", ["M", "F"])
                goal = st.selectbox("Obiectiv", ["slăbire", "menținere", "creștere"])
            submit_register = st.form_submit_button("Înregistrează-te", width="stretch")

        if submit_register:
            if not email.strip() or not password.strip() or not full_name.strip():
                st.warning("Te rog să completezi toate câmpurile obligatorii (Email, Parolă, Nume complet)!")
            elif len(password) < 6:
                st.warning("Parola trebuie să conțină cel puțin 6 caractere!")
            elif "@" not in email or email.count("@") != 1 or "." not in email.split("@")[1]:
                st.warning("Te rog introdu o adresă de email validă!")
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
                            st.session_state['user_id'] = user_account.id  # SALVAM ID-ul
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
    if st.sidebar.button("Deconectare", width="stretch"):
        st.session_state.clear()
        st.rerun()

# ==========================================
# USER ROUTING
# ==========================================
elif st.session_state['role'] == 'user':
    
    st.sidebar.title(f"Salut, {st.session_state['user_full_name']}!")
    
    menu = ["Acasă", "Jurnal Alimentar", "Catalog Alimente", "Catalog Activități"]
    choice = st.sidebar.selectbox("Meniu Principal", menu)
        
    if choice == "Acasă":
        st.title("🏠 Dashboard")
        st.success("Autentificare realizată cu succes!")
        st.info("Aici vom construi jurnalele și graficele tale.")


    elif choice == "Jurnal Alimentar":
        st.header("📔 Jurnal Alimentar")

        selected_date = st.date_input("Selectează ziua:", value=datetime.date.today())

        user_id = st.session_state.get('user_id')
        if not user_id:
            st.error("Sesiune invalidă. Te rugăm să te reautentifici.")
            st.stop()

        daily_log = DailyLog.get_or_create(user_id, selected_date)
        if not daily_log:
            st.error("Eroare la accesarea jurnalului zilnic.")
            st.stop()

        st.subheader("➕ Adaugă aliment consumat")
        food_conn = get_connection()
        food_options = {}
        if food_conn:
            try:
                cur = food_conn.cursor()
                cur.execute("SELECT id, name, calories_100g FROM food_items ORDER BY name ASC")
                for row in cur.fetchall():
                    food_options[row[1]] = {"id": row[0], "calories_100g": float(row[2])}
            except Exception as e:
                st.error(f"Eroare la preluarea alimentelor: {e}") # Adaugam si eroarea pe ecran ca sa nu mai treaca neobservata
            finally:
                food_conn.close()

        if not food_options:
            st.warning("Catalogul de alimente este gol. Administratorul trebuie să adauge alimente mai întâi.")
        else:
            with st.form("add_food_log_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    selected_food_name = st.selectbox("Aliment", options=list(food_options.keys()))
                    quantity = st.number_input("Cantitate (g)", min_value=1.0, max_value=5000.0,
                                               value=100.0, step=1.0)
                with col2:
                    meal_type = st.selectbox("Masă", ["Mic dejun", "Prânz", "Cină", "Gustare"])
                    meal_time = st.time_input("Ora consumului", value=datetime.time(12, 0))

                selected_food = food_options[selected_food_name]
                estimated_calories = round(selected_food["calories_100g"] * float(quantity) / 100.0, 2)
                st.caption(f"🔥 Calorii estimate: **{estimated_calories} kcal**")

                submit_food = st.form_submit_button("Salvează înregistrarea", width="stretch")

            if submit_food:
                food_log_entry = FoodLog(
                    log_id=daily_log.id,
                    quantity_g=quantity,
                    meal_type=meal_type,
                    meal_time=meal_time,
                    food_id=selected_food["id"]
                )
                if food_log_entry.save():
                    daily_log.recalculate_totals()
                    st.success(f"✅ {selected_food_name} ({quantity}g) adăugat cu succes!")
                    st.rerun()
                else:
                    st.error("Eroare la salvarea înregistrării.")

        st.divider()
        # Map months to Romanian to ensure consistent localization regardless of the OS locale
        romanian_months = {
            1: "Ianuarie", 2: "Februarie", 3: "Martie", 4: "Aprilie",
            5: "Mai", 6: "Iunie", 7: "Iulie", 8: "August",
            9: "Septembrie", 10: "Octombrie", 11: "Noiembrie", 12: "Decembrie"
        }
        formatted_date = f"{selected_date.day} {romanian_months[selected_date.month]} {selected_date.year}"
        st.subheader(f"📋 Alimente consumate pe {formatted_date}")
        df_entries = DailyLog.get_food_entries(daily_log.id)

        if not df_entries.empty:
           # Hide the index column (database ID) from the UI
            st.dataframe(df_entries, width="stretch", hide_index=True)
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("🍽️ Calorii consumate", f"{daily_log.total_calories_in:.0f} kcal")
            col2.metric("🔥 Calorii arse", f"{daily_log.total_calories_burned:.0f} kcal")
            col3.metric("⚖️ Balanță energetică",
                        f"{daily_log.calculate_energy_balance():.0f} kcal",
                        delta=f"{daily_log.calculate_energy_balance():.0f}")
        else:
            st.info("Nu există înregistrări pentru această zi. Adaugă primul aliment folosind formularul de mai sus.")

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
    if st.sidebar.button("Deconectare", width="stretch"):
        st.session_state.clear()
        st.rerun()