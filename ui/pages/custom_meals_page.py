import html
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import streamlit as st
from models.tracking import CustomMeal, FoodItem
from ui.food_selection import (
    build_food_selection_dataframe,
    build_food_selection_display_dataframe,
    build_food_selection_state_key,
    format_food_category_for_display,
    get_food_category_filter_options,
)
from ui.language import translate, translated_selection_key
from ui.quantity_validation import quantity_range_help_for_ui, validate_quantity_g_for_ui
from ui.tables import get_table_height


DISPLAY_DECIMAL_PLACES = 1
CUSTOM_MEAL_STATUS_SOURCE_TEXT = {
    CustomMeal.ACTIVE_STATUS: "Saved",
    CustomMeal.ARCHIVED_STATUS: "Archived",
}


def escape_html_text(value) -> str:
    """Escapes user-controlled text before inserting it into custom HTML blocks."""
    return html.escape(str(value))


def format_display_number(value: float, decimal_places: int) -> str:
    quantum = Decimal("1") if decimal_places == 0 else Decimal("1").scaleb(-decimal_places)
    rounded_value = Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)
    return format(rounded_value, f".{decimal_places}f")


def round_display_number(value: float, decimal_places: int = DISPLAY_DECIMAL_PLACES) -> float:
    return float(format_display_number(value, decimal_places))


def format_custom_meal_status(value) -> str:
    """Return a translated label without changing the stored status value."""
    source_text = CUSTOM_MEAL_STATUS_SOURCE_TEXT.get(value)
    if source_text is None:
        return str(value)
    return translate(source_text)


def build_custom_meal_display_rows_and_totals(ingredients: list[dict]) -> tuple[list[list], dict[str, float]]:
    rows = []
    totals = {
        "quantity_g": 0.0,
        "calories": 0.0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fats_g": 0.0,
    }

    for ingredient in ingredients:
        quantity_g = round_display_number(ingredient["quantity_g"])
        calories = round_display_number(ingredient["calories_100g"] * ingredient["quantity_g"] / 100.0)
        protein = round_display_number(ingredient["protein_g"] * ingredient["quantity_g"] / 100.0)
        carbs = round_display_number(ingredient["carbs_g"] * ingredient["quantity_g"] / 100.0)
        fats = round_display_number(ingredient["fats_g"] * ingredient["quantity_g"] / 100.0)

        totals["quantity_g"] += quantity_g
        totals["calories"] += calories
        totals["protein_g"] += protein
        totals["carbs_g"] += carbs
        totals["fats_g"] += fats

        rows.append([
            ingredient["name"],
            ingredient.get("source_label", "MacroSense"),
            quantity_g,
            calories,
            protein,
            carbs,
            fats,
        ])

    return rows, totals


def build_custom_meal_summary_cards_html(
    total_quantity: float,
    total_calories: float,
    total_protein: float,
    total_carbs: float,
    total_fats: float,
) -> str:
    cards = [
        (translate("Total quantity"), f"{format_display_number(total_quantity, 0)} g"),
        (translate("Total calories"), f"{format_display_number(total_calories, 0)} kcal"),
        (translate("Protein"), f"{format_display_number(total_protein, 1)} g"),
        (translate("Carbohydrates"), f"{format_display_number(total_carbs, 1)} g"),
        (translate("Fats"), f"{format_display_number(total_fats, 1)} g"),
    ]
    cards_html = "".join(
        (
            '<div class="custom-meal-summary-card">'
            f"<span>{escape_html_text(label)}</span>"
            f"<strong>{escape_html_text(value)}</strong>"
            "</div>"
        )
        for label, value in cards
    )
    return f'<div class="custom-meal-summary-grid">{cards_html}</div>'


def get_edit_quantity_widget_keys_to_reset(session_keys, meal_id) -> list[str]:
    """Returns edit quantity widget keys that can be reset without rebuilding picker tables."""
    quantity_prefix = f"custom_meal_edit_qty_{int(meal_id)}_"
    add_quantity_key = f"custom_meal_edit_add_quantity_{int(meal_id)}"
    return [
        key for key in session_keys
        if key.startswith(quantity_prefix) or key == add_quantity_key
    ]


def render_custom_meals_page() -> None:
    st.header(f"🥗 {translate('Custom meals')}")
    
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.error(translate("Invalid session. Please log in again."))
        st.stop()
    
    if "custom_meal_ingredients" not in st.session_state:
        st.session_state["custom_meal_ingredients"] = []
    if "custom_meal_edit_ingredients" not in st.session_state:
        st.session_state["custom_meal_edit_ingredients"] = []
    if "custom_meal_edit_row_counter" not in st.session_state:
        st.session_state["custom_meal_edit_row_counter"] = 0
    if "custom_meal_widget_version" not in st.session_state:
        st.session_state["custom_meal_widget_version"] = 0
    if "custom_meal_name_widget_version" not in st.session_state:
        st.session_state["custom_meal_name_widget_version"] = 0
    
    custom_meal_message = st.session_state.pop("custom_meal_msg", None)
    reset_edit_quantity_meal_id = st.session_state.pop(
        "custom_meal_reset_edit_quantity_widgets",
        None
    )
    if reset_edit_quantity_meal_id is not None:
        for key in get_edit_quantity_widget_keys_to_reset(
            list(st.session_state.keys()),
            reset_edit_quantity_meal_id
        ):
            del st.session_state[key]

    if st.session_state.pop("custom_meal_reset_widgets", False):
        st.session_state["custom_meal_widget_version"] += 1
        st.session_state["custom_meal_name_widget_version"] += 1
        custom_meal_widget_keys = [
            key for key in st.session_state.keys()
            if key.startswith((
                "custom_meal_details_select_",
                "custom_meal_edit_select_",
                "custom_meal_edit_name_",
                "custom_meal_edit_qty_",
                "custom_meal_edit_add_food_",
                "custom_meal_edit_add_quantity_",
                "custom_meal_ingredient_search_",
                "custom_meal_ingredient_category_",
                "custom_meal_ingredient_table_",
                "custom_meal_edit_ingredient_search_",
                "custom_meal_edit_ingredient_category_",
                "custom_meal_edit_ingredient_table_",
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
        "Ingredient": st.column_config.TextColumn(translate("Ingredient"), width="medium"),
        "Sursă": st.column_config.TextColumn(translate("Source"), width="small"),
        "Cantitate (g)": st.column_config.NumberColumn(translate("Quantity"), format="%.1f g", width="small"),
        "Calorii": st.column_config.NumberColumn(translate("Calories"), format="%.1f kcal", width="small"),
        "Proteine (g)": st.column_config.NumberColumn(translate("Protein"), format="%.1f g", width="small"),
        "Carbohidrați (g)": st.column_config.NumberColumn(translate("Carbohydrates"), format="%.1f g", width="small"),
        "Grăsimi (g)": st.column_config.NumberColumn(translate("Fats"), format="%.1f g", width="small"),
    }

    food_selection_table_config = {
        "Denumire": st.column_config.TextColumn(translate("Name"), width="medium"),
        "Categorie": st.column_config.TextColumn(translate("Category"), width="small"),
        "Sursă": st.column_config.TextColumn(translate("Source"), width="small"),
        "Kcal/100g": st.column_config.NumberColumn("Kcal/100g", format="%.1f kcal", width="small"),
        "Proteine": st.column_config.NumberColumn(translate("Protein"), format="%.1f g", width="small"),
        "Carbohidrați": st.column_config.NumberColumn(translate("Carbohydrates"), format="%.1f g", width="small"),
        "Grăsimi": st.column_config.NumberColumn(translate("Fats"), format="%.1f g", width="small"),
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

    def render_food_picker(search_key: str, category_key: str, table_key_prefix: str, caption: str):
        filter_col, category_col = st.columns([2, 1])
        with filter_col:
            search_text = st.text_input(
                translate("Search for ingredient"),
                placeholder=translate("E.g. bananas, broccoli, strawberries"),
                key=search_key
            )
        with category_col:
            category_filter = st.selectbox(
                translate("Category"),
                get_food_category_filter_options(food_options),
                format_func=format_food_category_for_display,
                key=translated_selection_key(category_key)
            )

        food_selection_df = build_food_selection_dataframe(
            food_options,
            search_text,
            category_filter
        )
        if food_selection_df.empty:
            st.info(translate("No ingredients match the selected search and category."))
            return None

        st.caption(caption)
        food_selection_display_df = build_food_selection_display_dataframe(
            food_selection_df
        )
        food_selection_state = st.dataframe(
            food_selection_display_df,
            width="stretch",
            height=get_table_height(food_selection_df, max_rows=6),
            hide_index=True,
            column_order=["Denumire", "Categorie", "Sursă", "Kcal/100g", "Proteine", "Carbohidrați", "Grăsimi"],
            column_config=food_selection_table_config,
            key=build_food_selection_state_key(search_text, category_filter, table_key_prefix),
            on_select="rerun",
            selection_mode="single-row",
            row_height=32
        )
        selected_rows = food_selection_state.selection.rows
        if selected_rows and selected_rows[0] < len(food_selection_df):
            return int(food_selection_df.iloc[selected_rows[0]]["_food_id"])
        return None
    
    def render_custom_meal_cards(meal_options):
        for meal in meal_options.values():
            is_archived = meal["status"] == CustomMeal.ARCHIVED_STATUS
            card_class = "custom-meal-card archived" if is_archived else "custom-meal-card active"
            status_class = "status-badge archived" if is_archived else "status-badge active"
            safe_recipe_name = escape_html_text(meal["recipe_name"])
            safe_status = escape_html_text(format_custom_meal_status(meal["status"]))
            display_ingredients = CustomMeal.get_ingredients(meal["id"], user_id)
            if display_ingredients:
                _, display_totals = build_custom_meal_display_rows_and_totals(display_ingredients)
            else:
                display_totals = {
                    "quantity_g": meal["quantity_g"],
                    "calories": meal["calories"],
                    "protein_g": meal["protein_g"],
                    "carbs_g": meal["carbs_g"],
                    "fats_g": meal["fats_g"],
                }
            quantity_label = escape_html_text(translate("Quantity"))
            calories_label = escape_html_text(translate("Calories"))
            protein_label = escape_html_text(translate("Protein"))
            carbohydrates_label = escape_html_text(translate("Carbohydrates"))
            fats_label = escape_html_text(translate("Fats"))
            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="custom-meal-card-header">
                        <strong>{safe_recipe_name}</strong>
                        <span class="{status_class}">{safe_status}</span>
                    </div>
                    <div class="custom-meal-card-grid">
                        <div><span>{quantity_label}</span><strong>{format_display_number(display_totals['quantity_g'], 0)} g</strong></div>
                        <div><span>{calories_label}</span><strong>{format_display_number(display_totals['calories'], 0)} kcal</strong></div>
                        <div><span>{protein_label}</span><strong>{format_display_number(display_totals['protein_g'], 1)} g</strong></div>
                        <div><span>{carbohydrates_label}</span><strong>{format_display_number(display_totals['carbs_g'], 1)} g</strong></div>
                        <div><span>{fats_label}</span><strong>{format_display_number(display_totals['fats_g'], 1)} g</strong></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    st.subheader(f"➕ {translate('Create a custom meal')}")
    recipe_name = st.text_input(translate("Meal name"), key="custom_meal_name")
    
    if not food_options:
        st.warning(
            translate(
                "The food catalog is empty. The administrator must add foods first."
            )
        )
    else:
        custom_meal_widget_version = st.session_state["custom_meal_widget_version"]
        selected_ingredient_id = render_food_picker(
            search_key=f"custom_meal_ingredient_search_{custom_meal_widget_version}",
            category_key=f"custom_meal_ingredient_category_{custom_meal_widget_version}",
            table_key_prefix=f"custom_meal_ingredient_table_{custom_meal_widget_version}",
            caption=translate(
                "Select the ingredient from the table. The Source column helps distinguish duplicate foods."
            )
        )
        ingredient_quantity = st.number_input(
            translate("Ingredient quantity (g)"),
            value=100.0,
            step=1.0,
            key="custom_meal_ingredient_quantity",
            help=quantity_range_help_for_ui()
        )
    
        selected_ingredient = food_options.get(selected_ingredient_id) if selected_ingredient_id else None
        ingredient_quantity_error = validate_quantity_g_for_ui(
            ingredient_quantity,
            "Ingredient quantity",
        )
        if selected_ingredient:
            if ingredient_quantity_error:
                st.error(ingredient_quantity_error)
            else:
                ingredient_calories = round(selected_ingredient["calories_100g"] * float(ingredient_quantity) / 100.0, 2)
                st.caption(
                    translate(
                        "🔥 Selected ingredient: **{name}** ({source}) · Estimated calories: **{calories} kcal**",
                        name=selected_ingredient["name"],
                        source=selected_ingredient.get("source_label", "MacroSense"),
                        calories=ingredient_calories,
                    )
                )
        else:
            st.caption(
                translate("Select an ingredient to calculate the calorie estimate.")
            )
    
        col_add, col_clear = st.columns(2)
        with col_add:
            if st.button(
                translate("Add ingredient"),
                width="stretch",
                key="btn_add_custom_meal_ingredient",
                type="primary",
                disabled=selected_ingredient is None or bool(ingredient_quantity_error)
            ):
                st.session_state["custom_meal_ingredients"].append({
                    "food_id": selected_ingredient["id"],
                    "name": selected_ingredient["name"],
                    "source_label": selected_ingredient.get("source_label", "MacroSense"),
                    "quantity_g": float(ingredient_quantity),
                    "calories_100g": selected_ingredient["calories_100g"],
                    "protein_g": selected_ingredient["protein_g"],
                    "carbs_g": selected_ingredient["carbs_g"],
                    "fats_g": selected_ingredient["fats_g"],
                })
                st.rerun()
        with col_clear:
            if st.button(
                translate("Clear list"),
                width="stretch",
                key="btn_clear_custom_meal_ingredients",
                type="tertiary",
            ):
                st.session_state["custom_meal_ingredients"] = []
                st.rerun()
    
    pending_ingredients = st.session_state["custom_meal_ingredients"]
    if pending_ingredients:
        rows, display_totals = build_custom_meal_display_rows_and_totals(pending_ingredients)
    
        df_pending = pd.DataFrame(
            rows,
            columns=["Ingredient", "Sursă", "Cantitate (g)", "Calorii", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)"]
        )
        render_ingredient_table(df_pending)
        st.markdown(
            build_custom_meal_summary_cards_html(
                display_totals["quantity_g"],
                display_totals["calories"],
                display_totals["protein_g"],
                display_totals["carbs_g"],
                display_totals["fats_g"],
            ),
            unsafe_allow_html=True,
        )
    
        if st.button(
            translate("Save custom meal"),
            width="stretch",
            key="btn_save_custom_meal",
            type="primary",
        ):
            if not recipe_name.strip():
                st.warning(translate("Enter a name for the custom meal."))
            elif not CustomMeal.is_valid_recipe_name(recipe_name):
                st.warning(
                    translate(
                        "The custom meal name must start with a letter and cannot contain HTML characters."
                    )
                )
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
                    st.session_state["custom_meal_msg"] = (
                        "success",
                        translate(
                            'Custom meal "{name}" was saved.',
                            name=saved_meal.recipe_name,
                        ),
                    )
                    st.session_state["custom_meal_reset_widgets"] = True
                    st.rerun()
                else:
                    st.error(translate("Error saving the custom meal."))
    else:
        st.info(
            translate("Add at least one ingredient to save a custom meal.")
        )
    
    st.divider()
    st.subheader(f"📋 {translate('Your custom meals')}")
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
        custom_meal_name_widget_version = st.session_state["custom_meal_name_widget_version"]
    
        with st.container(border=True):
            st.markdown(f"#### {translate('Custom meal archive')}")
            archive_col, restore_col = st.columns(2)
    
            with archive_col:
                st.caption(
                    translate("Remove an active meal from future use.")
                )
                if active_meal_options:
                    active_meal_ids = list(active_meal_options.keys())
                    selected_archive_meal_id = st.selectbox(
                        translate("Active meal"),
                        options=active_meal_ids,
                        format_func=lambda meal_id: active_meal_options[meal_id]["recipe_name"],
                        key=f"custom_meal_archive_select_{custom_meal_name_widget_version}"
                    )
                    if st.button(
                        translate("Archive meal"),
                        width="stretch",
                        key="btn_archive_custom_meal",
                        type="tertiary",
                    ):
                        if CustomMeal.archive(selected_archive_meal_id, user_id):
                            st.session_state["custom_meal_msg"] = (
                                "success",
                                translate(
                                    'Meal "{name}" was archived.',
                                    name=active_meal_options[selected_archive_meal_id]["recipe_name"],
                                ),
                            )
                            st.session_state["custom_meal_reset_widgets"] = True
                            st.rerun()
                        else:
                            st.error(translate("Error archiving the custom meal."))
                else:
                    st.info(translate("You have no active meals to archive."))
    
            with restore_col:
                st.caption(
                    translate("Restore an archived meal to the Food journal.")
                )
                if archived_meal_options:
                    archived_meal_ids = list(archived_meal_options.keys())
                    selected_restore_meal_id = st.selectbox(
                        translate("Archived meal"),
                        options=archived_meal_ids,
                        format_func=lambda meal_id: archived_meal_options[meal_id]["recipe_name"],
                        key=f"custom_meal_restore_select_{custom_meal_name_widget_version}"
                    )
                    if st.button(
                        translate("Restore meal"),
                        width="stretch",
                        key="btn_restore_custom_meal",
                        type="primary",
                    ):
                        if CustomMeal.restore(selected_restore_meal_id, user_id):
                            st.session_state["custom_meal_msg"] = (
                                "success",
                                translate(
                                    'Meal "{name}" was restored.',
                                    name=archived_meal_options[selected_restore_meal_id]["recipe_name"],
                                ),
                            )
                            st.session_state["custom_meal_reset_widgets"] = True
                            st.rerun()
                        else:
                            st.error(translate("Error restoring the custom meal."))
                else:
                    st.info(translate("You have no archived meals."))
    
        details_select_key = f"custom_meal_details_select_{custom_meal_name_widget_version}"
        saved_details_meal_id = st.session_state.get("custom_meal_details_selected_id")
        if saved_details_meal_id not in custom_meal_ids:
            st.session_state.pop("custom_meal_details_selected_id", None)
            saved_details_meal_id = None
        details_select_index = custom_meal_ids.index(saved_details_meal_id) if saved_details_meal_id in custom_meal_ids else 0
        st.markdown(f"#### {translate('View ingredients for')}")
        selected_saved_meal_id = st.selectbox(
            translate("Choose meal for details"),
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
        st.subheader(f"✏️ {translate('Edit a custom meal')}")
        edit_select_key = f"custom_meal_edit_select_{custom_meal_name_widget_version}"
        saved_edit_meal_id = st.session_state.get("custom_meal_edit_selected_id")
        if saved_edit_meal_id not in custom_meal_ids:
            st.session_state.pop("custom_meal_edit_selected_id", None)
            saved_edit_meal_id = None
        edit_select_index = custom_meal_ids.index(saved_edit_meal_id) if saved_edit_meal_id in custom_meal_ids else 0
        selected_edit_meal_id = st.selectbox(
            translate("Meal to edit"),
            options=custom_meal_ids,
            format_func=lambda meal_id: custom_meal_options[meal_id]["recipe_name"],
            index=edit_select_index,
            key=edit_select_key
        )
        st.session_state["custom_meal_edit_selected_id"] = int(selected_edit_meal_id)
    
        if st.session_state.get("custom_meal_edit_loaded_id") != int(selected_edit_meal_id):
            load_custom_meal_edit_state(selected_edit_meal_id, custom_meal_options)
    
        edit_name_key = f"custom_meal_edit_name_{selected_edit_meal_id}_{custom_meal_name_widget_version}"
        edited_recipe_name = st.text_input(
            translate("New meal name"),
            value=custom_meal_options[selected_edit_meal_id]["recipe_name"],
            key=edit_name_key
        )
        edit_ingredients = st.session_state["custom_meal_edit_ingredients"]
    
        if food_options:
            selected_edit_ingredient_id = render_food_picker(
                search_key=f"custom_meal_edit_ingredient_search_{selected_edit_meal_id}_{custom_meal_widget_version}",
                category_key=f"custom_meal_edit_ingredient_category_{selected_edit_meal_id}_{custom_meal_widget_version}",
                table_key_prefix=f"custom_meal_edit_ingredient_table_{selected_edit_meal_id}_{custom_meal_widget_version}",
                caption=translate(
                    "Select the ingredient to add. For large lists, search by name or filter the category."
                )
            )
            edit_ingredient_quantity = st.number_input(
                translate("New ingredient quantity (g)"),
                value=100.0,
                step=1.0,
                key=f"custom_meal_edit_add_quantity_{selected_edit_meal_id}",
                help=quantity_range_help_for_ui()
            )
            edit_ingredient_quantity_error = validate_quantity_g_for_ui(
                edit_ingredient_quantity,
                "New ingredient quantity",
            )
            if selected_edit_ingredient_id is not None and edit_ingredient_quantity_error:
                st.error(edit_ingredient_quantity_error)

            if st.button(
                translate("Add ingredient to recipe"),
                width="stretch",
                key="btn_add_custom_meal_edit_ingredient",
                type="primary",
                disabled=selected_edit_ingredient_id is None or bool(edit_ingredient_quantity_error)
            ):
                selected_edit_ingredient = food_options[selected_edit_ingredient_id]
                st.session_state["custom_meal_edit_row_counter"] += 1
                edit_ingredients.append({
                    "ingredient_id": None,
                    "row_key": f"new_{st.session_state['custom_meal_edit_row_counter']}",
                    "food_id": selected_edit_ingredient["id"],
                    "name": selected_edit_ingredient["name"],
                    "source_label": selected_edit_ingredient.get("source_label", "MacroSense"),
                    "quantity_g": float(edit_ingredient_quantity),
                    "calories_100g": selected_edit_ingredient["calories_100g"],
                    "protein_g": selected_edit_ingredient["protein_g"],
                    "carbs_g": selected_edit_ingredient["carbs_g"],
                    "fats_g": selected_edit_ingredient["fats_g"],
                })
                st.rerun()
        else:
            st.warning(
                translate(
                    "The food catalog is empty. You cannot add new ingredients right now."
                )
            )

        if edit_ingredients:
            st.caption(translate("Current ingredients"))
            edit_quantity_errors = []
            for ingredient_index, ingredient in enumerate(list(edit_ingredients)):
                row_key = ingredient["row_key"]
                with st.container(border=True):
                    col_name, col_quantity, col_remove = st.columns([2.2, 1, 0.75], vertical_alignment="center")
                    with col_name:
                        st.markdown(f"**{ingredient['name']}**")
                    with col_quantity:
                        updated_quantity = st.number_input(
                            translate("Quantity (g)"),
                            value=float(ingredient["quantity_g"]),
                            step=1.0,
                            key=f"custom_meal_edit_qty_{selected_edit_meal_id}_{row_key}",
                            label_visibility="collapsed",
                            help=quantity_range_help_for_ui()
                        )
                    with col_remove:
                        if st.button(
                            translate("Remove"),
                            key=f"btn_remove_custom_meal_edit_{selected_edit_meal_id}_{row_key}",
                            type="tertiary",
                            width="stretch"
                        ):
                            edit_ingredients.pop(ingredient_index)
                            st.rerun()

                quantity_error = validate_quantity_g_for_ui(
                    updated_quantity,
                    translate("Quantity for {name}", name=ingredient["name"]),
                )
                if quantity_error:
                    edit_quantity_errors.append(quantity_error)
                else:
                    edit_ingredients[ingredient_index]["quantity_g"] = float(updated_quantity)

            if edit_quantity_errors:
                st.error(edit_quantity_errors[0])
            else:
                edit_rows, edit_display_totals = build_custom_meal_display_rows_and_totals(edit_ingredients)

                df_edit = pd.DataFrame(
                    edit_rows,
                    columns=["Ingredient", "Sursă", "Cantitate (g)", "Calorii", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)"]
                )
                render_ingredient_table(df_edit)
                st.markdown(
                    build_custom_meal_summary_cards_html(
                        edit_display_totals["quantity_g"],
                        edit_display_totals["calories"],
                        edit_display_totals["protein_g"],
                        edit_display_totals["carbs_g"],
                        edit_display_totals["fats_g"],
                    ),
                    unsafe_allow_html=True,
                )
        else:
            edit_quantity_errors = []
    
        if st.button(
            translate("Save meal changes"),
            width="stretch",
            key="btn_update_custom_meal",
            type="primary",
            disabled=bool(edit_quantity_errors)
        ):
            if not edited_recipe_name.strip():
                st.warning(translate("Enter a name for the custom meal."))
            elif not CustomMeal.is_valid_recipe_name(edited_recipe_name):
                st.warning(
                    translate(
                        "The custom meal name must start with a letter and cannot contain HTML characters."
                    )
                )
            elif not edit_ingredients:
                st.warning(
                    translate("The custom meal must contain at least one ingredient.")
                )
            else:
                for ingredient in edit_ingredients:
                    quantity_error = validate_quantity_g_for_ui(
                        ingredient["quantity_g"],
                        translate("Quantity for {name}", name=ingredient["name"]),
                    )
                    if quantity_error:
                        st.error(quantity_error)
                        return

                updated_meal = CustomMeal.update_with_ingredients(
                    meal_id=selected_edit_meal_id,
                    user_id=user_id,
                    recipe_name=edited_recipe_name,
                    ingredients=edit_ingredients
                )
                if updated_meal:
                    st.session_state["custom_meal_edit_selected_id"] = int(selected_edit_meal_id)
                    st.session_state["custom_meal_edit_loaded_id"] = None
                    st.session_state["custom_meal_msg"] = (
                        "success",
                        translate(
                            'Custom meal "{name}" was updated. Entries already saved in the journal remain unchanged.',
                            name=edited_recipe_name.strip(),
                        ),
                    )
                    st.session_state["custom_meal_name_widget_version"] += 1
                    st.session_state["custom_meal_reset_edit_quantity_widgets"] = int(selected_edit_meal_id)
                    st.rerun()
                else:
                    st.error(translate("Error updating the custom meal."))
    else:
        st.info(translate("You do not have any saved custom meals yet."))
