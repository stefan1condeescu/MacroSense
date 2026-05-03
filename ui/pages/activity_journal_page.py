import datetime
import streamlit as st
from models.tracking import Activity, ActivityLog, DailyLog, WeightLog
from ui.tables import activity_log_table_config, render_table


def render_activity_journal_page() -> None:
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
    
    daily_log = DailyLog.get_for_date(user_id, selected_date)
    
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

    def format_reference_date(value) -> str:
        if isinstance(value, datetime.datetime):
            return value.date().strftime("%d.%m.%Y")
        if isinstance(value, datetime.date):
            return value.strftime("%d.%m.%Y")
        return str(value)
    
    show_activity_log_message(activity_log_message)
    weight_reference = WeightLog.get_reference_for_user(user_id, selected_date)
    if weight_reference["uses_future_reference"] and weight_reference["source_date"]:
        st.warning(
            "Pentru data selectată nu exista o greutate anterioară. "
            f"Calculele MET folosesc prima greutate disponibilă: "
            f"{weight_reference['weight']:.1f} kg din {format_reference_date(weight_reference['source_date'])}."
        )
    elif weight_reference["uses_fallback"]:
        st.warning("Nu există încă un istoric de greutate. Calculele MET folosesc temporar 70.0 kg.")
    
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
        latest_weight = weight_reference["weight"]
    
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
                daily_log_for_write = DailyLog.get_or_create(user_id, selected_date)
                if not daily_log_for_write:
                    st.error("Eroare la accesarea jurnalului zilnic.")
                    return

                act_log_entry = ActivityLog(
                    log_id=daily_log_for_write.id,
                    activity_id=selected_activity["id"],
                    duration_min=duration,
                    sets=db_sets,
                    reps=db_reps
                )
                if act_log_entry.save():
                    daily_log_for_write.recalculate_totals()
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
    
    df_entries = DailyLog.get_activity_entries(daily_log.id, user_id) if daily_log else None
    
    if df_entries is not None and not df_entries.empty:
        visible_activity_entries = df_entries.drop(columns=["_activity_id"], errors="ignore")
        render_table(visible_activity_entries, column_config=activity_log_table_config, max_rows=7)
    
        @st.fragment
        def render_activity_edit_panel():
            current_entries = DailyLog.get_activity_entries(daily_log.id, user_id)
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
                latest_weight = weight_reference["weight"]
    
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
                            st.session_state["activity_log_msg"] = ("success", "Antrenamentul a fost actualizat cu succes.")
                            st.session_state["activity_log_reset_edit_delete_widgets"] = True
                            st.rerun(scope="app")
                        else:
                            st.error("Eroare la actualizarea antrenamentului.")
                    except ValueError as ve:
                        st.error(f"Eroare de validare: {ve}")
    
        @st.fragment
        def render_activity_delete_panel():
            current_entries = DailyLog.get_activity_entries(daily_log.id, user_id)
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
                        DailyLog.delete_if_empty(daily_log.id, user_id)
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
