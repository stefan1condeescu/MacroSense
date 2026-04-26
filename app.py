import streamlit as st
import datetime
import pandas as pd
from database import get_connection
from models.authentication import User, Admin
from models.tracking import FoodItem, Activity, FoodLog, DailyLog, ActivityLog, CustomMeal

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
                            st.session_state['user_id'] = user_account.id
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
            st.dataframe(df_foods, width='stretch', hide_index=True)
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
            st.dataframe(df_activities, width='stretch', hide_index=True)
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
    
    menu = ["Acasă", "Jurnal Alimentar", "Jurnal Activități", "Mese Personalizate", "Catalog Alimente", "Catalog Activități"]
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

        st.subheader("➕ Adaugă consum alimentar")
        food_options = FoodItem.get_catalog_options()
        custom_meal_options = CustomMeal.get_user_meal_options(user_id)

        entry_type = st.radio(
            "Tip înregistrare",
            ["Aliment din catalog", "Masă personalizată"],
            horizontal=True,
            key="food_entry_type"
        )

        if entry_type == "Aliment din catalog":
            if not food_options:
                st.warning("Catalogul de alimente este gol. Administratorul trebuie să adauge alimente mai întâi.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    selected_food_id = st.selectbox(
                        "Aliment",
                        options=list(food_options.keys()),
                        format_func=lambda food_id: food_options[food_id]["name"],
                        key="food_log_food_select"
                    )
                    quantity = st.number_input("Cantitate (g)", min_value=1.0, max_value=5000.0, value=100.0, step=1.0, key="food_log_food_quantity")
                with col2:
                    meal_type = st.selectbox("Masă", ["Mic dejun", "Prânz", "Cină", "Gustare"], key="food_log_food_meal_type")
                    meal_time = st.time_input("Ora consumului", value=datetime.time(12, 0), key="food_log_food_time")

                selected_food = food_options[selected_food_id]
                estimated_calories = round(selected_food["calories_100g"] * float(quantity) / 100.0, 2)
                st.caption(f"🔥 Calorii estimate: **{estimated_calories} kcal**")

                submit_food = st.button("Salvează înregistrarea", width="stretch", key="btn_save_food")

                if submit_food:
                    try:
                        food_log_entry = FoodLog(
                            log_id=daily_log.id,
                            quantity_g=quantity,
                            meal_type=meal_type,
                            meal_time=meal_time,
                            food_id=selected_food["id"]
                        )

                        if food_log_entry.save():
                            daily_log.recalculate_totals()
                            st.success(f"✅ {selected_food['name']} ({quantity}g) adăugat cu succes!")
                            st.rerun()
                        else:
                            st.error("Eroare la salvarea înregistrării.")
                    except ValueError as ve:
                        st.error(f"Eroare de validare: {ve}")
        else:
            if not custom_meal_options:
                st.warning("Nu ai mese personalizate salvate. Creează una în pagina „Mese Personalizate”.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    selected_meal_id = st.selectbox(
                        "Masă personalizată",
                        options=list(custom_meal_options.keys()),
                        format_func=lambda meal_id: custom_meal_options[meal_id]["recipe_name"],
                        key="food_log_custom_meal_select"
                    )
                    custom_quantity = st.number_input("Cantitate consumată (g)", min_value=1.0, max_value=5000.0, value=100.0, step=1.0, key="food_log_custom_meal_quantity")
                with col2:
                    custom_meal_type = st.selectbox("Masă", ["Mic dejun", "Prânz", "Cină", "Gustare"], key="food_log_custom_meal_type")
                    custom_meal_time = st.time_input("Ora consumului", value=datetime.time(12, 0), key="food_log_custom_meal_time")

                selected_custom_meal = custom_meal_options[selected_meal_id]
                estimated_custom_calories = round(selected_custom_meal["calories_per_g"] * float(custom_quantity), 2)
                st.caption(f"🔥 Calorii estimate: **{estimated_custom_calories} kcal**")

                submit_custom_meal = st.button("Salvează masa în jurnal", width="stretch", key="btn_save_custom_meal_log")

                if submit_custom_meal:
                    try:
                        custom_meal_log_entry = FoodLog(
                            log_id=daily_log.id,
                            quantity_g=custom_quantity,
                            meal_type=custom_meal_type,
                            meal_time=custom_meal_time,
                            custom_meal_id=selected_custom_meal["id"]
                        )

                        if custom_meal_log_entry.save():
                            daily_log.recalculate_totals()
                            st.success(f"✅ {selected_custom_meal['recipe_name']} ({custom_quantity}g) adăugată cu succes!")
                            st.rerun()
                        else:
                            st.error("Eroare la salvarea mesei personalizate.")
                    except ValueError as ve:
                        st.error(f"Eroare de validare: {ve}")
            
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

    elif choice == "Jurnal Activități":
        st.header("🏋️‍♂️ Jurnal Activități Fizice")

        selected_date = st.date_input("Selectează ziua:", value=datetime.date.today())

        user_id = st.session_state.get('user_id')
        if not user_id:
            st.error("Sesiune invalidă. Te rugăm să te reautentifici.")
            st.stop()

        daily_log = DailyLog.get_or_create(user_id, selected_date)
        if not daily_log:
            st.error("Eroare la accesarea jurnalului zilnic.")
            st.stop()

        st.subheader("➕ Adaugă antrenament")
        act_conn = get_connection()
        activity_options = {}
        if act_conn:
            try:
                cur = act_conn.cursor()
                cur.execute("SELECT id, name, met_multiplier, category FROM activities ORDER BY name ASC")
                for row in cur.fetchall():
                    activity_options[row[1]] = {"id": row[0], "met": float(row[2]), "category": row[3]}
            except Exception as e:
                st.error(f"Eroare la preluarea activităților: {e}")
            finally:
                act_conn.close()

        if not activity_options:
            st.warning("Catalogul de activități este gol. Administratorul trebuie să adauge date mai întâi.")
        else:
            # Selectbox placed OUTSIDE the form to enable dynamic UI reactivity on category change
            selected_act_name = st.selectbox(
                "1. Alege activitatea",
                options=list(activity_options.keys()),
                key="activity_select"
            )
            selected_act = activity_options[selected_act_name]

            # Defensive .strip() to handle accidental whitespace stored in DB
            is_strength = selected_act["category"].strip() == "Forță"
            latest_weight = DailyLog.get_latest_weight(user_id, selected_date)

            # Live preview inputs for the activity journal.
            col1, col2 = st.columns(2)

            with col1:
                # Duration is mandatory for ALL activity types to compute T_rest in the hybrid TUT model
                duration = st.number_input(
                    "Durată TOTALĂ sesiune (minute)",
                    min_value=1, max_value=600, value=30, step=5,
                    help="Timpul total petrecut la acest exercițiu (inclusiv pauzele dintre seturi)."
                )

            with col2:
                # Sets and reps are rendered only for strength activities; hidden entirely for cardio
                if is_strength:
                    sets = st.number_input("Seturi", min_value=1, max_value=50, value=3, step=1)
                    reps = st.number_input("Repetări pe set", min_value=1, max_value=200, value=12, step=1)
                else:
                    st.info("📌 Seturile și repetările se aplică doar la exerciții de Forță.")
                    sets = 0
                    reps = 0

            # Ensure numeric fallback for the hybrid calories helper when category is cardio
            calc_sets = sets if is_strength else 0
            calc_reps = reps if is_strength else 0

            estimated_burned = DailyLog.calculate_hybrid_calories(
                selected_act["category"].strip(), selected_act["met"],
                latest_weight, duration,
                calc_sets, calc_reps
            )
            st.caption(f"🔥 Calorii estimate consumate: **{estimated_burned} kcal**")

            submit_act = st.button("Salvează antrenamentul", width="stretch", key="btn_save_act")

            if submit_act:
                # Map 0 to None for DB insertion — schema allows NULL for sets/reps on cardio entries
                db_sets = calc_sets if calc_sets > 0 else None
                db_reps = calc_reps if calc_reps > 0 else None

                try:
                    act_log_entry = ActivityLog(
                        log_id=daily_log.id,
                        activity_id=selected_act["id"],
                        duration_min=duration,
                        sets=db_sets,
                        reps=db_reps
                    )
                    if act_log_entry.save():
                        daily_log.recalculate_totals()
                        st.success(f"✅ {selected_act_name} adăugat cu succes!")
                        st.rerun()
                    else:
                        st.error("Eroare la salvarea înregistrării.")
                except ValueError as ve:
                    st.error(f"Eroare de validare: {ve}")

        st.divider()
        romanian_months = {
            1: "Ianuarie", 2: "Februarie", 3: "Martie", 4: "Aprilie",
            5: "Mai", 6: "Iunie", 7: "Iulie", 8: "August",
            9: "Septembrie", 10: "Octombrie", 11: "Noiembrie", 12: "Decembrie"
        }
        formatted_date = f"{selected_date.day} {romanian_months[selected_date.month]} {selected_date.year}"
        st.subheader(f"📋 Antrenamente efectuate pe {formatted_date}")
        
        df_entries = DailyLog.get_activity_entries(daily_log.id)

        if not df_entries.empty:
                # Hide the index column (database ID) from the UI
            st.dataframe(df_entries, width="stretch", hide_index=True) 
            st.divider()
            col1, col2, col3 = st.columns(3)
            cals_strength = df_entries[df_entries["Categorie"] == "Forță"]["Calorii Arse"].sum()
            cals_cardio_other = df_entries[df_entries["Categorie"] != "Forță"]["Calorii Arse"].sum()
            total_burned = cals_strength + cals_cardio_other
            
            col1.metric(
                "🏋️ Calorii Forță",
                f"{cals_strength:.0f} kcal",
                help="Calculate pe baza modelului Time Under Tension (TUT)."
            )
            col2.metric(
                "🏃 Calorii Cardio & Altele",
                f"{cals_cardio_other:.0f} kcal",
                help="Calculate pe baza formulei standard MET × Greutate × Durată."
            )
            col3.metric(
                "🔥 Total Calorii Arse",
                f"{total_burned:.0f} kcal",
                help="Suma tuturor caloriilor arse în această zi (Forță + Cardio & Altele)."
            )

            st.markdown("<br>", unsafe_allow_html=True)

            _, col4, col5, _ = st.columns([0.5, 1, 1, 0.5])
            col4.metric(
                "🍽️ Calorii Consumate",
                f"{daily_log.total_calories_in:.0f} kcal",
                help="Total calorii consumate din alimentație în această zi."
            )
            col5.metric(
                "⚖️ Balanță energetică",
                f"{daily_log.calculate_energy_balance():.0f} kcal",
                delta=f"{daily_log.calculate_energy_balance():.0f}"
            )
        else:
            st.info("Nu există antrenamente înregistrate pentru această zi.")

    elif choice == "Mese Personalizate":
        st.header("🥗 Mese Personalizate")

        user_id = st.session_state.get('user_id')
        if not user_id:
            st.error("Sesiune invalidă. Te rugăm să te reautentifici.")
            st.stop()

        if "custom_meal_ingredients" not in st.session_state:
            st.session_state["custom_meal_ingredients"] = []

        food_options = FoodItem.get_catalog_options()

        st.subheader("➕ Creează o masă personalizată")
        recipe_name = st.text_input("Denumire masă", key="custom_meal_name")

        if not food_options:
            st.warning("Catalogul de alimente este gol. Administratorul trebuie să adauge alimente mai întâi.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                selected_ingredient_id = st.selectbox(
                    "Ingredient",
                    options=list(food_options.keys()),
                    format_func=lambda food_id: food_options[food_id]["name"],
                    key="custom_meal_ingredient_select"
                )
            with col2:
                ingredient_quantity = st.number_input("Cantitate ingredient (g)", min_value=1.0, max_value=5000.0, value=100.0, step=1.0, key="custom_meal_ingredient_quantity")

            selected_ingredient = food_options[selected_ingredient_id]
            ingredient_calories = round(selected_ingredient["calories_100g"] * float(ingredient_quantity) / 100.0, 2)
            st.caption(f"🔥 Ingredient selectat: **{ingredient_calories} kcal**")

            col_add, col_clear = st.columns(2)
            with col_add:
                if st.button("Adaugă ingredient", width="stretch", key="btn_add_custom_meal_ingredient"):
                    st.session_state["custom_meal_ingredients"].append({
                        "food_id": selected_ingredient["id"],
                        "name": selected_ingredient["name"],
                        "quantity_g": float(ingredient_quantity),
                        "calories_100g": selected_ingredient["calories_100g"],
                        "protein_g": selected_ingredient["protein_g"],
                        "carbs_g": selected_ingredient["carbs_g"],
                        "fats_g": selected_ingredient["fats_g"],
                    })
                    st.rerun()
            with col_clear:
                if st.button("Golește lista", width="stretch", key="btn_clear_custom_meal_ingredients"):
                    st.session_state["custom_meal_ingredients"] = []
                    st.rerun()

        pending_ingredients = st.session_state["custom_meal_ingredients"]
        if pending_ingredients:
            rows = []
            total_quantity = 0.0
            total_calories = 0.0
            total_protein = 0.0
            total_carbs = 0.0
            total_fats = 0.0

            for ingredient in pending_ingredients:
                quantity_g = ingredient["quantity_g"]
                calories = ingredient["calories_100g"] * quantity_g / 100.0
                protein = ingredient["protein_g"] * quantity_g / 100.0
                carbs = ingredient["carbs_g"] * quantity_g / 100.0
                fats = ingredient["fats_g"] * quantity_g / 100.0

                total_quantity += quantity_g
                total_calories += calories
                total_protein += protein
                total_carbs += carbs
                total_fats += fats

                rows.append([
                    ingredient["name"],
                    round(quantity_g, 2),
                    round(calories, 2),
                    round(protein, 2),
                    round(carbs, 2),
                    round(fats, 2),
                ])

            df_pending = pd.DataFrame(
                rows,
                columns=["Ingredient", "Cantitate (g)", "Calorii", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)"]
            )
            st.dataframe(df_pending, width="stretch", hide_index=True)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Cantitate", f"{total_quantity:.0f} g")
            col2.metric("Calorii", f"{total_calories:.0f} kcal")
            col3.metric("Proteine", f"{total_protein:.1f} g")
            col4.metric("Carbohidrați", f"{total_carbs:.1f} g")
            st.caption(f"Grăsimi totale: **{total_fats:.1f} g**")

            if st.button("Salvează masa personalizată", width="stretch", key="btn_save_custom_meal"):
                if not recipe_name.strip():
                    st.warning("Introdu o denumire pentru masa personalizată.")
                else:
                    saved_meal = CustomMeal.create_with_ingredients(
                        user_id=user_id,
                        recipe_name=recipe_name,
                        ingredients=pending_ingredients
                    )
                    if saved_meal:
                        st.session_state["custom_meal_ingredients"] = []
                        st.success(f"✅ Masa personalizată „{saved_meal.recipe_name}” a fost salvată.")
                        st.rerun()
                    else:
                        st.error("Eroare la salvarea mesei personalizate.")
        else:
            st.info("Adaugă cel puțin un ingredient pentru a salva o masă personalizată.")

        st.divider()
        st.subheader("📋 Mesele tale personalizate")
        df_custom_meals = CustomMeal.get_all_as_dataframe(user_id)
        if not df_custom_meals.empty:
            st.dataframe(df_custom_meals, width="stretch", hide_index=True)

            custom_meal_options = CustomMeal.get_user_meal_options(user_id)
            selected_saved_meal_id = st.selectbox(
                "Vezi ingredientele pentru",
                options=list(custom_meal_options.keys()),
                format_func=lambda meal_id: custom_meal_options[meal_id]["recipe_name"],
                key="custom_meal_details_select"
            )
            selected_saved_meal = custom_meal_options[selected_saved_meal_id]
            df_ingredients = CustomMeal.get_ingredients_as_dataframe(selected_saved_meal["id"], user_id)
            if not df_ingredients.empty:
                st.dataframe(df_ingredients, width="stretch", hide_index=True)
        else:
            st.info("Nu ai încă mese personalizate salvate.")
   
    elif choice == "Catalog Alimente":
        st.header("🍎 Catalog Alimente")
        st.subheader("Baza de date nutrițională")
        df_foods = FoodItem.get_all_as_dataframe()
        if not df_foods.empty:
            st.dataframe(df_foods, width='stretch', hide_index=True)
        else:
            st.info("Catalogul este gol în acest moment. Administratorul va adăuga date în curând.")

    elif choice == "Catalog Activități":
        st.header("🏃‍♂️ Catalog Activități Fizice")
        st.subheader("Lista activităților disponibile")
        df_activities = Activity.get_all_as_dataframe()
        if not df_activities.empty:
            st.dataframe(df_activities, width='stretch', hide_index=True)
        else:
            st.info("Catalogul de activități este gol în acest moment.")
            
    # User Logout Button
    st.sidebar.divider()
    if st.sidebar.button("Deconectare", width="stretch"):
        st.session_state.clear()
        st.rerun()
