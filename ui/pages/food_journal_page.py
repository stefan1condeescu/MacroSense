import datetime
import streamlit as st
from models.tracking import CustomMeal, DailyLog, FoodItem, FoodLog
from ui.formatters import format_food_entries_for_display, format_time_for_display
from ui.tables import food_log_table_config, render_table


def render_food_journal_page() -> None:
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
