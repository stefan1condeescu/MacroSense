import html
import os
import re
import streamlit as st
from models.tracking import Activity, FoodItem
from models.text_validation import contains_letter, has_obvious_html_chars
from services.usda_food_data import USDAFoodDataClient
from ui.activity_selection import format_activity_category_for_display
from ui.catalog_constants import ACTIVITY_CATEGORIES, FOOD_CATEGORIES, USDA_DATA_TYPES
from ui.food_selection import format_food_category_for_display
from ui.language import translate, translated_selection_key
from ui.tables import render_activity_catalog_table, render_food_catalog_table


CATEGORY_KEYWORDS = [
    ("Alcoolice", ["beer", "wine", "vodka", "whiskey", "alcohol", "liqueur"]),
    ("Dulciuri", ["ice cream", "cake", "cookie", "chocolate", "candy", "dessert", "pie", "sweet"]),
    ("Mezeluri", ["sausage", "salami", "ham", "bacon", "pepperoni", "deli", "prosciutto"]),
    ("Pește", ["fish", "salmon", "tuna", "cod", "shrimp", "seafood", "sardine", "trout"]),
    ("Carne", ["chicken", "beef", "pork", "turkey", "meat", "veal", "lamb", "duck"]),
    ("Ouă", ["egg", "eggs", "omelet"]),
    ("Băuturi & Sucuri", ["juice", "soda", "beverage", "drink", "coffee", "tea", "smoothie"]),
    ("Pâine & Panificație", ["bread", "bun", "roll", "bagel", "toast", "bakery"]),
    ("Paste & Orez", ["pasta", "spaghetti", "macaroni", "noodle", "rice"]),
    ("Leguminoase", ["bean", "beans", "lentil", "chickpea", "pea", "peas"]),
    ("Nuci & Semințe", ["almond", "walnut", "peanut", "seed", "cashew", "pistachio", "hazelnut"]),
    ("Uleiuri & Grăsimi", ["oil", "lard", "margarine", "butter", "fat", "shortening"]),
    ("Gustări", ["chips", "crackers", "snack", "popcorn", "pretzel"]),
    ("Lactate", ["milk", "cheese", "yogurt", "yoghurt", "cream", "dairy"]),
    ("Cereale", ["oats", "oatmeal", "cereal", "wheat", "corn", "barley", "rye"]),
    ("Fructe", ["apple", "banana", "orange", "strawberry", "berries", "fruit", "pear", "grape"]),
    ("Legume", ["tomato", "potato", "carrot", "broccoli", "vegetable", "lettuce", "spinach", "pepper", "eggplant", "aubergine"]),
    ("Condimente & Sosuri", ["sauce", "ketchup", "mustard", "spice", "salt", "pepper", "dressing"]),
]


def get_usda_api_key() -> str | None:
    """Returns the USDA API key from Streamlit secrets or environment variables."""
    try:
        secret_key = st.secrets.get("FDC_API_KEY")
    except Exception:
        secret_key = None

    return secret_key or os.environ.get("FDC_API_KEY")


def format_usda_result(food: dict) -> str:
    return (
        f"{food['description']} "
        f"({food['data_type']}, {food['calories']:.1f} kcal/100g, FDC {food['fdc_id']})"
    )


def build_usda_preview_metric_html(label: str, value: str) -> str:
    """Builds a compact metric block for the USDA import preview."""
    return (
        '<div class="usda-preview-metric">'
        f'<span>{html.escape(str(label), quote=True)}</span>'
        f'<strong>{html.escape(str(value), quote=True)}</strong>'
        "</div>"
    )


def description_has_keyword(description: str, keyword: str) -> bool:
    """Checks category keywords without matching partial words such as egg in eggplant."""
    if " " in keyword:
        return keyword in description
    return re.search(rf"\b{re.escape(keyword)}\b", description) is not None


def suggest_food_category(description: str) -> str:
    """Suggests a local MacroSense food category from an USDA description."""
    normalized_description = (description or "").lower()
    for category, keywords in CATEGORY_KEYWORDS:
        if any(description_has_keyword(normalized_description, keyword) for keyword in keywords):
            return category
    return "Altele"


def validate_food_item_input(name: str, calories: float, protein: float, carbs: float, fats: float) -> list[str]:
    """Validates manual food catalog input before saving from the Admin UI."""
    errors = []
    if not name or not name.strip():
        errors.append(translate("Food name is required."))
    elif has_obvious_html_chars(name):
        errors.append(translate("Food name cannot contain HTML-like characters."))
    elif not contains_letter(name):
        errors.append(translate("Food name must contain at least one letter."))

    nutrition_values = [float(calories or 0), float(protein or 0), float(carbs or 0), float(fats or 0)]
    if any(value < 0 for value in nutrition_values):
        errors.append(translate("Nutritional values cannot be negative."))
    if float(calories or 0) <= 0:
        errors.append(translate("Calories must be greater than 0."))
    if all(value == 0 for value in [float(protein or 0), float(carbs or 0), float(fats or 0)]):
        errors.append(translate("Enter at least one macronutrient greater than 0."))

    return errors


def validate_activity_input(name: str, met: float, category: str, check_duplicate: bool = False) -> list[str]:
    """Validates manual activity catalog input before saving from the Admin UI."""
    errors = []
    if not name or not name.strip():
        errors.append(translate("Activity name is required."))
    elif has_obvious_html_chars(name):
        errors.append(translate("Activity name cannot contain HTML-like characters."))
    elif not contains_letter(name):
        errors.append(translate("Activity name must contain at least one letter."))
    elif check_duplicate and Activity.name_exists_normalized(name):
        errors.append(translate("An activity with this name already exists."))
    if float(met or 0) < Activity.MIN_MET_MULTIPLIER:
        errors.append(
            translate(
                "The MET coefficient must be at least {minimum:.1f}.",
                minimum=Activity.MIN_MET_MULTIPLIER,
            )
        )
    if not category or not category.strip():
        errors.append(translate("Activity category is required."))

    return errors


def show_first_validation_error(errors: list[str]) -> None:
    """Displays only the first validation error to keep Admin forms readable."""
    if errors:
        st.error(errors[0])


def show_admin_food_catalog_toasts() -> None:
    message = st.session_state.pop("admin_food_catalog_toast", None)
    if message:
        st.toast(message, icon="✅")


def show_admin_activity_catalog_toasts() -> None:
    message = st.session_state.pop("admin_activity_catalog_toast", None)
    if message:
        st.toast(message, icon="✅")


def render_usda_food_import_panel() -> None:
    with st.expander(translate("Import food from USDA"), expanded=False):
        st.caption(
            translate(
                "Search for non-branded foods in FoodData Central and save their per-100g values locally."
            )
        )
        st.caption(
            translate(
                "USDA search works best with English terms, for example "
                '"ice cream", "salmon", or "orange juice".'
            )
        )

        api_key = get_usda_api_key()
        if not api_key:
            st.warning(
                translate(
                    "Configure `FDC_API_KEY` in Streamlit secrets or environment variables to use USDA import."
                )
            )
            return

        query = st.text_input(
            translate("Search for USDA food (in English)"),
            placeholder=translate("E.g. banana, chicken breast, oats"),
            key="usda_food_query"
        )
        data_types = st.multiselect(
            translate("USDA sources"),
            options=USDA_DATA_TYPES,
            default=["SR Legacy", "Foundation"],
            key="usda_food_data_types",
            help=translate(
                "Branded is not included in this version to avoid commercial duplicates."
            ),
        )

        cleaned_query = query.strip()
        selected_data_types = tuple(data_types)

        if st.button(
            translate("Search USDA"),
            width="stretch",
            key="btn_search_usda_food",
            type="primary",
        ):
            if not cleaned_query:
                st.warning(translate("Enter a search term."))
            elif not data_types:
                st.warning(translate("Select at least one USDA source."))
            else:
                try:
                    client = USDAFoodDataClient(api_key)
                    results = client.search_foods(cleaned_query, data_types)
                    st.session_state["usda_food_results"] = results
                    st.session_state["usda_food_results_context"] = {
                        "query": cleaned_query,
                        "data_types": selected_data_types,
                    }
                    if results:
                        st.success(
                            translate(
                                "Found {count} relevant importable results.",
                                count=len(results),
                            )
                        )
                    else:
                        st.warning(
                            translate(
                                "No results with complete calorie and macronutrient values were found."
                            )
                        )
                except Exception as e:
                    st.error(translate("USDA query error: {error}", error=e))

        results = st.session_state.get("usda_food_results", [])
        if not results:
            return

        results_context = st.session_state.get("usda_food_results_context", {})
        current_context = {
            "query": cleaned_query,
            "data_types": selected_data_types,
        }
        if results_context != current_context:
            st.info(
                translate(
                    'The search criteria changed. Select "Search USDA" again to refresh the results.'
                )
            )
            return

        result_by_id = {food["fdc_id"]: food for food in results}
        selected_fdc_id = st.radio(
            translate("USDA result"),
            options=list(result_by_id.keys()),
            format_func=lambda fdc_id: format_usda_result(result_by_id[fdc_id]),
            key="usda_food_result_radio"
        )
        selected_food = result_by_id[selected_fdc_id]

        with st.container(border=True):
            st.markdown(f"#### {translate('Review the food before importing')}")
            col_cal, col_protein, col_carbs, col_fats = st.columns(4)
            col_cal.markdown(
                build_usda_preview_metric_html(
                    translate("Calories"),
                    f"{selected_food['calories']:.1f} kcal",
                ),
                unsafe_allow_html=True,
            )
            col_protein.markdown(
                build_usda_preview_metric_html(
                    translate("Protein"),
                    f"{selected_food['protein_g']:.1f} g",
                ),
                unsafe_allow_html=True,
            )
            col_carbs.markdown(
                build_usda_preview_metric_html(
                    translate("Carbohydrates"),
                    f"{selected_food['carbs_g']:.1f} g",
                ),
                unsafe_allow_html=True,
            )
            col_fats.markdown(
                build_usda_preview_metric_html(
                    translate("Fats"),
                    f"{selected_food['fats_g']:.1f} g",
                ),
                unsafe_allow_html=True,
            )
            st.link_button(
                translate("Open source in FoodData Central"),
                selected_food["source_url"],
                width="stretch"
            )

            imported_name = st.text_input(
                translate("Name in the application"),
                value=selected_food["description"].capitalize(),
                key=f"usda_food_import_name_{selected_fdc_id}"
            )
            suggested_category = suggest_food_category(selected_food["description"])
            st.caption(
                translate(
                    "Suggested category: {category}",
                    category=format_food_category_for_display(suggested_category),
                )
            )
            imported_category = st.pills(
                translate("Category"),
                FOOD_CATEGORIES,
                default=suggested_category,
                selection_mode="single",
                required=True,
                format_func=format_food_category_for_display,
                key=translated_selection_key(f"usda_food_import_category_{selected_fdc_id}")
            )

            already_imported = FoodItem.external_reference_exists("USDA", selected_food["fdc_id"])
            if already_imported:
                st.info(translate("This USDA food is already imported into the catalog."))

            if st.button(
                translate("Import food"),
                width="stretch",
                key=f"btn_import_usda_food_{selected_fdc_id}",
                type="primary",
                disabled=already_imported
            ):
                validation_errors = validate_food_item_input(
                    imported_name,
                    selected_food["calories"],
                    selected_food["protein_g"],
                    selected_food["carbs_g"],
                    selected_food["fats_g"]
                )
                if validation_errors:
                    show_first_validation_error(validation_errors)
                    return

                try:
                    imported_food = FoodItem(
                        name=imported_name.strip(),
                        calories_100g=selected_food["calories"],
                        protein_g=selected_food["protein_g"],
                        carbs_g=selected_food["carbs_g"],
                        fats_g=selected_food["fats_g"],
                        category=imported_category or "Altele",
                        source="USDA",
                        source_type=selected_food["data_type"],
                        external_id=selected_food["fdc_id"],
                        source_url=selected_food["source_url"]
                    )
                except ValueError:
                    st.error(
                        translate("The imported food does not satisfy the validation rules.")
                    )
                    return

                if imported_food.save():
                    st.session_state["admin_food_catalog_toast"] = (
                        translate(
                            'Food "{name}" was imported.',
                            name=imported_name.strip(),
                        )
                    )
                    st.session_state["usda_food_results"] = []
                    st.session_state.pop("usda_food_results_context", None)
                    st.rerun()
                else:
                    st.error(
                        translate(
                            "Import failed. Check whether the food already exists in the catalog."
                        )
                    )


def render_admin_food_catalog_page() -> None:
    st.header(f"🍎 {translate('Food catalog management')}")
    show_admin_food_catalog_toasts()

    if st.session_state.pop("admin_food_form_reset", False):
        for key in (
            "admin_food_name",
            "admin_food_category",
            "admin_food_calories",
            "admin_food_protein",
            "admin_food_carbs",
            "admin_food_fats",
        ):
            st.session_state.pop(key, None)

    with st.expander(f"➕ {translate('Add a new food')}", expanded=True):
        with st.container(border=True, key="add_food_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(translate("Food name"), key="admin_food_name")
                category = st.selectbox(
                    translate("Category"),
                    FOOD_CATEGORIES,
                    format_func=format_food_category_for_display,
                    key=translated_selection_key("admin_food_category"),
                )
                calories = st.number_input(
                    translate("Calories (per 100g)"),
                    step=1.0,
                    key="admin_food_calories",
                )
            with col2:
                protein = st.number_input(
                    translate("Protein (g)"),
                    step=0.1,
                    key="admin_food_protein",
                )
                carbs = st.number_input(
                    translate("Carbohydrates (g)"),
                    step=0.1,
                    key="admin_food_carbs",
                )
                fats = st.number_input(
                    translate("Fats (g)"),
                    step=0.1,
                    key="admin_food_fats",
                )

            submit_food = st.button(
                translate("Save food"), type="primary", key="admin_food_submit"
            )

            if submit_food:
                validation_errors = validate_food_item_input(name, calories, protein, carbs, fats)
                if validation_errors:
                    show_first_validation_error(validation_errors)
                else:
                    try:
                        new_food = FoodItem(name.strip(), calories, protein, carbs, fats, category)
                        if new_food.save():
                            st.session_state["admin_food_catalog_toast"] = (
                                translate(
                                    'Food "{name}" was added successfully!',
                                    name=name.strip(),
                                )
                            )
                            st.session_state["admin_food_form_reset"] = True
                            st.rerun()
                        else:
                            st.error(translate("Could not add the food."))
                    except ValueError:
                        st.error(translate("The food does not satisfy the validation rules."))

    render_usda_food_import_panel()

    st.subheader(translate("Nutrition database"))
    df_foods = FoodItem.get_all_as_dataframe()
    if not df_foods.empty:
        render_food_catalog_table(df_foods, key_prefix="admin")
    else:
        st.info(translate("The catalog is empty."))


def render_admin_activity_catalog_page() -> None:
    st.header(f"🏃‍♂️ {translate('Activity catalog management')}")
    show_admin_activity_catalog_toasts()

    if st.session_state.pop("admin_activity_form_reset", False):
        for key in (
            "admin_activity_name",
            "admin_activity_category",
            "admin_activity_met",
        ):
            st.session_state.pop(key, None)

    with st.expander(f"➕ {translate('Add a new activity')}", expanded=True):
        with st.container(border=True, key="add_activity_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(translate("Activity name"), key="admin_activity_name")
                category = st.selectbox(
                    translate("Category"),
                    ACTIVITY_CATEGORIES,
                    format_func=format_activity_category_for_display,
                    key=translated_selection_key("admin_activity_category"),
                )
            with col2:
                met = st.number_input(
                    translate("MET coefficient"),
                    value=1.0,
                    step=0.1,
                    key="admin_activity_met",
                    help=translate(
                        "The minimum accepted value is {minimum:.1f}. E.g. Running = 8.0",
                        minimum=Activity.MIN_MET_MULTIPLIER,
                    ),
                )

            submit_act = st.button(
                translate("Save activity"), type="primary", key="admin_activity_submit"
            )

            if submit_act:
                validation_errors = validate_activity_input(name, met, category, check_duplicate=True)
                if validation_errors:
                    show_first_validation_error(validation_errors)
                else:
                    try:
                        new_activity = Activity(name.strip(), met, category)
                        if new_activity.save():
                            st.session_state["admin_activity_catalog_toast"] = (
                                translate(
                                    'Activity "{name}" was added successfully!',
                                    name=name.strip(),
                                )
                            )
                            st.session_state["admin_activity_form_reset"] = True
                            st.rerun()
                        else:
                            st.error(translate("Could not add the activity."))
                    except ValueError:
                        st.error(
                            translate(
                                "The activity does not satisfy the validation rules."
                            )
                        )

    st.subheader(translate("Available activities"))
    df_activities = Activity.get_all_as_dataframe()
    if not df_activities.empty:
        render_activity_catalog_table(df_activities, key_prefix="admin")
    else:
        st.info(translate("The activity catalog is empty."))
