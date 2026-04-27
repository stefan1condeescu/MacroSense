import streamlit as st
import datetime
import pandas as pd
from pathlib import Path
from models.authentication import User, Admin
from models.tracking import FoodItem, Activity, FoodLog, DailyLog, ActivityLog, CustomMeal

# ==========================================
# UI CONFIGURATION
# ==========================================
st.set_page_config(page_title="MacroSense", layout="centered")

def load_local_css(file_name: str) -> None:
    """Loads local CSS styles if the asset file exists."""
    css_path = Path(__file__).parent / file_name
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

load_local_css("assets/style.css")

def get_table_height(dataframe: pd.DataFrame, max_rows: int = 6, row_height: int = 32) -> int:
    """Returns a compact dynamic height for Streamlit dataframes."""
    visible_rows = min(max(len(dataframe), 1), max_rows)
    return 38 + visible_rows * row_height

def render_table(dataframe: pd.DataFrame, column_config: dict = None, column_order: list = None, max_rows: int = 6) -> None:
    """Renders a compact dataframe with consistent project styling."""
    st.dataframe(
        dataframe,
        width="stretch",
        height=get_table_height(dataframe, max_rows=max_rows),
        hide_index=True,
        column_config=column_config,
        column_order=column_order,
        row_height=32
    )

def format_time_for_display(value) -> str:
    """Formats database time values for Streamlit display widgets."""
    if value is None:
        return "-"

    try:
        if pd.isna(value):
            return "-"
    except (TypeError, ValueError):
        pass

    if isinstance(value, datetime.timedelta):
        total_seconds = int(value.total_seconds())
        return (datetime.datetime.min + datetime.timedelta(seconds=total_seconds)).time().strftime("%H:%M")

    if isinstance(value, datetime.time):
        return value.strftime("%H:%M")

    if isinstance(value, str):
        try:
            return datetime.time.fromisoformat(value).strftime("%H:%M")
        except ValueError:
            return value

    return str(value)

def format_food_entries_for_display(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Returns a UI-safe copy of food log entries with formatted time."""
    visible_dataframe = dataframe.copy()
    if "Ora" in visible_dataframe.columns:
        visible_dataframe["Ora"] = visible_dataframe["Ora"].apply(format_time_for_display)
    return visible_dataframe

food_catalog_table_config = {
    "Denumire": st.column_config.TextColumn("Denumire", width="medium"),
    "Calorii/100g": st.column_config.NumberColumn("Calorii/100g", format="%.1f kcal", width="small"),
    "Proteine (g)": st.column_config.NumberColumn("Proteine", format="%.1f g", width="small"),
    "Carbohidrați (g)": st.column_config.NumberColumn("Carbohidrați", format="%.1f g", width="small"),
    "Grăsimi (g)": st.column_config.NumberColumn("Grăsimi", format="%.1f g", width="small"),
    "Categorie": st.column_config.TextColumn("Categorie", width="small"),
}

activity_catalog_table_config = {
    "Denumire": st.column_config.TextColumn("Denumire", width="medium"),
    "Coeficient MET": st.column_config.NumberColumn("MET", format="%.1f", width="small"),
    "Categorie": st.column_config.TextColumn("Categorie", width="small"),
}

food_log_table_config = {
    "Tip": st.column_config.TextColumn("Tip", width="small"),
    "Aliment / Masă": st.column_config.TextColumn("Aliment / Masă", width="medium"),
    "Cantitate (g)": st.column_config.NumberColumn("Cantitate", format="%.1f g", width="small"),
    "Calorii": st.column_config.NumberColumn("Calorii", format="%.1f kcal", width="small"),
    "Masă": st.column_config.TextColumn("Masă", width="small"),
    "Ora": st.column_config.TextColumn("Ora", width="small"),
}

activity_log_table_config = {
    "Activitate": st.column_config.TextColumn("Activitate", width="medium"),
    "Categorie": st.column_config.TextColumn("Categorie", width="small"),
    "Durată (min)": st.column_config.NumberColumn("Durată", format="%d min", width="small"),
    "Seturi": st.column_config.TextColumn("Seturi", width="small"),
    "Repetări": st.column_config.TextColumn("Repetări", width="small"),
    "Calorii Arse": st.column_config.NumberColumn("Calorii Arse", format="%.1f kcal", width="small"),
}

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
            submit_register = st.form_submit_button("Înregistrează-te", width="stretch", type="primary")

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
                
                submit_food = st.form_submit_button("Salvează Alimentul", type="primary")
                
                if submit_food:
                    new_food = FoodItem(name, calories, protein, carbs, fats, category)
                    if new_food.save():
                        st.success(f"Alimentul '{name}' a fost adăugat cu succes!")
                    else:
                        st.error("Eroare la adăugarea alimentului.")

        st.subheader("Baza de date nutrițională")
        df_foods = FoodItem.get_all_as_dataframe()
        if not df_foods.empty:
            render_table(df_foods, column_config=food_catalog_table_config)
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
                
                submit_act = st.form_submit_button("Salvează Activitatea", type="primary")
                
                if submit_act:
                    new_activity = Activity(name, met, category)
                    if new_activity.save():
                        st.success(f"Activitatea '{name}' a fost adăugată cu succes!")
                    else:
                        st.error("Eroare la adăugarea activității.")

        st.subheader("Lista activităților disponibile")
        df_activities = Activity.get_all_as_dataframe()
        if not df_activities.empty:
            render_table(df_activities, column_config=activity_catalog_table_config)
        else:
            st.info("Catalogul de activități este gol.")
            
    # Admin Logout Button
    st.sidebar.divider()
    if st.sidebar.button("Deconectare", width="stretch", type="tertiary"):
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
        food_log_message = st.session_state.pop("food_log_msg", None)
        if "food_log_widget_version" not in st.session_state:
            st.session_state["food_log_widget_version"] = 0

        if st.session_state.pop("food_log_reset_edit_delete_widgets", False):
            st.session_state["food_log_widget_version"] += 1
            legacy_food_widget_keys = {
                "food_log_edit_select",
                "food_log_delete_select",
                "food_log_delete_confirm",
            }
            food_widget_keys = [
                key for key in st.session_state.keys()
                if key in legacy_food_widget_keys
                or key.startswith((
                    "food_log_edit_select_",
                    "food_log_delete_select_",
                    "food_log_delete_confirm_",
                    "food_log_edit_quantity_",
                    "food_log_edit_meal_type_",
                    "food_log_edit_time_",
                ))
            ]
            for key in food_widget_keys:
                del st.session_state[key]

        user_id = st.session_state.get('user_id')
        if not user_id:
            st.error("Sesiune invalidă. Te rugăm să te reautentifici.")
            st.stop()

        daily_log = DailyLog.get_or_create(user_id, selected_date)
        if not daily_log:
            st.error("Eroare la accesarea jurnalului zilnic.")
            st.stop()

        def show_food_log_message(message):
            if not message:
                return

            message_type, message_text = message
            icon = "✅" if message_type == "success" else "⚠️" if message_type == "warning" else "❌"
            st.toast(message_text, icon=icon)

        def format_food_log_option(entries_df, log_entry_id):
            row = entries_df.loc[log_entry_id]
            meal_time = format_time_for_display(row["Ora"])
            return f"{row['Tip']} - {row['Aliment / Masă']} ({row['Cantitate (g)']}g, {row['Masă']}, {meal_time})"

        show_food_log_message(food_log_message)

        @st.fragment
        def render_food_entry_panel():
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

                    submit_food = st.button("Salvează înregistrarea", width="stretch", key="btn_save_food", type="primary")

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
                                st.session_state["food_log_msg"] = ("success", f"{selected_food['name']} ({quantity}g) adăugat cu succes!")
                                st.rerun(scope="app")
                            else:
                                st.error("Eroare la salvarea înregistrării.")
                        except ValueError as ve:
                            st.error(f"Eroare de validare: {ve}")
            else:
                if not custom_meal_options:
                    st.warning("Nu ai mese personalizate active. Creează sau reactivează una în pagina „Mese Personalizate”.")
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

                    submit_custom_meal = st.button("Salvează masa în jurnal", width="stretch", key="btn_save_custom_meal_log", type="primary")

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
                                st.session_state["food_log_msg"] = ("success", f"{selected_custom_meal['recipe_name']} ({custom_quantity}g) adăugată cu succes!")
                                st.rerun(scope="app")
                            else:
                                st.error("Eroare la salvarea mesei personalizate.")
                        except ValueError as ve:
                            st.error(f"Eroare de validare: {ve}")

        render_food_entry_panel()
            
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
            render_table(format_food_entries_for_display(df_entries), column_config=food_log_table_config, max_rows=7)

            @st.fragment
            def render_food_edit_panel():
                current_entries = DailyLog.get_food_entries(daily_log.id)
                if current_entries.empty:
                    return

                with st.container(border=True):
                    st.markdown("#### ✏️ Editează o înregistrare")
                    food_log_ids = list(current_entries.index)
                    food_widget_version = st.session_state["food_log_widget_version"]
                    edit_select_key = f"food_log_edit_select_{daily_log.id}_{food_widget_version}"
                    if st.session_state.get(edit_select_key) not in food_log_ids:
                        st.session_state.pop(edit_select_key, None)

                    saved_edit_food_log_id = st.session_state.get("food_log_edit_selected_id")
                    if saved_edit_food_log_id not in food_log_ids:
                        st.session_state.pop("food_log_edit_selected_id", None)
                        saved_edit_food_log_id = None
                    edit_select_index = food_log_ids.index(saved_edit_food_log_id) if saved_edit_food_log_id in food_log_ids else 0
                    selected_edit_food_log_id = st.selectbox(
                        "Înregistrare de editat",
                        options=food_log_ids,
                        format_func=lambda log_entry_id: format_food_log_option(current_entries, log_entry_id),
                        index=edit_select_index,
                        key=edit_select_key
                    )
                    st.session_state["food_log_edit_selected_id"] = int(selected_edit_food_log_id)

                    selected_edit_row = current_entries.loc[selected_edit_food_log_id]
                    meal_options = ["Mic dejun", "Prânz", "Cină", "Gustare"]
                    current_meal_type = selected_edit_row["Masă"]
                    meal_type_index = meal_options.index(current_meal_type) if current_meal_type in meal_options else 0
                    current_time = selected_edit_row["Ora"]
                    if isinstance(current_time, datetime.timedelta):
                        total_seconds = int(current_time.total_seconds())
                        current_time = (datetime.datetime.min + datetime.timedelta(seconds=total_seconds)).time()
                    elif isinstance(current_time, str):
                        current_time = datetime.time.fromisoformat(current_time)

                    col_edit1, col_edit2 = st.columns(2)
                    with col_edit1:
                        edited_quantity = st.number_input(
                            "Cantitate nouă (g)",
                            min_value=1.0,
                            max_value=5000.0,
                            value=float(selected_edit_row["Cantitate (g)"]),
                            step=1.0,
                            key=f"food_log_edit_quantity_{selected_edit_food_log_id}"
                        )
                        edited_meal_type = st.selectbox(
                            "Masă nouă",
                            options=meal_options,
                            index=meal_type_index,
                            key=f"food_log_edit_meal_type_{selected_edit_food_log_id}"
                        )
                    with col_edit2:
                        edited_meal_time = st.time_input(
                            "Oră nouă",
                            value=current_time,
                            key=f"food_log_edit_time_{selected_edit_food_log_id}"
                        )

                    if st.button("Salvează modificările", width="stretch", key="btn_update_food_log", type="primary"):
                        try:
                            if FoodLog.update(
                                int(selected_edit_food_log_id),
                                user_id,
                                edited_quantity,
                                edited_meal_type,
                                edited_meal_time
                            ):
                                daily_log.recalculate_totals()
                                st.session_state["food_log_edit_selected_id"] = int(selected_edit_food_log_id)
                                st.session_state["food_log_delete_selected_id"] = int(selected_edit_food_log_id)
                                st.session_state["food_log_msg"] = ("success", "Înregistrarea a fost actualizată cu succes.")
                                st.session_state["food_log_reset_edit_delete_widgets"] = True
                                st.rerun(scope="app")
                            else:
                                st.error("Eroare la actualizarea înregistrării.")
                        except ValueError as ve:
                            st.error(f"Eroare de validare: {ve}")

            @st.fragment
            def render_food_delete_panel():
                current_entries = DailyLog.get_food_entries(daily_log.id)
                if current_entries.empty:
                    return

                with st.container(border=True):
                    st.markdown("#### 🗑️ Șterge o înregistrare")
                    food_log_ids = list(current_entries.index)
                    food_widget_version = st.session_state["food_log_widget_version"]
                    delete_select_key = f"food_log_delete_select_{daily_log.id}_{food_widget_version}"
                    delete_confirm_key = f"food_log_delete_confirm_{daily_log.id}_{food_widget_version}"
                    if st.session_state.get(delete_select_key) not in food_log_ids:
                        st.session_state.pop(delete_select_key, None)

                    saved_delete_food_log_id = st.session_state.get("food_log_delete_selected_id")
                    if saved_delete_food_log_id not in food_log_ids:
                        st.session_state.pop("food_log_delete_selected_id", None)
                        saved_delete_food_log_id = None
                    delete_select_index = food_log_ids.index(saved_delete_food_log_id) if saved_delete_food_log_id in food_log_ids else 0
                    selected_food_log_id = st.selectbox(
                        "Înregistrare",
                        options=food_log_ids,
                        format_func=lambda log_entry_id: format_food_log_option(current_entries, log_entry_id),
                        index=delete_select_index,
                        key=delete_select_key
                    )
                    st.session_state["food_log_delete_selected_id"] = int(selected_food_log_id)
                    confirm_food_delete = st.checkbox(
                        "Confirm ștergerea acestei înregistrări",
                        key=delete_confirm_key
                    )

                    if st.button("Șterge înregistrarea", width="stretch", key="btn_delete_food_log", type="tertiary"):
                        if not confirm_food_delete:
                            st.warning("Bifează confirmarea înainte de ștergere.")
                        elif FoodLog.delete(int(selected_food_log_id), user_id):
                            daily_log.recalculate_totals()
                            if st.session_state.get("food_log_edit_selected_id") == int(selected_food_log_id):
                                del st.session_state["food_log_edit_selected_id"]
                            if st.session_state.get("food_log_delete_selected_id") == int(selected_food_log_id):
                                del st.session_state["food_log_delete_selected_id"]
                            st.session_state["food_log_msg"] = ("success", "Înregistrarea a fost ștearsă cu succes.")
                            st.session_state["food_log_reset_edit_delete_widgets"] = True
                            st.rerun(scope="app")
                        else:
                            st.error("Eroare la ștergerea înregistrării.")

            render_food_edit_panel()
            render_food_delete_panel()

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
        activity_log_message = st.session_state.pop("activity_log_msg", None)
        if "activity_log_widget_version" not in st.session_state:
            st.session_state["activity_log_widget_version"] = 0

        if st.session_state.pop("activity_log_reset_edit_delete_widgets", False):
            st.session_state["activity_log_widget_version"] += 1
            legacy_activity_widget_keys = {
                "activity_log_edit_select",
                "activity_log_delete_select",
                "activity_log_delete_confirm",
            }
            activity_widget_keys = [
                key for key in st.session_state.keys()
                if key in legacy_activity_widget_keys
                or key.startswith((
                    "activity_log_edit_select_",
                    "activity_log_delete_select_",
                    "activity_log_delete_confirm_",
                    "activity_log_edit_activity_",
                    "activity_log_edit_duration_",
                    "activity_log_edit_sets_",
                    "activity_log_edit_reps_",
                ))
            ]
            for key in activity_widget_keys:
                del st.session_state[key]

        user_id = st.session_state.get('user_id')
        if not user_id:
            st.error("Sesiune invalidă. Te rugăm să te reautentifici.")
            st.stop()

        daily_log = DailyLog.get_or_create(user_id, selected_date)
        if not daily_log:
            st.error("Eroare la accesarea jurnalului zilnic.")
            st.stop()

        def show_activity_log_message(message):
            if not message:
                return

            message_type, message_text = message
            icon = "✅" if message_type == "success" else "⚠️" if message_type == "warning" else "❌"
            st.toast(message_text, icon=icon)

        def is_strength_activity(activity):
            return (activity["category"] or "").strip() == "Forță"

        def format_activity_log_option(entries_df, log_entry_id):
            row = entries_df.loc[log_entry_id]
            return f"{row['Activitate']} ({row['Categorie']}, {row['Durată (min)']} min, {row['Calorii Arse']} kcal)"

        def parse_optional_int(value, default_value):
            if value in (None, "-", ""):
                return default_value
            return int(float(value))

        show_activity_log_message(activity_log_message)

        @st.fragment
        def render_activity_entry_panel():
            st.subheader("➕ Adaugă antrenament")
            activity_options = Activity.get_catalog_options()

            if not activity_options:
                st.warning("Catalogul de activități este gol. Administratorul trebuie să adauge date mai întâi.")
                return

            selected_activity_id = st.selectbox(
                "1. Alege activitatea",
                options=list(activity_options.keys()),
                format_func=lambda activity_id: activity_options[activity_id]["name"],
                key="activity_select"
            )
            selected_activity = activity_options[selected_activity_id]
            is_strength = is_strength_activity(selected_activity)
            latest_weight = DailyLog.get_latest_weight(user_id, selected_date)

            col1, col2 = st.columns(2)
            with col1:
                duration = st.number_input(
                    "Durată TOTALĂ sesiune (minute)",
                    min_value=1,
                    max_value=600,
                    value=30,
                    step=5,
                    key="activity_log_duration",
                    help="Timpul total petrecut la acest exercițiu (inclusiv pauzele dintre seturi)."
                )

            with col2:
                if is_strength:
                    sets = st.number_input("Seturi", min_value=1, max_value=50, value=3, step=1, key="activity_log_sets")
                    reps = st.number_input("Repetări pe set", min_value=1, max_value=200, value=12, step=1, key="activity_log_reps")
                else:
                    st.info("📌 Seturile și repetările se aplică doar la exerciții de Forță.")
                    sets = 0
                    reps = 0

            calc_sets = sets if is_strength else 0
            calc_reps = reps if is_strength else 0
            estimated_burned = DailyLog.calculate_hybrid_calories(
                (selected_activity["category"] or "").strip(),
                selected_activity["met"],
                latest_weight,
                duration,
                calc_sets,
                calc_reps
            )
            st.caption(f"🔥 Calorii estimate consumate: **{estimated_burned} kcal**")

            if st.button("Salvează antrenamentul", width="stretch", key="btn_save_act", type="primary"):
                db_sets = calc_sets if calc_sets > 0 else None
                db_reps = calc_reps if calc_reps > 0 else None

                try:
                    act_log_entry = ActivityLog(
                        log_id=daily_log.id,
                        activity_id=selected_activity["id"],
                        duration_min=duration,
                        sets=db_sets,
                        reps=db_reps
                    )
                    if act_log_entry.save():
                        daily_log.recalculate_totals()
                        st.session_state["activity_log_msg"] = ("success", f"{selected_activity['name']} adăugat cu succes!")
                        st.rerun(scope="app")
                    else:
                        st.error("Eroare la salvarea înregistrării.")
                except ValueError as ve:
                    st.error(f"Eroare de validare: {ve}")

        render_activity_entry_panel()

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
            visible_activity_entries = df_entries.drop(columns=["_activity_id"], errors="ignore")
            render_table(visible_activity_entries, column_config=activity_log_table_config, max_rows=7)

            @st.fragment
            def render_activity_edit_panel():
                current_entries = DailyLog.get_activity_entries(daily_log.id)
                if current_entries.empty:
                    return

                activity_options = Activity.get_catalog_options()
                if not activity_options:
                    return

                with st.container(border=True):
                    st.markdown("#### ✏️ Editează un antrenament")
                    activity_log_ids = list(current_entries.index)
                    activity_widget_version = st.session_state["activity_log_widget_version"]
                    edit_select_key = f"activity_log_edit_select_{daily_log.id}_{activity_widget_version}"
                    if st.session_state.get(edit_select_key) not in activity_log_ids:
                        st.session_state.pop(edit_select_key, None)

                    saved_activity_log_id = st.session_state.get("activity_log_edit_selected_id")
                    if saved_activity_log_id not in activity_log_ids:
                        st.session_state.pop("activity_log_edit_selected_id", None)
                        saved_activity_log_id = None
                    edit_select_index = activity_log_ids.index(saved_activity_log_id) if saved_activity_log_id in activity_log_ids else 0
                    selected_edit_activity_log_id = st.selectbox(
                        "Înregistrare de editat",
                        options=activity_log_ids,
                        format_func=lambda log_entry_id: format_activity_log_option(current_entries, log_entry_id),
                        index=edit_select_index,
                        key=edit_select_key
                    )
                    st.session_state["activity_log_edit_selected_id"] = int(selected_edit_activity_log_id)

                    selected_edit_row = current_entries.loc[selected_edit_activity_log_id]
                    current_activity_id = int(selected_edit_row["_activity_id"])
                    activity_ids = list(activity_options.keys())
                    activity_select_index = activity_ids.index(current_activity_id) if current_activity_id in activity_ids else 0
                    edited_activity_id = st.selectbox(
                        "Activitate nouă",
                        options=activity_ids,
                        format_func=lambda activity_id: activity_options[activity_id]["name"],
                        index=activity_select_index,
                        key=f"activity_log_edit_activity_{selected_edit_activity_log_id}"
                    )

                    edited_activity = activity_options[edited_activity_id]
                    edited_is_strength = is_strength_activity(edited_activity)
                    latest_weight = DailyLog.get_latest_weight(user_id, selected_date)

                    col_edit1, col_edit2 = st.columns(2)
                    with col_edit1:
                        edited_duration = st.number_input(
                            "Durată nouă (minute)",
                            min_value=1,
                            max_value=600,
                            value=int(selected_edit_row["Durată (min)"]),
                            step=5,
                            key=f"activity_log_edit_duration_{selected_edit_activity_log_id}"
                        )
                    with col_edit2:
                        if edited_is_strength:
                            edited_sets = st.number_input(
                                "Seturi noi",
                                min_value=1,
                                max_value=50,
                                value=parse_optional_int(selected_edit_row["Seturi"], 3),
                                step=1,
                                key=f"activity_log_edit_sets_{selected_edit_activity_log_id}"
                            )
                            edited_reps = st.number_input(
                                "Repetări noi pe set",
                                min_value=1,
                                max_value=200,
                                value=parse_optional_int(selected_edit_row["Repetări"], 12),
                                step=1,
                                key=f"activity_log_edit_reps_{selected_edit_activity_log_id}"
                            )
                        else:
                            st.info("📌 Seturile și repetările se aplică doar la exerciții de Forță.")
                            edited_sets = 0
                            edited_reps = 0

                    calc_sets = edited_sets if edited_is_strength else 0
                    calc_reps = edited_reps if edited_is_strength else 0
                    estimated_burned = DailyLog.calculate_hybrid_calories(
                        (edited_activity["category"] or "").strip(),
                        edited_activity["met"],
                        latest_weight,
                        edited_duration,
                        calc_sets,
                        calc_reps
                    )
                    st.caption(f"🔥 Calorii estimate după modificare: **{estimated_burned} kcal**")

                    if st.button("Salvează modificările", width="stretch", key="btn_update_activity_log", type="primary"):
                        db_sets = calc_sets if calc_sets > 0 else None
                        db_reps = calc_reps if calc_reps > 0 else None

                        try:
                            if ActivityLog.update(
                                int(selected_edit_activity_log_id),
                                user_id,
                                edited_activity["id"],
                                edited_duration,
                                db_sets,
                                db_reps
                            ):
                                daily_log.recalculate_totals()
                                st.session_state["activity_log_edit_selected_id"] = int(selected_edit_activity_log_id)
                                st.session_state["activity_log_delete_selected_id"] = int(selected_edit_activity_log_id)
                                st.session_state["activity_log_msg"] = ("success", "Antrenamentul a fost actualizat cu succes.")
                                st.session_state["activity_log_reset_edit_delete_widgets"] = True
                                st.rerun(scope="app")
                            else:
                                st.error("Eroare la actualizarea antrenamentului.")
                        except ValueError as ve:
                            st.error(f"Eroare de validare: {ve}")

            @st.fragment
            def render_activity_delete_panel():
                current_entries = DailyLog.get_activity_entries(daily_log.id)
                if current_entries.empty:
                    return

                with st.container(border=True):
                    st.markdown("#### 🗑️ Șterge un antrenament")
                    activity_log_ids = list(current_entries.index)
                    activity_widget_version = st.session_state["activity_log_widget_version"]
                    delete_select_key = f"activity_log_delete_select_{daily_log.id}_{activity_widget_version}"
                    delete_confirm_key = f"activity_log_delete_confirm_{daily_log.id}_{activity_widget_version}"
                    if st.session_state.get(delete_select_key) not in activity_log_ids:
                        st.session_state.pop(delete_select_key, None)

                    saved_delete_activity_log_id = st.session_state.get("activity_log_delete_selected_id")
                    if saved_delete_activity_log_id not in activity_log_ids:
                        st.session_state.pop("activity_log_delete_selected_id", None)
                        saved_delete_activity_log_id = None
                    delete_select_index = activity_log_ids.index(saved_delete_activity_log_id) if saved_delete_activity_log_id in activity_log_ids else 0
                    selected_activity_log_id = st.selectbox(
                        "Înregistrare",
                        options=activity_log_ids,
                        format_func=lambda log_entry_id: format_activity_log_option(current_entries, log_entry_id),
                        index=delete_select_index,
                        key=delete_select_key
                    )
                    st.session_state["activity_log_delete_selected_id"] = int(selected_activity_log_id)
                    confirm_activity_delete = st.checkbox(
                        "Confirm ștergerea acestui antrenament",
                        key=delete_confirm_key
                    )

                    if st.button("Șterge antrenamentul", width="stretch", key="btn_delete_activity_log", type="tertiary"):
                        if not confirm_activity_delete:
                            st.warning("Bifează confirmarea înainte de ștergere.")
                        elif ActivityLog.delete(int(selected_activity_log_id), user_id):
                            daily_log.recalculate_totals()
                            if st.session_state.get("activity_log_edit_selected_id") == int(selected_activity_log_id):
                                del st.session_state["activity_log_edit_selected_id"]
                            if st.session_state.get("activity_log_delete_selected_id") == int(selected_activity_log_id):
                                del st.session_state["activity_log_delete_selected_id"]
                            st.session_state["activity_log_msg"] = ("success", "Antrenamentul a fost șters cu succes.")
                            st.session_state["activity_log_reset_edit_delete_widgets"] = True
                            st.rerun(scope="app")
                        else:
                            st.error("Eroare la ștergerea antrenamentului.")

            render_activity_edit_panel()
            render_activity_delete_panel()

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
        if "custom_meal_edit_ingredients" not in st.session_state:
            st.session_state["custom_meal_edit_ingredients"] = []
        if "custom_meal_edit_row_counter" not in st.session_state:
            st.session_state["custom_meal_edit_row_counter"] = 0
        if "custom_meal_widget_version" not in st.session_state:
            st.session_state["custom_meal_widget_version"] = 0

        custom_meal_message = st.session_state.pop("custom_meal_msg", None)
        if st.session_state.pop("custom_meal_reset_widgets", False):
            st.session_state["custom_meal_widget_version"] += 1
            custom_meal_widget_keys = [
                key for key in st.session_state.keys()
                if key.startswith((
                    "custom_meal_details_select_",
                    "custom_meal_edit_select_",
                    "custom_meal_edit_name_",
                    "custom_meal_edit_qty_",
                    "custom_meal_edit_add_food_",
                    "custom_meal_edit_add_quantity_",
                    "custom_meal_archive_select_",
                    "custom_meal_restore_select_",
                ))
            ]
            for key in custom_meal_widget_keys:
                del st.session_state[key]

        def show_custom_meal_message(message):
            if not message:
                return

            message_type, message_text = message
            icon = "✅" if message_type == "success" else "⚠️" if message_type == "warning" else "❌"
            st.toast(message_text, icon=icon)

        def load_custom_meal_edit_state(meal_id, meal_options):
            ingredients = CustomMeal.get_ingredients(meal_id, user_id)
            for ingredient in ingredients:
                ingredient["row_key"] = f"existing_{ingredient['ingredient_id']}"

            st.session_state["custom_meal_edit_loaded_id"] = int(meal_id)
            st.session_state["custom_meal_edit_ingredients"] = ingredients

        show_custom_meal_message(custom_meal_message)

        food_options = FoodItem.get_catalog_options()

        ingredient_table_config = {
            "Ingredient": st.column_config.TextColumn("Ingredient", width="medium"),
            "Cantitate (g)": st.column_config.NumberColumn("Cantitate", format="%.1f g", width="small"),
            "Calorii": st.column_config.NumberColumn("Calorii", format="%.1f kcal", width="small"),
            "Proteine (g)": st.column_config.NumberColumn("Proteine", format="%.1f g", width="small"),
            "Carbohidrați (g)": st.column_config.NumberColumn("Carbohidrați", format="%.1f g", width="small"),
            "Grăsimi (g)": st.column_config.NumberColumn("Grăsimi", format="%.1f g", width="small"),
        }

        def render_ingredient_table(dataframe):
            st.dataframe(
                dataframe,
                width="stretch",
                height=get_table_height(dataframe),
                hide_index=True,
                column_config=ingredient_table_config,
                row_height=32
            )

        def render_custom_meal_cards(meal_options):
            for meal in meal_options.values():
                is_archived = meal["status"] == CustomMeal.ARCHIVED_STATUS
                card_class = "custom-meal-card archived" if is_archived else "custom-meal-card active"
                status_class = "status-badge archived" if is_archived else "status-badge active"
                st.markdown(
                    f"""
                    <div class="{card_class}">
                        <div class="custom-meal-card-header">
                            <strong>{meal['recipe_name']}</strong>
                            <span class="{status_class}">{meal['status']}</span>
                        </div>
                        <div class="custom-meal-card-grid">
                            <div><span>Cantitate</span><strong>{meal['quantity_g']:.0f} g</strong></div>
                            <div><span>Calorii</span><strong>{meal['calories']:.0f} kcal</strong></div>
                            <div><span>Proteine</span><strong>{meal['protein_g']:.1f} g</strong></div>
                            <div><span>Carbohidrați</span><strong>{meal['carbs_g']:.1f} g</strong></div>
                            <div><span>Grăsimi</span><strong>{meal['fats_g']:.1f} g</strong></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

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
                if st.button("Adaugă ingredient", width="stretch", key="btn_add_custom_meal_ingredient", type="primary"):
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
                if st.button("Golește lista", width="stretch", key="btn_clear_custom_meal_ingredients", type="tertiary"):
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
            render_ingredient_table(df_pending)

            _, col_quantity, col_calories, _ = st.columns([0.85, 1, 1, 0.15])
            col_quantity.metric("Cantitate totală", f"{total_quantity:.0f} g")
            col_calories.metric("Calorii totale", f"{total_calories:.0f} kcal")

            st.markdown("<br>", unsafe_allow_html=True)

            _, col_protein, col_carbs, col_fats, _ = st.columns([0.75, 1, 1, 1, 0.05])
            col_protein.caption("Proteine")
            col_protein.metric(" ", f"{total_protein:.1f} g", label_visibility="collapsed")
            col_carbs.caption("Carbohidrați")
            col_carbs.metric(" ", f"{total_carbs:.1f} g", label_visibility="collapsed")
            col_fats.caption("Grăsimi")
            col_fats.metric(" ", f"{total_fats:.1f} g", label_visibility="collapsed")

            if st.button("Salvează masa personalizată", width="stretch", key="btn_save_custom_meal", type="primary"):
                if not recipe_name.strip():
                    st.warning("Introdu o denumire pentru masa personalizată.")
                elif not CustomMeal.is_valid_recipe_name(recipe_name):
                    st.warning("Denumirea mesei trebuie să înceapă cu o literă.")
                else:
                    saved_meal = CustomMeal.create_with_ingredients(
                        user_id=user_id,
                        recipe_name=recipe_name,
                        ingredients=pending_ingredients
                    )
                    if saved_meal:
                        st.session_state["custom_meal_ingredients"] = []
                        st.session_state["custom_meal_details_selected_id"] = int(saved_meal.id)
                        st.session_state["custom_meal_edit_selected_id"] = int(saved_meal.id)
                        st.session_state["custom_meal_edit_loaded_id"] = None
                        st.session_state["custom_meal_msg"] = ("success", f"Masa personalizată „{saved_meal.recipe_name}” a fost salvată.")
                        st.session_state["custom_meal_reset_widgets"] = True
                        st.rerun()
                    else:
                        st.error("Eroare la salvarea mesei personalizate.")
        else:
            st.info("Adaugă cel puțin un ingredient pentru a salva o masă personalizată.")

        st.divider()
        st.subheader("📋 Mesele tale personalizate")
        custom_meal_options = CustomMeal.get_user_meal_options(user_id, include_archived=True)
        if custom_meal_options:
            render_custom_meal_cards(custom_meal_options)

            active_meal_options = {
                meal_id: meal
                for meal_id, meal in custom_meal_options.items()
                if meal["status"] == CustomMeal.ACTIVE_STATUS
            }
            archived_meal_options = {
                meal_id: meal
                for meal_id, meal in custom_meal_options.items()
                if meal["status"] == CustomMeal.ARCHIVED_STATUS
            }
            custom_meal_ids = list(custom_meal_options.keys())
            custom_meal_widget_version = st.session_state["custom_meal_widget_version"]

            with st.container(border=True):
                st.markdown("#### Arhivă mese personalizate")
                archive_col, restore_col = st.columns(2)

                with archive_col:
                    st.caption("Scoate o masă activă din lista de folosire viitoare.")
                    if active_meal_options:
                        active_meal_ids = list(active_meal_options.keys())
                        selected_archive_meal_id = st.selectbox(
                            "Masă activă",
                            options=active_meal_ids,
                            format_func=lambda meal_id: active_meal_options[meal_id]["recipe_name"],
                            key=f"custom_meal_archive_select_{custom_meal_widget_version}"
                        )
                        if st.button("Arhivează masa", width="stretch", key="btn_archive_custom_meal", type="tertiary"):
                            if CustomMeal.archive(selected_archive_meal_id, user_id):
                                st.session_state["custom_meal_msg"] = (
                                    "success",
                                    f"Masa „{active_meal_options[selected_archive_meal_id]['recipe_name']}” a fost arhivată."
                                )
                                st.session_state["custom_meal_reset_widgets"] = True
                                st.rerun()
                            else:
                                st.error("Eroare la arhivarea mesei personalizate.")
                    else:
                        st.info("Nu ai mese active de arhivat.")

                with restore_col:
                    st.caption("Readuce o masă arhivată în Jurnal Alimentar.")
                    if archived_meal_options:
                        archived_meal_ids = list(archived_meal_options.keys())
                        selected_restore_meal_id = st.selectbox(
                            "Masă arhivată",
                            options=archived_meal_ids,
                            format_func=lambda meal_id: archived_meal_options[meal_id]["recipe_name"],
                            key=f"custom_meal_restore_select_{custom_meal_widget_version}"
                        )
                        if st.button("Reactivează masa", width="stretch", key="btn_restore_custom_meal", type="primary"):
                            if CustomMeal.restore(selected_restore_meal_id, user_id):
                                st.session_state["custom_meal_msg"] = (
                                    "success",
                                    f"Masa „{archived_meal_options[selected_restore_meal_id]['recipe_name']}” a fost reactivată."
                                )
                                st.session_state["custom_meal_reset_widgets"] = True
                                st.rerun()
                            else:
                                st.error("Eroare la reactivarea mesei personalizate.")
                    else:
                        st.info("Nu ai mese arhivate.")

            details_select_key = f"custom_meal_details_select_{custom_meal_widget_version}"
            saved_details_meal_id = st.session_state.get("custom_meal_details_selected_id")
            if saved_details_meal_id not in custom_meal_ids:
                st.session_state.pop("custom_meal_details_selected_id", None)
                saved_details_meal_id = None
            details_select_index = custom_meal_ids.index(saved_details_meal_id) if saved_details_meal_id in custom_meal_ids else 0
            st.markdown("#### Vezi ingredientele pentru")
            selected_saved_meal_id = st.selectbox(
                "Alege masa pentru detalii",
                options=custom_meal_ids,
                format_func=lambda meal_id: custom_meal_options[meal_id]["recipe_name"],
                index=details_select_index,
                key=details_select_key,
                label_visibility="collapsed"
            )
            st.session_state["custom_meal_details_selected_id"] = int(selected_saved_meal_id)
            selected_saved_meal = custom_meal_options[selected_saved_meal_id]
            df_ingredients = CustomMeal.get_ingredients_as_dataframe(selected_saved_meal["id"], user_id)
            if not df_ingredients.empty:
                render_ingredient_table(df_ingredients)

            st.divider()
            st.subheader("✏️ Editează o masă personalizată")
            edit_select_key = f"custom_meal_edit_select_{custom_meal_widget_version}"
            saved_edit_meal_id = st.session_state.get("custom_meal_edit_selected_id")
            if saved_edit_meal_id not in custom_meal_ids:
                st.session_state.pop("custom_meal_edit_selected_id", None)
                saved_edit_meal_id = None
            edit_select_index = custom_meal_ids.index(saved_edit_meal_id) if saved_edit_meal_id in custom_meal_ids else 0
            selected_edit_meal_id = st.selectbox(
                "Masă de editat",
                options=custom_meal_ids,
                format_func=lambda meal_id: custom_meal_options[meal_id]["recipe_name"],
                index=edit_select_index,
                key=edit_select_key
            )
            st.session_state["custom_meal_edit_selected_id"] = int(selected_edit_meal_id)

            if st.session_state.get("custom_meal_edit_loaded_id") != int(selected_edit_meal_id):
                load_custom_meal_edit_state(selected_edit_meal_id, custom_meal_options)

            edit_name_key = f"custom_meal_edit_name_{selected_edit_meal_id}_{custom_meal_widget_version}"
            edited_recipe_name = st.text_input(
                "Denumire nouă masă",
                value=custom_meal_options[selected_edit_meal_id]["recipe_name"],
                key=edit_name_key
            )
            edit_ingredients = st.session_state["custom_meal_edit_ingredients"]

            if food_options:
                col_add_food, col_add_quantity = st.columns(2)
                with col_add_food:
                    selected_edit_ingredient_id = st.selectbox(
                        "Ingredient de adăugat",
                        options=list(food_options.keys()),
                        format_func=lambda food_id: food_options[food_id]["name"],
                        key=f"custom_meal_edit_add_food_{selected_edit_meal_id}"
                    )
                with col_add_quantity:
                    edit_ingredient_quantity = st.number_input(
                        "Cantitate ingredient nou (g)",
                        min_value=1.0,
                        max_value=5000.0,
                        value=100.0,
                        step=1.0,
                        key=f"custom_meal_edit_add_quantity_{selected_edit_meal_id}"
                    )

                if st.button("Adaugă ingredient în rețetă", width="stretch", key="btn_add_custom_meal_edit_ingredient", type="primary"):
                    selected_edit_ingredient = food_options[selected_edit_ingredient_id]
                    st.session_state["custom_meal_edit_row_counter"] += 1
                    edit_ingredients.append({
                        "ingredient_id": None,
                        "row_key": f"new_{st.session_state['custom_meal_edit_row_counter']}",
                        "food_id": selected_edit_ingredient["id"],
                        "name": selected_edit_ingredient["name"],
                        "quantity_g": float(edit_ingredient_quantity),
                        "calories_100g": selected_edit_ingredient["calories_100g"],
                        "protein_g": selected_edit_ingredient["protein_g"],
                        "carbs_g": selected_edit_ingredient["carbs_g"],
                        "fats_g": selected_edit_ingredient["fats_g"],
                    })
                    st.rerun()
            else:
                st.warning("Catalogul de alimente este gol. Nu poți adăuga ingrediente noi momentan.")

            if edit_ingredients:
                st.caption("Ingrediente curente")
                for ingredient_index, ingredient in enumerate(list(edit_ingredients)):
                    row_key = ingredient["row_key"]
                    with st.container(border=True):
                        col_name, col_quantity, col_remove = st.columns([2.2, 1, 0.75], vertical_alignment="center")
                        with col_name:
                            st.markdown(f"**{ingredient['name']}**")
                        with col_quantity:
                            updated_quantity = st.number_input(
                                "Cantitate (g)",
                                min_value=1.0,
                                max_value=5000.0,
                                value=float(ingredient["quantity_g"]),
                                step=1.0,
                                key=f"custom_meal_edit_qty_{selected_edit_meal_id}_{row_key}",
                                label_visibility="collapsed"
                            )
                        with col_remove:
                            if st.button(
                                "Elimină",
                                key=f"btn_remove_custom_meal_edit_{selected_edit_meal_id}_{row_key}",
                                type="tertiary",
                                width="stretch"
                            ):
                                edit_ingredients.pop(ingredient_index)
                                st.rerun()

                    edit_ingredients[ingredient_index]["quantity_g"] = float(updated_quantity)

                edit_rows = []
                edit_total_quantity = 0.0
                edit_total_calories = 0.0
                edit_total_protein = 0.0
                edit_total_carbs = 0.0
                edit_total_fats = 0.0

                for ingredient in edit_ingredients:
                    quantity_g = ingredient["quantity_g"]
                    calories = ingredient["calories_100g"] * quantity_g / 100.0
                    protein = ingredient["protein_g"] * quantity_g / 100.0
                    carbs = ingredient["carbs_g"] * quantity_g / 100.0
                    fats = ingredient["fats_g"] * quantity_g / 100.0

                    edit_total_quantity += quantity_g
                    edit_total_calories += calories
                    edit_total_protein += protein
                    edit_total_carbs += carbs
                    edit_total_fats += fats

                    edit_rows.append([
                        ingredient["name"],
                        round(quantity_g, 2),
                        round(calories, 2),
                        round(protein, 2),
                        round(carbs, 2),
                        round(fats, 2),
                    ])

                df_edit = pd.DataFrame(
                    edit_rows,
                    columns=["Ingredient", "Cantitate (g)", "Calorii", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)"]
                )
                render_ingredient_table(df_edit)

                _, col_edit_quantity, col_edit_calories, _ = st.columns([0.85, 1, 1, 0.15])
                col_edit_quantity.metric("Cantitate totală", f"{edit_total_quantity:.0f} g")
                col_edit_calories.metric("Calorii totale", f"{edit_total_calories:.0f} kcal")

                st.markdown("<br>", unsafe_allow_html=True)

                _, col_edit_protein, col_edit_carbs, col_edit_fats, _ = st.columns([0.75, 1, 1, 1, 0.05])
                col_edit_protein.caption("Proteine")
                col_edit_protein.metric(" ", f"{edit_total_protein:.1f} g", label_visibility="collapsed")
                col_edit_carbs.caption("Carbohidrați")
                col_edit_carbs.metric(" ", f"{edit_total_carbs:.1f} g", label_visibility="collapsed")
                col_edit_fats.caption("Grăsimi")
                col_edit_fats.metric(" ", f"{edit_total_fats:.1f} g", label_visibility="collapsed")

            if st.button("Salvează modificările mesei", width="stretch", key="btn_update_custom_meal", type="primary"):
                if not edited_recipe_name.strip():
                    st.warning("Introdu o denumire pentru masa personalizată.")
                elif not CustomMeal.is_valid_recipe_name(edited_recipe_name):
                    st.warning("Denumirea mesei trebuie să înceapă cu o literă.")
                elif not edit_ingredients:
                    st.warning("Masa personalizată trebuie să conțină cel puțin un ingredient.")
                else:
                    affected_log_ids = CustomMeal.get_affected_daily_log_ids(selected_edit_meal_id, user_id)
                    updated_meal = CustomMeal.update_with_ingredients(
                        meal_id=selected_edit_meal_id,
                        user_id=user_id,
                        recipe_name=edited_recipe_name,
                        ingredients=edit_ingredients
                    )
                    if updated_meal:
                        recalculated_logs = 0
                        for log_id in affected_log_ids:
                            affected_daily_log = DailyLog.get_by_id(log_id, user_id)
                            if affected_daily_log and affected_daily_log.recalculate_totals():
                                recalculated_logs += 1

                        st.session_state["custom_meal_details_selected_id"] = int(selected_edit_meal_id)
                        st.session_state["custom_meal_edit_selected_id"] = int(selected_edit_meal_id)
                        st.session_state["custom_meal_edit_loaded_id"] = None
                        st.session_state["custom_meal_msg"] = (
                            "success",
                            f"Masa personalizată „{edited_recipe_name.strip()}” a fost actualizată. Jurnale recalculate: {recalculated_logs}."
                        )
                        st.session_state["custom_meal_reset_widgets"] = True
                        st.rerun()
                    else:
                        st.error("Eroare la actualizarea mesei personalizate.")
        else:
            st.info("Nu ai încă mese personalizate salvate.")
   
    elif choice == "Catalog Alimente":
        st.header("🍎 Catalog Alimente")
        st.subheader("Baza de date nutrițională")
        df_foods = FoodItem.get_all_as_dataframe()
        if not df_foods.empty:
            render_table(df_foods, column_config=food_catalog_table_config)
        else:
            st.info("Catalogul este gol în acest moment. Administratorul va adăuga date în curând.")

    elif choice == "Catalog Activități":
        st.header("🏃‍♂️ Catalog Activități Fizice")
        st.subheader("Lista activităților disponibile")
        df_activities = Activity.get_all_as_dataframe()
        if not df_activities.empty:
            render_table(df_activities, column_config=activity_catalog_table_config)
        else:
            st.info("Catalogul de activități este gol în acest moment.")
            
    # User Logout Button
    st.sidebar.divider()
    if st.sidebar.button("Deconectare", width="stretch", type="tertiary"):
        st.session_state.clear()
        st.rerun()
