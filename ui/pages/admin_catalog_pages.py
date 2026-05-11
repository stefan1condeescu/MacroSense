import os
import re
import streamlit as st
from models.tracking import Activity, FoodItem
from models.text_validation import contains_letter, has_obvious_html_chars
from services.usda_food_data import USDAFoodDataClient
from ui.catalog_constants import ACTIVITY_CATEGORIES, FOOD_CATEGORIES, USDA_DATA_TYPES
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
        errors.append("Denumirea alimentului este obligatorie.")
    elif has_obvious_html_chars(name):
        errors.append("Denumirea alimentului nu poate conține caractere de tip HTML.")
    elif not contains_letter(name):
        errors.append("Denumirea alimentului trebuie să conțină cel puțin o literă.")

    nutrition_values = [float(calories or 0), float(protein or 0), float(carbs or 0), float(fats or 0)]
    if any(value < 0 for value in nutrition_values):
        errors.append("Valorile nutriționale nu pot fi negative.")
    if float(calories or 0) <= 0:
        errors.append("Caloriile trebuie să fie mai mari decât 0.")
    if all(value == 0 for value in [float(protein or 0), float(carbs or 0), float(fats or 0)]):
        errors.append("Completează cel puțin un macronutrient mai mare decât 0.")

    return errors


def validate_activity_input(name: str, met: float, category: str, check_duplicate: bool = False) -> list[str]:
    """Validates manual activity catalog input before saving from the Admin UI."""
    errors = []
    if not name or not name.strip():
        errors.append("Denumirea activității este obligatorie.")
    elif has_obvious_html_chars(name):
        errors.append("Denumirea activității nu poate conține caractere de tip HTML.")
    elif not contains_letter(name):
        errors.append("Denumirea activității trebuie să conțină cel puțin o literă.")
    elif check_duplicate and Activity.name_exists_normalized(name):
        errors.append("Există deja o activitate cu această denumire.")
    if float(met or 0) < Activity.MIN_MET_MULTIPLIER:
        errors.append(f"Coeficientul MET trebuie să fie cel puțin {Activity.MIN_MET_MULTIPLIER:.1f}.")
    if not category or not category.strip():
        errors.append("Categoria activității este obligatorie.")

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
    with st.expander("Importă aliment din USDA", expanded=False):
        st.caption("Caută alimente nebranduite în FoodData Central și salvează local valorile per 100g.")
        st.caption("Căutarea USDA funcționează cel mai bine cu termeni în engleză, de exemplu `ice cream`, `salmon`, `orange juice`.")

        api_key = get_usda_api_key()
        if not api_key:
            st.warning("Configurează cheia `FDC_API_KEY` în Streamlit secrets sau în variabilele de mediu pentru import USDA.")
            return

        query = st.text_input(
            "Caută aliment USDA (în engleză)",
            placeholder="Ex: banana, chicken breast, oats",
            key="usda_food_query"
        )
        data_types = st.multiselect(
            "Surse USDA",
            options=USDA_DATA_TYPES,
            default=["SR Legacy", "Foundation"],
            key="usda_food_data_types",
            help="Branded nu este inclus în această versiune pentru a evita duplicatele comerciale."
        )

        cleaned_query = query.strip()
        selected_data_types = tuple(data_types)

        if st.button("Caută în USDA", width="stretch", key="btn_search_usda_food", type="primary"):
            if not cleaned_query:
                st.warning("Introdu un termen de căutare.")
            elif not data_types:
                st.warning("Selectează cel puțin o sursă USDA.")
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
                        st.success(f"Am găsit {len(results)} rezultate relevante importabile.")
                    else:
                        st.warning("Nu am găsit rezultate cu valori complete pentru calorii și macronutrienți.")
                except Exception as e:
                    st.error(f"Eroare la interogarea USDA: {e}")

        results = st.session_state.get("usda_food_results", [])
        if not results:
            return

        results_context = st.session_state.get("usda_food_results_context", {})
        current_context = {
            "query": cleaned_query,
            "data_types": selected_data_types,
        }
        if results_context != current_context:
            st.info("Ai modificat criteriile de căutare. Apasă din nou „Caută în USDA” pentru rezultate actualizate.")
            return

        result_by_id = {food["fdc_id"]: food for food in results}
        selected_fdc_id = st.radio(
            "Rezultat USDA",
            options=list(result_by_id.keys()),
            format_func=lambda fdc_id: format_usda_result(result_by_id[fdc_id]),
            key="usda_food_result_radio"
        )
        selected_food = result_by_id[selected_fdc_id]

        with st.container(border=True):
            st.markdown("#### Verifică alimentul înainte de import")
            col_cal, col_protein, col_carbs, col_fats = st.columns(4)
            col_cal.metric("Calorii", f"{selected_food['calories']:.1f} kcal")
            col_protein.metric("Proteine", f"{selected_food['protein_g']:.1f} g")
            col_carbs.metric("Carbohidrați", f"{selected_food['carbs_g']:.1f} g")
            col_fats.metric("Grăsimi", f"{selected_food['fats_g']:.1f} g")
            st.link_button(
                "Deschide sursa în FoodData Central",
                selected_food["source_url"],
                width="stretch"
            )

            imported_name = st.text_input(
                "Denumire în aplicație",
                value=selected_food["description"].capitalize(),
                key=f"usda_food_import_name_{selected_fdc_id}"
            )
            suggested_category = suggest_food_category(selected_food["description"])
            st.caption(f"Categorie sugerată: {suggested_category}")
            imported_category = st.pills(
                "Categorie",
                FOOD_CATEGORIES,
                default=suggested_category,
                selection_mode="single",
                required=True,
                key=f"usda_food_import_category_{selected_fdc_id}"
            )

            already_imported = FoodItem.external_reference_exists("USDA", selected_food["fdc_id"])
            if already_imported:
                st.info("Acest aliment USDA este deja importat în catalog.")

            if st.button(
                "Importă alimentul",
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
                    st.error("Alimentul importat nu respectă regulile de validare.")
                    return

                if imported_food.save():
                    st.session_state["admin_food_catalog_toast"] = (
                        f"Alimentul „{imported_name.strip()}” a fost importat."
                    )
                    st.session_state["usda_food_results"] = []
                    st.session_state.pop("usda_food_results_context", None)
                    st.rerun()
                else:
                    st.error("Eroare la import. Verifică dacă alimentul nu există deja în catalog.")


def render_admin_food_catalog_page() -> None:
    st.header("🍎 Gestiune Catalog Alimente")
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

    with st.expander("➕ Adaugă un aliment nou", expanded=True):
        with st.form("add_food_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Denumire aliment", key="admin_food_name")
                category = st.selectbox("Categorie", FOOD_CATEGORIES, key="admin_food_category")
                calories = st.number_input("Calorii (per 100g)", step=1.0, key="admin_food_calories")
            with col2:
                protein = st.number_input("Proteine (g)", step=0.1, key="admin_food_protein")
                carbs = st.number_input("Carbohidrați (g)", step=0.1, key="admin_food_carbs")
                fats = st.number_input("Grăsimi (g)", step=0.1, key="admin_food_fats")

            submit_food = st.form_submit_button("Salvează alimentul", type="primary")

            if submit_food:
                validation_errors = validate_food_item_input(name, calories, protein, carbs, fats)
                if validation_errors:
                    show_first_validation_error(validation_errors)
                else:
                    try:
                        new_food = FoodItem(name.strip(), calories, protein, carbs, fats, category)
                        if new_food.save():
                            st.session_state["admin_food_catalog_toast"] = (
                                f"Alimentul „{name.strip()}” a fost adăugat cu succes!"
                            )
                            st.session_state["admin_food_form_reset"] = True
                            st.rerun()
                        else:
                            st.error("Eroare la adăugarea alimentului.")
                    except ValueError:
                        st.error("Alimentul nu respectă regulile de validare.")

    render_usda_food_import_panel()

    st.subheader("Baza de date nutrițională")
    df_foods = FoodItem.get_all_as_dataframe()
    if not df_foods.empty:
        render_food_catalog_table(df_foods, key_prefix="admin")
    else:
        st.info("Catalogul este gol.")


def render_admin_activity_catalog_page() -> None:
    st.header("🏃‍♂️ Gestiune Catalog Activități")
    show_admin_activity_catalog_toasts()

    if st.session_state.pop("admin_activity_form_reset", False):
        for key in (
            "admin_activity_name",
            "admin_activity_category",
            "admin_activity_met",
        ):
            st.session_state.pop(key, None)

    with st.expander("➕ Adaugă o activitate nouă", expanded=True):
        with st.form("add_activity_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Denumire activitate", key="admin_activity_name")
                category = st.selectbox("Categorie", ACTIVITY_CATEGORIES, key="admin_activity_category")
            with col2:
                met = st.number_input(
                    "Coeficient MET",
                    value=1.0,
                    step=0.1,
                    key="admin_activity_met",
                    help=f"Valoarea minimă acceptată este {Activity.MIN_MET_MULTIPLIER:.1f}. Ex: Alergat = 8.0"
                )

            submit_act = st.form_submit_button("Salvează activitatea", type="primary")

            if submit_act:
                validation_errors = validate_activity_input(name, met, category, check_duplicate=True)
                if validation_errors:
                    show_first_validation_error(validation_errors)
                else:
                    try:
                        new_activity = Activity(name.strip(), met, category)
                        if new_activity.save():
                            st.session_state["admin_activity_catalog_toast"] = (
                                f"Activitatea „{name.strip()}” a fost adăugată cu succes!"
                            )
                            st.session_state["admin_activity_form_reset"] = True
                            st.rerun()
                        else:
                            st.error("Eroare la adăugarea activității.")
                    except ValueError as ve:
                        st.error(f"Eroare de validare: {ve}")

    st.subheader("Lista activităților disponibile")
    df_activities = Activity.get_all_as_dataframe()
    if not df_activities.empty:
        render_activity_catalog_table(df_activities, key_prefix="admin")
    else:
        st.info("Catalogul de activități este gol.")
