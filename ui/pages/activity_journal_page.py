import datetime
from typing import Any

import streamlit as st
from models.tracking import Activity, ActivityLog, DailyLog, WeightLog
from services.analytics.dashboard_data import get_daily_energy_estimate
from ui.activity_selection import (
    build_activity_selection_dataframe,
    build_activity_selection_display_dataframe,
    build_activity_selection_state_key,
    format_activity_category_for_display,
    format_activity_met_method_for_display,
    get_activity_category_filter_options,
)
from ui.activity_validation import (
    duration_range_help_for_ui,
    validate_duration_minutes_for_ui,
    validate_reps_for_ui,
    validate_sets_for_ui,
)
from ui.journal_energy_summary import render_daily_energy_summary
from ui.language import translate, translated_selection_key
from ui.tables import get_table_height, render_activity_log_cards


ACTIVITY_JOURNAL_DATE_KEY = "activity_journal_selected_date"
MONTH_SOURCE_TEXT = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def is_strength_activity(activity) -> bool:
    """Use the raw stored category for strength-specific behavior."""
    return bool(activity) and (activity["category"] or "").strip() == "Forță"


def format_activity_journal_date(value: datetime.date) -> str:
    """Format a journal date without relying on the operating-system locale."""
    month = translate(MONTH_SOURCE_TEXT[value.month])
    return f"{value.day} {month} {value.year}"


def format_activity_log_option(entries_df, log_entry_id) -> str:
    """Format one stable activity-log ID for an edit or delete selector."""
    row = entries_df.loc[log_entry_id]
    duration = float(row["Durată (min)"])
    formatted_duration = f"{duration:.1f}".rstrip("0").rstrip(".")
    category = format_activity_category_for_display(row["Categorie"])
    return (
        f"{row['Activitate']} "
        f"({category}, {formatted_duration} min, {row['Calorii Arse']} kcal)"
    )


def validate_manual_calories_input(value) -> str | None:
    """Return a bilingual manual-calorie error while preserving model limits."""
    try:
        ActivityLog.validate_manual_calories(value)
    except ValueError:
        return translate(
            "Manual calories must be between {minimum:.0f} and {maximum:.0f} kcal.",
            minimum=ActivityLog.MIN_MANUAL_CALORIES_BURNED,
            maximum=ActivityLog.MAX_MANUAL_CALORIES_BURNED,
        )
    return None


def _float_or_zero(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _sum_activity_breakdown_category(activity_breakdown, category: str) -> float:
    if activity_breakdown is None or activity_breakdown.empty:
        return 0.0
    if "category" not in activity_breakdown or "total_calories_burned" not in activity_breakdown:
        return 0.0

    category_values = activity_breakdown.loc[
        activity_breakdown["category"] == category,
        "total_calories_burned",
    ]
    return _float_or_zero(category_values.sum())


def render_activity_journal_page() -> None:
    st.header(f"🏋️‍♂️ {translate('Physical activity journal')}")

    today = datetime.date.today()
    selected_date = st.date_input(
        translate("Select day:"),
        value=today,
        max_value=today,
        key=ACTIVITY_JOURNAL_DATE_KEY,
    )
    date_is_future = selected_date > today
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
                "activity_log_edit_activity_search_",
                "activity_log_edit_activity_category_",
                "activity_log_edit_manual_override_",
                "activity_log_edit_manual_calories_",
            ))
        ]
        for key in activity_widget_keys:
            del st.session_state[key]
    
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error(translate("Invalid session. Please log in again."))
        st.stop()
    
    if date_is_future:
        st.error(translate("You cannot save workouts for a future date."))

    daily_log = None if date_is_future else DailyLog.get_for_date(user_id, selected_date)
    energy_estimate = {} if date_is_future else get_daily_energy_estimate(user_id, selected_date)
    
    def show_activity_log_message(message):
        if not message:
            return
    
        message_type, message_text = message
        icon = "✅" if message_type == "success" else "⚠️" if message_type == "warning" else "❌"
        st.toast(message_text, icon=icon)
    
    def parse_optional_int(value, default_value):
        if value in (None, "-", ""):
            return default_value
        return int(float(value))

    def parse_optional_float(value):
        if value in (None, "-", "") or (isinstance(value, float) and value != value):
            return None
        return float(value)

    def get_first_error(*errors) -> str | None:
        return next((error for error in errors if error), None)

    def render_activity_selector(
        activity_options: dict,
        key_prefix: str,
        caption_text: str,
        default_activity_id: int = None,
    ) -> int | None:
        filter_col, category_col = st.columns([2, 1])
        with filter_col:
            search_text = st.text_input(
                translate("Search for activity"),
                placeholder=translate("E.g. running, push-ups, chest press"),
                key=f"{key_prefix}_activity_search"
            )
        with category_col:
            category_filter = st.selectbox(
                translate("Category"),
                get_activity_category_filter_options(activity_options),
                format_func=format_activity_category_for_display,
                key=translated_selection_key(f"{key_prefix}_activity_category")
            )

        activity_selection_df = build_activity_selection_dataframe(
            activity_options,
            search_text,
            category_filter,
        )
        if activity_selection_df.empty:
            st.info(
                translate(
                    "No activities match the selected search and category."
                )
            )
            return default_activity_id

        st.caption(caption_text)
        activity_selection_display_df = build_activity_selection_display_dataframe(
            activity_selection_df
        )
        selection_state = st.dataframe(
            activity_selection_display_df,
            width="stretch",
            height=get_table_height(activity_selection_df, max_rows=8),
            hide_index=True,
            column_order=["Denumire", "Categorie", "Sursă", "Metodă MET", "MET"],
            column_config={
                "Denumire": st.column_config.TextColumn(translate("Name"), width="medium"),
                "Categorie": st.column_config.TextColumn(translate("Category"), width="small"),
                "Sursă": st.column_config.TextColumn(translate("Source"), width="small"),
                "Metodă MET": st.column_config.TextColumn(translate("MET method"), width="medium"),
                "MET": st.column_config.NumberColumn("MET", format="%.1f", width="small"),
            },
            key=build_activity_selection_state_key(
                search_text,
                category_filter,
                f"{key_prefix}_activity_selection_table"
            ),
            on_select="rerun",
            selection_mode="single-row",
            row_height=32
        )
        selected_rows = selection_state.selection.rows
        if selected_rows and selected_rows[0] < len(activity_selection_df):
            return int(activity_selection_df.iloc[selected_rows[0]]["_activity_id"])
        return default_activity_id

    def format_reference_date(value) -> str:
        if isinstance(value, datetime.datetime):
            return value.date().strftime("%d.%m.%Y")
        if isinstance(value, datetime.date):
            return value.strftime("%d.%m.%Y")
        return str(value)
    
    show_activity_log_message(activity_log_message)
    if not date_is_future:
        render_daily_energy_summary(energy_estimate)
    weight_reference = WeightLog.get_reference_for_user(user_id, selected_date)
    if weight_reference["uses_future_reference"] and weight_reference["source_date"]:
        st.warning(
            translate(
                "There was no earlier weight for the selected date. MET calculations use the first available weight: {weight:.1f} kg from {date}.",
                weight=weight_reference["weight"],
                date=format_reference_date(weight_reference["source_date"]),
            )
        )
    elif weight_reference["uses_fallback"]:
        st.warning(
            translate(
                "There is no weight history yet. MET calculations temporarily use 70.0 kg."
            )
        )
    
    @st.fragment
    def render_activity_entry_panel():
        st.subheader(f"➕ {translate('Add workout')}")
        activity_options = Activity.get_catalog_options()
    
        if not activity_options:
            st.warning(
                translate(
                    "The activity catalog is empty. The administrator must add activities first."
                )
            )
            return
    
        selected_activity_id = render_activity_selector(
            activity_options,
            key_prefix="activity_log_add",
            caption_text=translate(
                "Select the activity from the table below. The Source and MET method columns explain where the MET value comes from."
            ),
        )
        selected_activity = activity_options.get(selected_activity_id) if selected_activity_id else None
        if selected_activity:
            st.caption(
                translate(
                    "MET source: {source} · {method}",
                    source=selected_activity.get("source_label", "MacroSense"),
                    method=format_activity_met_method_for_display(
                        selected_activity.get("met_method_label", "Manual Admin")
                    ),
                )
            )
        is_strength = is_strength_activity(selected_activity) if selected_activity else False
        latest_weight = weight_reference["weight"]
    
        col1, col2 = st.columns(2)
        with col1:
            duration = st.number_input(
                translate("TOTAL session duration (minutes)"),
                value=30.0,
                step=0.1,
                key="activity_log_duration",
                help=translate(
                    "Total time spent on this exercise, including rest between sets. {range_help}",
                    range_help=duration_range_help_for_ui(),
                ),
            )
    
        with col2:
            if is_strength:
                sets = st.number_input(
                    translate("Sets"),
                    value=3,
                    step=1,
                    key="activity_log_sets",
                )
                reps = st.number_input(
                    translate("Repetitions per set"),
                    value=12,
                    step=1,
                    key="activity_log_reps",
                )
            else:
                st.info(
                    translate(
                        "📌 Sets and repetitions apply only to Strength exercises."
                    )
                )
                sets = 0
                reps = 0
    
        calc_sets = sets if is_strength else 0
        calc_reps = reps if is_strength else 0
        duration_error = validate_duration_minutes_for_ui(
            duration,
            "Total duration",
        )
        sets_error = validate_sets_for_ui(calc_sets) if is_strength else None
        reps_error = validate_reps_for_ui(calc_reps) if is_strength else None
        estimated_burned = None
        if selected_activity and not get_first_error(duration_error, sets_error, reps_error):
            estimated_burned = DailyLog.calculate_hybrid_calories(
                (selected_activity["category"] or "").strip(),
                selected_activity["met"],
                latest_weight,
                duration,
                calc_sets,
                calc_reps
            )
            st.caption(
                translate(
                    "🔥 Estimated calories burned: **{calories} kcal**",
                    calories=estimated_burned,
                )
            )
        elif not selected_activity:
            st.caption(
                translate("Select an activity to calculate the calorie estimate.")
            )

        use_manual_calories = st.checkbox(
            translate("Use calories reported by a watch or cardio machine"),
            key="activity_log_manual_override",
            help=translate(
                "The manual value will be saved instead of the MET/TUT estimate for this entry."
            ),
        )
        manual_calories = None
        manual_calories_error = None
        if use_manual_calories:
            manual_calories = st.number_input(
                translate("Reported calories burned"),
                value=float(max(1, round(estimated_burned or 1, 1))),
                step=1.0,
                key="activity_log_manual_calories"
            )
            manual_calories_error = validate_manual_calories_input(manual_calories)
            if not manual_calories_error:
                st.caption(
                    translate(
                        "The manual value will be saved: **{calories:.1f} kcal**",
                        calories=manual_calories,
                    )
                )

        validation_error = get_first_error(duration_error, sets_error, reps_error, manual_calories_error)
        if validation_error:
            st.error(validation_error)

        if st.button(
            translate("Save workout"),
            width="stretch",
            key="btn_save_act",
            type="primary",
            disabled=selected_activity is None
        ):
            if validation_error:
                return
            if date_is_future:
                st.error(translate("You cannot save workouts for a future date."))
                return

            db_sets = calc_sets if calc_sets > 0 else None
            db_reps = calc_reps if calc_reps > 0 else None
    
            try:
                daily_log_for_write = DailyLog.get_or_create(user_id, selected_date)
                if not daily_log_for_write:
                    st.error(translate("Error accessing the daily journal."))
                    return

                act_log_entry = ActivityLog(
                    log_id=daily_log_for_write.id,
                    activity_id=selected_activity["id"],
                    duration_min=duration,
                    sets=db_sets,
                    reps=db_reps,
                    manual_calories_burned=manual_calories if use_manual_calories else None
                )
                if act_log_entry.save():
                    daily_log_for_write.recalculate_totals()
                    st.session_state["activity_log_msg"] = (
                        "success",
                        translate(
                            "{name} added successfully!",
                            name=selected_activity["name"],
                        ),
                    )
                    st.rerun(scope="app")
                else:
                    st.error(translate("Error saving the entry."))
            except ValueError as ve:
                st.error(translate("Validation error: {error}", error=ve))
    
    render_activity_entry_panel()
    
    st.divider()
    formatted_date = format_activity_journal_date(selected_date)
    st.subheader(
        f"📋 {translate('Workouts performed on {date}', date=formatted_date)}"
    )
    
    df_entries = DailyLog.get_activity_entries(daily_log.id, user_id) if daily_log else None
    
    if df_entries is not None and not df_entries.empty:
        visible_activity_entries = df_entries.drop(columns=["_activity_id", "_manual_calories_burned"], errors="ignore")
        render_activity_log_cards(visible_activity_entries)
    
        @st.fragment
        def render_activity_edit_panel():
            current_entries = DailyLog.get_activity_entries(daily_log.id, user_id)
            if current_entries.empty:
                return
    
            activity_options = Activity.get_catalog_options()
            if not activity_options:
                return
    
            with st.container(border=True):
                st.markdown(f"#### ✏️ {translate('Edit a workout')}")
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
                    translate("Entry to edit"),
                    options=activity_log_ids,
                    format_func=lambda log_entry_id: format_activity_log_option(current_entries, log_entry_id),
                    index=edit_select_index,
                    key=translated_selection_key(edit_select_key)
                )
                st.session_state["activity_log_edit_selected_id"] = int(selected_edit_activity_log_id)
    
                selected_edit_row = current_entries.loc[selected_edit_activity_log_id]
                current_activity_id = int(selected_edit_row["_activity_id"])
                current_activity = activity_options.get(current_activity_id)
                if current_activity:
                    st.caption(
                        translate(
                            "Current activity: **{name}**. Select another row from the table only if you want to change the activity.",
                            name=current_activity["name"],
                        )
                    )
                edited_activity_id = render_activity_selector(
                    activity_options,
                    key_prefix=f"activity_log_edit_{selected_edit_activity_log_id}",
                    caption_text=translate(
                        "Select a new activity from the table, or leave the table unselected to keep the current activity."
                    ),
                    default_activity_id=current_activity_id
                )
    
                edited_activity = activity_options[edited_activity_id]
                st.caption(
                    translate(
                        "MET source: {source} · {method}",
                        source=edited_activity.get("source_label", "MacroSense"),
                        method=format_activity_met_method_for_display(
                            edited_activity.get("met_method_label", "Manual Admin")
                        ),
                    )
                )
                edited_is_strength = is_strength_activity(edited_activity)
                latest_weight = weight_reference["weight"]
    
                col_edit1, col_edit2 = st.columns(2)
                with col_edit1:
                    edited_duration = st.number_input(
                        translate("New duration (minutes)"),
                        value=float(selected_edit_row["Durată (min)"]),
                        step=0.1,
                        key=f"activity_log_edit_duration_{selected_edit_activity_log_id}",
                        help=duration_range_help_for_ui()
                    )
                with col_edit2:
                    if edited_is_strength:
                        edited_sets = st.number_input(
                            translate("New sets"),
                            value=parse_optional_int(selected_edit_row["Seturi"], 3),
                            step=1,
                            key=f"activity_log_edit_sets_{selected_edit_activity_log_id}"
                        )
                        edited_reps = st.number_input(
                            translate("New repetitions per set"),
                            value=parse_optional_int(selected_edit_row["Repetări"], 12),
                            step=1,
                            key=f"activity_log_edit_reps_{selected_edit_activity_log_id}"
                        )
                    else:
                        st.info(
                            translate(
                                "📌 Sets and repetitions apply only to Strength exercises."
                            )
                        )
                        edited_sets = 0
                        edited_reps = 0
    
                calc_sets = edited_sets if edited_is_strength else 0
                calc_reps = edited_reps if edited_is_strength else 0
                edited_duration_error = validate_duration_minutes_for_ui(
                    edited_duration,
                    "New duration",
                )
                edited_sets_error = (
                    validate_sets_for_ui(calc_sets) if edited_is_strength else None
                )
                edited_reps_error = (
                    validate_reps_for_ui(calc_reps) if edited_is_strength else None
                )
                estimated_burned = None
                if not get_first_error(edited_duration_error, edited_sets_error, edited_reps_error):
                    estimated_burned = DailyLog.calculate_hybrid_calories(
                        (edited_activity["category"] or "").strip(),
                        edited_activity["met"],
                        latest_weight,
                        edited_duration,
                        calc_sets,
                        calc_reps
                    )
                    st.caption(
                        translate(
                            "🔥 Estimated calories after the change: **{calories} kcal**",
                            calories=estimated_burned,
                        )
                    )

                current_manual_calories = parse_optional_float(selected_edit_row.get("_manual_calories_burned"))
                edit_manual_override = st.checkbox(
                    translate("Use calories reported by a watch or cardio machine"),
                    value=current_manual_calories is not None,
                    key=f"activity_log_edit_manual_override_{selected_edit_activity_log_id}",
                    help=translate(
                        "The manual value will replace the MET/TUT estimate only for this entry."
                    ),
                )
                edited_manual_calories = None
                edited_manual_calories_error = None
                if edit_manual_override:
                    edited_manual_calories = st.number_input(
                        translate("Reported calories burned"),
                        value=float(current_manual_calories or max(1, round(estimated_burned or 1, 1))),
                        step=1.0,
                        key=f"activity_log_edit_manual_calories_{selected_edit_activity_log_id}"
                    )
                    edited_manual_calories_error = validate_manual_calories_input(edited_manual_calories)
                    if not edited_manual_calories_error:
                        st.caption(
                            translate(
                                "The manual value will be saved: **{calories:.1f} kcal**",
                                calories=edited_manual_calories,
                            )
                        )

                edited_validation_error = get_first_error(
                    edited_duration_error,
                    edited_sets_error,
                    edited_reps_error,
                    edited_manual_calories_error
                )
                if edited_validation_error:
                    st.error(edited_validation_error)
    
                if st.button(
                    translate("Save changes"),
                    width="stretch",
                    key="btn_update_activity_log",
                    type="primary",
                ):
                    if edited_validation_error:
                        return

                    db_sets = calc_sets if calc_sets > 0 else None
                    db_reps = calc_reps if calc_reps > 0 else None
    
                    try:
                        if ActivityLog.update(
                            int(selected_edit_activity_log_id),
                            user_id,
                            edited_activity["id"],
                            edited_duration,
                            db_sets,
                            db_reps,
                            manual_calories_burned=edited_manual_calories if edit_manual_override else None
                        ):
                            daily_log.recalculate_totals()
                            st.session_state["activity_log_edit_selected_id"] = int(selected_edit_activity_log_id)
                            st.session_state["activity_log_msg"] = (
                                "success",
                                translate("The workout was updated successfully."),
                            )
                            st.session_state["activity_log_reset_edit_delete_widgets"] = True
                            st.rerun(scope="app")
                        else:
                            st.error(translate("Error updating the workout."))
                    except ValueError as ve:
                        st.error(translate("Validation error: {error}", error=ve))
    
        @st.fragment
        def render_activity_delete_panel():
            current_entries = DailyLog.get_activity_entries(daily_log.id, user_id)
            if current_entries.empty:
                return
    
            with st.container(border=True):
                st.markdown(f"#### 🗑️ {translate('Delete a workout')}")
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
                    translate("Entry"),
                    options=activity_log_ids,
                    format_func=lambda log_entry_id: format_activity_log_option(current_entries, log_entry_id),
                    index=delete_select_index,
                    key=translated_selection_key(delete_select_key)
                )
                st.session_state["activity_log_delete_selected_id"] = int(selected_activity_log_id)
                confirm_activity_delete = st.checkbox(
                    translate("I confirm deletion of this workout"),
                    key=delete_confirm_key
                )
    
                if st.button(
                    translate("Delete workout"),
                    width="stretch",
                    key="btn_delete_activity_log",
                    type="tertiary",
                ):
                    if not confirm_activity_delete:
                        st.warning(
                            translate("Check the confirmation box before deleting.")
                        )
                    elif ActivityLog.delete(int(selected_activity_log_id), user_id):
                        daily_log.recalculate_totals()
                        DailyLog.delete_if_empty(daily_log.id, user_id)
                        if st.session_state.get("activity_log_edit_selected_id") == int(selected_activity_log_id):
                            del st.session_state["activity_log_edit_selected_id"]
                        if st.session_state.get("activity_log_delete_selected_id") == int(selected_activity_log_id):
                            del st.session_state["activity_log_delete_selected_id"]
                        st.session_state["activity_log_msg"] = (
                            "success",
                            translate("The workout was deleted successfully."),
                        )
                        st.session_state["activity_log_reset_edit_delete_widgets"] = True
                        st.rerun(scope="app")
                    else:
                        st.error(translate("Error deleting the workout."))
    
        render_activity_edit_panel()
        render_activity_delete_panel()
        return
    else:
        st.info(translate("There are no workouts recorded for this day."))
