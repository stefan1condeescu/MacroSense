import datetime
import streamlit as st
from models.tracking import WeightLog
from ui.tables import render_table, weight_log_table_config


def render_weight_journal_page() -> None:
    st.header("⚖️ Jurnal Greutate")

    weight_log_message = st.session_state.pop("weight_log_msg", None)
    if "weight_log_widget_version" not in st.session_state:
        st.session_state["weight_log_widget_version"] = 0

    if st.session_state.pop("weight_log_reset_widgets", False):
        st.session_state["weight_log_widget_version"] += 1
        legacy_weight_widget_keys = {
            "weight_log_edit_select",
            "weight_log_delete_select",
            "weight_log_delete_confirm",
            "weight_log_add_date",
            "weight_log_add_value",
        }
        weight_widget_keys = [
            key for key in st.session_state.keys()
            if key in legacy_weight_widget_keys
            or key.startswith((
                "weight_log_add_date_",
                "weight_log_add_value_",
                "weight_log_edit_select_",
                "weight_log_delete_select_",
                "weight_log_delete_confirm_",
                "weight_log_edit_date_",
                "weight_log_edit_value_",
            ))
        ]
        for key in weight_widget_keys:
            del st.session_state[key]

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("Sesiune invalidă. Te rugăm să te reautentifici.")
        st.stop()

    def show_weight_log_message(message):
        if not message:
            return

        message_type, message_text = message
        icon = "✅" if message_type == "success" else "⚠️" if message_type == "warning" else "❌"
        st.toast(message_text, icon=icon)

    def format_weight_date(value) -> str:
        if isinstance(value, datetime.datetime):
            return value.date().strftime("%d.%m.%Y")
        if isinstance(value, datetime.date):
            return value.strftime("%d.%m.%Y")
        return str(value)

    def normalize_weight_date(value):
        if isinstance(value, datetime.datetime):
            return value.date()
        return value

    def format_weight_option(entries_df, weight_entry_id):
        row = entries_df.loc[weight_entry_id]
        return f"{format_weight_date(row['Data'])} - {float(row['Greutate (kg)']):.1f} kg"

    def has_weight_entry_for_date(entries_df, target_date, excluded_entry_id=None) -> bool:
        if entries_df.empty:
            return False

        normalized_target_date = normalize_weight_date(target_date)
        for entry_id, row in entries_df.iterrows():
            if excluded_entry_id is not None and int(entry_id) == int(excluded_entry_id):
                continue
            if normalize_weight_date(row["Data"]) == normalized_target_date:
                return True
        return False

    def is_weight_in_allowed_range(value) -> bool:
        return WeightLog.MIN_WEIGHT_KG <= float(value) <= WeightLog.MAX_WEIGHT_KG

    def clamp_weight_value(value) -> float:
        return min(max(float(value), WeightLog.MIN_WEIGHT_KG), WeightLog.MAX_WEIGHT_KG)

    def weight_range_error_message() -> str:
        return (
            "Greutatea trebuie să fie între "
            f"{WeightLog.MIN_WEIGHT_KG:.0f} și {WeightLog.MAX_WEIGHT_KG:.0f} kg."
        )

    def recalculate_after_weight_change(before_references: dict) -> int:
        return WeightLog.recalculate_user_daily_logs(user_id, before_references)

    def format_weight_change_message(action: str, recalculated_logs: int) -> str:
        return f"Greutate {action}. Zile afectate: {recalculated_logs}."

    show_weight_log_message(weight_log_message)

    weight_entries = WeightLog.get_user_entries(user_id)

    if not weight_entries.empty:
        latest_entry = weight_entries.iloc[0]
        previous_entry = weight_entries.iloc[1] if len(weight_entries) > 1 else None
        latest_weight = float(latest_entry["Greutate (kg)"])
        previous_weight = float(previous_entry["Greutate (kg)"]) if previous_entry is not None else None
        weight_delta = latest_weight - previous_weight if previous_weight is not None else None

        col_metric1, col_metric2, col_metric3 = st.columns(3)
        col_metric1.metric(
            "Ultima greutate",
            f"{latest_weight:.1f} kg",
            delta=f"{weight_delta:+.1f} kg" if weight_delta is not None else None
        )
        col_metric2.metric("Data ultimei măsurători", format_weight_date(latest_entry["Data"]))
        col_metric3.metric("Înregistrări", f"{len(weight_entries)}")
    else:
        st.info("Nu există încă înregistrări de greutate pentru acest cont.")

    @st.fragment
    def render_weight_entry_panel():
        st.subheader("➕ Adaugă greutate")
        weight_widget_version = st.session_state["weight_log_widget_version"]
        default_weight = 70.0
        if not weight_entries.empty:
            default_weight = float(weight_entries.iloc[0]["Greutate (kg)"])
        default_weight = clamp_weight_value(default_weight)

        col_add1, col_add2 = st.columns(2)
        with col_add1:
            selected_date = st.date_input(
                "Data măsurării",
                value=datetime.date.today(),
                key=f"weight_log_add_date_{weight_widget_version}"
            )
        with col_add2:
            weight_kg = st.number_input(
                "Greutate (kg)",
                value=default_weight,
                step=0.1,
                help=weight_range_error_message(),
                key=f"weight_log_add_value_{weight_widget_version}"
            )

        date_already_exists = has_weight_entry_for_date(weight_entries, selected_date)
        if date_already_exists:
            st.warning("Există deja o greutate pentru această dată. Salvarea va actualiza valoarea existentă.")
        st.caption("Dacă există deja o greutate pentru aceeași zi, valoarea va fi actualizată.")

        if st.button("Salvează greutatea", width="stretch", key="btn_save_weight_log", type="primary"):
            if not is_weight_in_allowed_range(weight_kg):
                st.error(weight_range_error_message())
                return

            try:
                before_references = WeightLog.get_activity_day_weight_references(user_id)
                weight_log = WeightLog(
                    user_id=user_id,
                    log_date=selected_date,
                    weight_kg=weight_kg
                )
                if weight_log.save():
                    recalculated_logs = recalculate_after_weight_change(before_references)
                    if date_already_exists:
                        st.session_state["weight_log_msg"] = (
                            "warning",
                            format_weight_change_message("actualizată", recalculated_logs)
                        )
                    else:
                        st.session_state["weight_log_msg"] = (
                            "success",
                            format_weight_change_message("salvată", recalculated_logs)
                        )
                    st.session_state["weight_log_reset_widgets"] = True
                    st.rerun(scope="app")
                else:
                    st.error("Eroare la salvarea greutății.")
            except ValueError as ve:
                st.error(f"Eroare de validare: {ve}")

    render_weight_entry_panel()

    st.divider()
    st.subheader("📋 Istoric greutate")
    weight_entries = WeightLog.get_user_entries(user_id)

    if weight_entries.empty:
        st.info("Adaugă prima greutate folosind formularul de mai sus.")
        return

    render_table(weight_entries, column_config=weight_log_table_config, max_rows=8)

    @st.fragment
    def render_weight_edit_panel():
        current_entries = WeightLog.get_user_entries(user_id)
        if current_entries.empty:
            return

        with st.container(border=True):
            st.markdown("#### ✏️ Editează o greutate")
            weight_log_ids = list(current_entries.index)
            weight_widget_version = st.session_state["weight_log_widget_version"]
            edit_select_key = f"weight_log_edit_select_{weight_widget_version}"
            if st.session_state.get(edit_select_key) not in weight_log_ids:
                st.session_state.pop(edit_select_key, None)

            saved_weight_log_id = st.session_state.get("weight_log_edit_selected_id")
            if saved_weight_log_id not in weight_log_ids:
                st.session_state.pop("weight_log_edit_selected_id", None)
                saved_weight_log_id = None
            edit_select_index = weight_log_ids.index(saved_weight_log_id) if saved_weight_log_id in weight_log_ids else 0
            selected_weight_log_id = st.selectbox(
                "Înregistrare de editat",
                options=weight_log_ids,
                format_func=lambda entry_id: format_weight_option(current_entries, entry_id),
                index=edit_select_index,
                key=edit_select_key
            )
            st.session_state["weight_log_edit_selected_id"] = int(selected_weight_log_id)

            selected_row = current_entries.loc[selected_weight_log_id]
            existing_dates_by_id = {
                int(entry_id): row["Data"]
                for entry_id, row in current_entries.iterrows()
            }

            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                edited_date = st.date_input(
                    "Dată nouă",
                    value=selected_row["Data"],
                    key=f"weight_log_edit_date_{selected_weight_log_id}_{weight_widget_version}"
                )
            with col_edit2:
                edited_weight = st.number_input(
                    "Greutate nouă (kg)",
                    value=clamp_weight_value(selected_row["Greutate (kg)"]),
                    step=0.1,
                    help=weight_range_error_message(),
                    key=f"weight_log_edit_value_{selected_weight_log_id}_{weight_widget_version}"
                )

            if st.button("Salvează modificările", width="stretch", key="btn_update_weight_log", type="primary"):
                if not is_weight_in_allowed_range(edited_weight):
                    st.error(weight_range_error_message())
                    return

                duplicate_date = any(
                    entry_id != int(selected_weight_log_id) and normalize_weight_date(entry_date) == edited_date
                    for entry_id, entry_date in existing_dates_by_id.items()
                )
                if duplicate_date:
                    st.warning("Există deja o greutate salvată pentru această dată.")
                    return

                try:
                    before_references = WeightLog.get_activity_day_weight_references(user_id)
                    if WeightLog.update(
                        int(selected_weight_log_id),
                        user_id,
                        edited_date,
                        edited_weight
                    ):
                        recalculated_logs = recalculate_after_weight_change(before_references)
                        st.session_state["weight_log_edit_selected_id"] = int(selected_weight_log_id)
                        st.session_state["weight_log_msg"] = (
                            "success",
                            format_weight_change_message("actualizată", recalculated_logs)
                        )
                        st.session_state["weight_log_reset_widgets"] = True
                        st.rerun(scope="app")
                    else:
                        st.error("Eroare la actualizarea greutății.")
                except ValueError as ve:
                    st.error(f"Eroare de validare: {ve}")

    @st.fragment
    def render_weight_delete_panel():
        current_entries = WeightLog.get_user_entries(user_id)
        if current_entries.empty:
            return

        with st.container(border=True):
            st.markdown("#### 🗑️ Șterge o greutate")
            if len(current_entries) <= 1:
                st.info("Păstrăm cel puțin o greutate de referință pentru calculele MET și predicțiile viitoare.")
                return

            weight_log_ids = list(current_entries.index)
            weight_widget_version = st.session_state["weight_log_widget_version"]
            delete_select_key = f"weight_log_delete_select_{weight_widget_version}"
            delete_confirm_key = f"weight_log_delete_confirm_{weight_widget_version}"
            if st.session_state.get(delete_select_key) not in weight_log_ids:
                st.session_state.pop(delete_select_key, None)

            saved_delete_weight_log_id = st.session_state.get("weight_log_delete_selected_id")
            if saved_delete_weight_log_id not in weight_log_ids:
                st.session_state.pop("weight_log_delete_selected_id", None)
                saved_delete_weight_log_id = None
            delete_select_index = weight_log_ids.index(saved_delete_weight_log_id) if saved_delete_weight_log_id in weight_log_ids else 0
            selected_delete_weight_log_id = st.selectbox(
                "Înregistrare",
                options=weight_log_ids,
                format_func=lambda entry_id: format_weight_option(current_entries, entry_id),
                index=delete_select_index,
                key=delete_select_key
            )
            st.session_state["weight_log_delete_selected_id"] = int(selected_delete_weight_log_id)
            confirm_delete = st.checkbox(
                "Confirm ștergerea acestei greutăți",
                key=delete_confirm_key
            )

            if st.button("Șterge greutatea", width="stretch", key="btn_delete_weight_log", type="tertiary"):
                if not confirm_delete:
                    st.warning("Bifează confirmarea înainte de ștergere.")
                    return

                before_references = WeightLog.get_activity_day_weight_references(user_id)
                if WeightLog.delete(int(selected_delete_weight_log_id), user_id):
                    recalculated_logs = recalculate_after_weight_change(before_references)
                    if st.session_state.get("weight_log_edit_selected_id") == int(selected_delete_weight_log_id):
                        del st.session_state["weight_log_edit_selected_id"]
                    if st.session_state.get("weight_log_delete_selected_id") == int(selected_delete_weight_log_id):
                        del st.session_state["weight_log_delete_selected_id"]
                    st.session_state["weight_log_msg"] = (
                        "success",
                        format_weight_change_message("ștearsă", recalculated_logs)
                    )
                    st.session_state["weight_log_reset_widgets"] = True
                    st.rerun(scope="app")
                else:
                    st.error("Eroare la ștergerea greutății.")

    render_weight_edit_panel()
    render_weight_delete_panel()
