import datetime
import streamlit as st
from models.tracking import CustomMeal, DailyLog, FoodItem, FoodLog
from services.analytics.dashboard_data import get_daily_energy_estimate
from ui.food_selection import (
    build_food_selection_dataframe,
    build_food_selection_display_dataframe,
    build_food_selection_state_key,
    format_food_category_for_display,
    format_food_entry_type,
    format_meal_type,
    get_food_category_filter_options,
)
from ui.formatters import format_food_entries_for_display, format_time_for_display
from ui.journal_energy_summary import render_daily_energy_summary
from ui.language import translate, translated_selection_key
from ui.quantity_validation import (
    quantity_range_help_for_ui,
    validate_quantity_g_for_ui,
)
from ui.tables import get_table_height, render_food_log_cards


MEAL_TYPES = list(FoodLog.VALID_MEAL_TYPES)
FOOD_ENTRY_TYPES = ("Aliment din catalog", "Masă personalizată")
FOOD_JOURNAL_DATE_KEY = "food_journal_selected_date"
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


def format_food_journal_date(value: datetime.date) -> str:
    """Format a journal date without relying on the operating-system locale."""
    month = translate(MONTH_SOURCE_TEXT[value.month])
    return f"{value.day} {month} {value.year}"


def format_food_log_option(entries_df, log_entry_id) -> str:
    """Format one stable food-log ID for an edit or delete selector."""
    row = entries_df.loc[log_entry_id]
    meal_time = format_time_for_display(row["Ora"])
    entry_type = format_food_entry_type(row["Tip"])
    meal_type = format_meal_type(row["Masă"])
    return (
        f"{entry_type} - {row['Aliment / Masă']} "
        f"({row['Cantitate (g)']}g, {meal_type}, {meal_time})"
    )


def render_food_journal_page() -> None:
    st.header(f"📔 {translate('Food journal')}")

    today = datetime.date.today()
    selected_date = st.date_input(
        translate("Select day:"),
        value=today,
        max_value=today,
        key=FOOD_JOURNAL_DATE_KEY,
    )
    date_is_future = selected_date > today
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
        st.error(translate("Invalid session. Please log in again."))
        st.stop()
    
    if date_is_future:
        st.error(translate("You cannot save food entries for a future date."))

    daily_log = None if date_is_future else DailyLog.get_for_date(user_id, selected_date)
    energy_estimate = {} if date_is_future else get_daily_energy_estimate(user_id, selected_date)
    
    def show_food_log_message(message):
        if not message:
            return
    
        message_type, message_text = message
        icon = "✅" if message_type == "success" else "⚠️" if message_type == "warning" else "❌"
        st.toast(message_text, icon=icon)
    
    show_food_log_message(food_log_message)
    if not date_is_future:
        render_daily_energy_summary(energy_estimate)
    
    @st.fragment
    def render_food_entry_panel():
        st.subheader(f"➕ {translate('Add food intake')}")
        food_options = FoodItem.get_catalog_options()
        custom_meal_options = CustomMeal.get_user_meal_options(user_id)
    
        entry_type = st.radio(
            translate("Entry type"),
            FOOD_ENTRY_TYPES,
            format_func=format_food_entry_type,
            horizontal=True,
            key=translated_selection_key("food_entry_type")
        )
    
        if entry_type == "Aliment din catalog":
            if not food_options:
                st.warning(
                    translate(
                        "The food catalog is empty. The administrator must add foods first."
                    )
                )
            else:
                filter_col, category_col = st.columns([2, 1])
                with filter_col:
                    food_search_text = st.text_input(
                        translate("Search for food"),
                        placeholder=translate("E.g. bananas, broccoli, salmon"),
                        key="food_log_food_search"
                    )
                with category_col:
                    food_category_filter = st.selectbox(
                        translate("Category"),
                        get_food_category_filter_options(food_options),
                        format_func=format_food_category_for_display,
                        key=translated_selection_key("food_log_food_category_filter")
                    )

                food_selection_df = build_food_selection_dataframe(
                    food_options,
                    food_search_text,
                    food_category_filter
                )
                selected_food_id = None
                if food_selection_df.empty:
                    st.info(
                        translate(
                            "No foods match the selected search and category."
                        )
                    )
                else:
                    st.caption(
                        translate(
                            "Select the food from the table below. The Source column distinguishes MacroSense foods from USDA foods."
                        )
                    )
                    food_selection_display_df = build_food_selection_display_dataframe(
                        food_selection_df
                    )
                    food_selection_state = st.dataframe(
                        food_selection_display_df,
                        width="stretch",
                        height=get_table_height(food_selection_df, max_rows=8),
                        hide_index=True,
                        column_order=["Denumire", "Categorie", "Sursă", "Kcal/100g", "Proteine", "Carbohidrați", "Grăsimi"],
                        column_config={
                            "Denumire": st.column_config.TextColumn(translate("Name"), width="medium"),
                            "Categorie": st.column_config.TextColumn(translate("Category"), width="small"),
                            "Sursă": st.column_config.TextColumn(translate("Source"), width="small"),
                            "Kcal/100g": st.column_config.NumberColumn("Kcal/100g", format="%.1f kcal", width="small"),
                            "Proteine": st.column_config.NumberColumn(translate("Protein"), format="%.1f g", width="small"),
                            "Carbohidrați": st.column_config.NumberColumn(translate("Carbohydrates"), format="%.1f g", width="small"),
                            "Grăsimi": st.column_config.NumberColumn(translate("Fats"), format="%.1f g", width="small"),
                        },
                        key=build_food_selection_state_key(food_search_text, food_category_filter),
                        on_select="rerun",
                        selection_mode="single-row",
                        row_height=32
                    )
                    selected_rows = food_selection_state.selection.rows
                    if selected_rows and selected_rows[0] < len(food_selection_df):
                        selected_food_id = int(food_selection_df.iloc[selected_rows[0]]["_food_id"])

                quantity_col, time_col = st.columns(2)
                with quantity_col:
                    quantity = st.number_input(
                        translate("Quantity (g)"),
                        value=100.0,
                        step=1.0,
                        key="food_log_food_quantity",
                        help=quantity_range_help_for_ui()
                    )
                with time_col:
                    meal_time = st.time_input(
                        translate("Consumption time"),
                        value=datetime.time(12, 0),
                        key="food_log_food_time",
                    )
                meal_type = st.radio(
                    translate("Meal"),
                    MEAL_TYPES,
                    format_func=format_meal_type,
                    horizontal=True,
                    key=translated_selection_key("food_log_food_meal_type"),
                )

                selected_food = food_options.get(selected_food_id) if selected_food_id else None
                quantity_error = validate_quantity_g_for_ui(quantity, "Quantity")
                if selected_food:
                    if quantity_error:
                        st.error(quantity_error)
                    else:
                        estimated_calories = round(selected_food["calories_100g"] * float(quantity) / 100.0, 2)
                        st.caption(
                            translate(
                                "🔥 Selected food: **{name}** ({source}) · Estimated calories: **{calories} kcal**",
                                name=selected_food["name"],
                                source=selected_food.get("source_label", "MacroSense"),
                                calories=estimated_calories,
                            )
                        )
                else:
                    st.caption(
                        translate("Select a food to calculate the calorie estimate.")
                    )

                submit_food = st.button(
                    translate("Save entry"),
                    width="stretch",
                    key="btn_save_food",
                    type="primary",
                    disabled=selected_food is None
                )

                if submit_food:
                    if quantity_error:
                        return
                    if date_is_future:
                        st.error(
                            translate(
                                "You cannot save food entries for a future date."
                            )
                        )
                        return

                    try:
                        daily_log_for_write = DailyLog.get_or_create(user_id, selected_date)
                        if not daily_log_for_write:
                            st.error(translate("Error accessing the daily journal."))
                            return

                        food_log_entry = FoodLog(
                            log_id=daily_log_for_write.id,
                            quantity_g=quantity,
                            meal_type=meal_type,
                            meal_time=meal_time,
                            food_id=selected_food["id"]
                        )
    
                        if food_log_entry.save():
                            daily_log_for_write.recalculate_totals()
                            st.session_state["food_log_msg"] = (
                                "success",
                                translate(
                                    "{name} ({quantity}g) added successfully!",
                                    name=selected_food["name"],
                                    quantity=quantity,
                                ),
                            )
                            st.rerun(scope="app")
                        else:
                            st.error(translate("Error saving the entry."))
                    except ValueError as ve:
                        st.error(translate("Validation error: {error}", error=ve))
        else:
            if not custom_meal_options:
                st.warning(
                    translate(
                        "You have no active custom meals. Create or restore one on the Custom meals page."
                    )
                )
            else:
                col1, col2 = st.columns(2)
                with col1:
                    selected_meal_id = st.selectbox(
                        translate("Custom meal"),
                        options=list(custom_meal_options.keys()),
                        format_func=lambda meal_id: custom_meal_options[meal_id]["recipe_name"],
                        key="food_log_custom_meal_select"
                    )
                    custom_quantity = st.number_input(
                        translate("Consumed quantity (g)"),
                        value=100.0,
                        step=1.0,
                        key="food_log_custom_meal_quantity",
                        help=quantity_range_help_for_ui()
                    )
                with col2:
                    custom_meal_time = st.time_input(
                        translate("Consumption time"),
                        value=datetime.time(12, 0),
                        key="food_log_custom_meal_time",
                    )
                custom_meal_type = st.radio(
                    translate("Meal"),
                    MEAL_TYPES,
                    format_func=format_meal_type,
                    horizontal=True,
                    key=translated_selection_key("food_log_custom_meal_type"),
                )
    
                selected_custom_meal = custom_meal_options[selected_meal_id]
                custom_quantity_error = validate_quantity_g_for_ui(
                    custom_quantity,
                    "Consumed quantity",
                )
                if custom_quantity_error:
                    st.error(custom_quantity_error)
                else:
                    estimated_custom_calories = round(selected_custom_meal["calories_per_g"] * float(custom_quantity), 2)
                    st.caption(
                        translate(
                            "🔥 Estimated calories: **{calories} kcal**",
                            calories=estimated_custom_calories,
                        )
                    )
    
                submit_custom_meal = st.button(
                    translate("Save meal to journal"),
                    width="stretch",
                    key="btn_save_custom_meal_log",
                    type="primary",
                )
    
                if submit_custom_meal:
                    if custom_quantity_error:
                        return
                    if date_is_future:
                        st.error(
                            translate(
                                "You cannot save food entries for a future date."
                            )
                        )
                        return

                    try:
                        daily_log_for_write = DailyLog.get_or_create(user_id, selected_date)
                        if not daily_log_for_write:
                            st.error(translate("Error accessing the daily journal."))
                            return

                        custom_meal_log_entry = FoodLog(
                            log_id=daily_log_for_write.id,
                            quantity_g=custom_quantity,
                            meal_type=custom_meal_type,
                            meal_time=custom_meal_time,
                            custom_meal_id=selected_custom_meal["id"]
                        )
    
                        if custom_meal_log_entry.save():
                            daily_log_for_write.recalculate_totals()
                            st.session_state["food_log_msg"] = (
                                "success",
                                translate(
                                    "Custom meal {name} ({quantity}g) added successfully!",
                                    name=selected_custom_meal["recipe_name"],
                                    quantity=custom_quantity,
                                ),
                            )
                            st.rerun(scope="app")
                        else:
                            st.error(translate("Error saving the custom meal."))
                    except ValueError as ve:
                        st.error(translate("Validation error: {error}", error=ve))
    
    render_food_entry_panel()
        
    st.divider()
    formatted_date = format_food_journal_date(selected_date)
    st.subheader(
        f"📋 {translate('Foods consumed on {date}', date=formatted_date)}"
    )
    
    df_entries = DailyLog.get_food_entries(daily_log.id, user_id) if daily_log else None
    
    has_food_entries = df_entries is not None and not df_entries.empty

    if has_food_entries:
        render_food_log_cards(format_food_entries_for_display(df_entries))
    
        @st.fragment
        def render_food_edit_panel():
            current_entries = DailyLog.get_food_entries(daily_log.id, user_id)
            if current_entries.empty:
                return
    
            with st.container(border=True):
                st.markdown(f"#### ✏️ {translate('Edit an entry')}")
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
                    translate("Entry to edit"),
                    options=food_log_ids,
                    format_func=lambda log_entry_id: format_food_log_option(current_entries, log_entry_id),
                    index=edit_select_index,
                    key=translated_selection_key(edit_select_key)
                )
                st.session_state["food_log_edit_selected_id"] = int(selected_edit_food_log_id)
    
                selected_edit_row = current_entries.loc[selected_edit_food_log_id]
                meal_options = MEAL_TYPES
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
                        translate("New quantity (g)"),
                        value=float(selected_edit_row["Cantitate (g)"]),
                        step=1.0,
                        key=f"food_log_edit_quantity_{selected_edit_food_log_id}",
                        help=quantity_range_help_for_ui()
                    )
                    edited_meal_type = st.selectbox(
                        translate("New meal"),
                        options=meal_options,
                        format_func=format_meal_type,
                        index=meal_type_index,
                        key=translated_selection_key(f"food_log_edit_meal_type_{selected_edit_food_log_id}")
                    )
                with col_edit2:
                    edited_meal_time = st.time_input(
                        translate("New time"),
                        value=current_time,
                        key=f"food_log_edit_time_{selected_edit_food_log_id}"
                    )
    
                if st.button(
                    translate("Save changes"),
                    width="stretch",
                    key="btn_update_food_log",
                    type="primary",
                ):
                    quantity_error = validate_quantity_g_for_ui(
                        edited_quantity,
                        "New quantity",
                    )
                    if quantity_error:
                        st.error(quantity_error)
                        return

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
                            st.session_state["food_log_msg"] = (
                                "success",
                                translate("The entry was updated successfully."),
                            )
                            st.session_state["food_log_reset_edit_delete_widgets"] = True
                            st.rerun(scope="app")
                        else:
                            st.error(translate("Error updating the entry."))
                    except ValueError as ve:
                        st.error(translate("Validation error: {error}", error=ve))
    
        @st.fragment
        def render_food_delete_panel():
            current_entries = DailyLog.get_food_entries(daily_log.id, user_id)
            if current_entries.empty:
                return
    
            with st.container(border=True):
                st.markdown(f"#### 🗑️ {translate('Delete an entry')}")
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
                    translate("Entry"),
                    options=food_log_ids,
                    format_func=lambda log_entry_id: format_food_log_option(current_entries, log_entry_id),
                    index=delete_select_index,
                    key=translated_selection_key(delete_select_key)
                )
                st.session_state["food_log_delete_selected_id"] = int(selected_food_log_id)
                confirm_food_delete = st.checkbox(
                    translate("I confirm deletion of this entry"),
                    key=delete_confirm_key
                )
    
                if st.button(
                    translate("Delete entry"),
                    width="stretch",
                    key="btn_delete_food_log",
                    type="tertiary",
                ):
                    if not confirm_food_delete:
                        st.warning(
                            translate("Check the confirmation box before deleting.")
                        )
                    elif FoodLog.delete(int(selected_food_log_id), user_id):
                        daily_log.recalculate_totals()
                        DailyLog.delete_if_empty(daily_log.id, user_id)
                        if st.session_state.get("food_log_edit_selected_id") == int(selected_food_log_id):
                            del st.session_state["food_log_edit_selected_id"]
                        if st.session_state.get("food_log_delete_selected_id") == int(selected_food_log_id):
                            del st.session_state["food_log_delete_selected_id"]
                        st.session_state["food_log_msg"] = (
                            "success",
                            translate("The entry was deleted successfully."),
                        )
                        st.session_state["food_log_reset_edit_delete_widgets"] = True
                        st.rerun(scope="app")
                    else:
                        st.error(translate("Error deleting the entry."))
    
        render_food_edit_panel()
        render_food_delete_panel()
    else:
        st.info(
            translate(
                "There are no food entries for this day. Add the first food using the form above."
            )
        )
