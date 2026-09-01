import hashlib
import unicodedata

import pandas as pd

from ui.language import translate


FOOD_ENTRY_TYPE_SOURCE_TEXT = {
    "Aliment": "Food",
    "Aliment din catalog": "Catalog food",
    "Masă personalizată": "Custom meal",
}
MEAL_TYPE_SOURCE_TEXT = {
    "Mic dejun": "Breakfast",
    "Prânz": "Lunch",
    "Cină": "Dinner",
    "Gustare": "Snack",
}
FOOD_CATEGORY_SOURCE_TEXT = {
    "Toate": "All",
    "Fructe": "Fruits",
    "Legume": "Vegetables",
    "Carne": "Meat",
    "Pește": "Fish",
    "Ouă": "Eggs",
    "Lactate": "Dairy",
    "Cereale": "Grains",
    "Pâine & Panificație": "Bread & bakery products",
    "Paste & Orez": "Pasta & rice",
    "Leguminoase": "Legumes",
    "Nuci & Semințe": "Nuts & seeds",
    "Uleiuri & Grăsimi": "Oils & fats",
    "Mezeluri": "Processed meats",
    "Dulciuri": "Sweets",
    "Gustări": "Snacks",
    "Băuturi & Sucuri": "Beverages & juices",
    "Alcoolice": "Alcoholic beverages",
    "Condimente & Sosuri": "Condiments & sauces",
    "Altele": "Other",
}


def _format_mapped_value(value, source_text_by_value: dict) -> str:
    source_text = source_text_by_value.get(value)
    if source_text is None:
        return str(value)
    return translate(source_text)


def format_food_entry_type(value) -> str:
    """Return a translated label without changing the stable entry-type value."""
    return _format_mapped_value(value, FOOD_ENTRY_TYPE_SOURCE_TEXT)


def format_meal_type(value) -> str:
    """Return a translated label without changing the stored meal-type value."""
    return _format_mapped_value(value, MEAL_TYPE_SOURCE_TEXT)


def format_food_category_for_display(value) -> str:
    """Return a translated label without changing the stored food category."""
    return _format_mapped_value(value, FOOD_CATEGORY_SOURCE_TEXT)


def build_food_selection_display_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return a translated display copy while preserving selection IDs and values."""
    display_dataframe = dataframe.copy()
    if "Categorie" in display_dataframe.columns:
        display_dataframe["Categorie"] = display_dataframe["Categorie"].map(
            format_food_category_for_display
        )
    return display_dataframe


def normalize_search_text(value: str) -> str:
    """Normalizes user search text for case-insensitive and accent-insensitive matching."""
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    without_accents = "".join(
        character for character in normalized
        if not unicodedata.combining(character)
    )
    return " ".join(without_accents.lower().strip().split())


def build_food_selection_dataframe(
    food_options: dict,
    search_text: str,
    category_filter: str,
    max_rows: int | None = None,
) -> pd.DataFrame:
    """Builds a filtered food catalog table for food selection workflows."""
    search_terms = [
        term for term in normalize_search_text(search_text).split()
        if term
    ]
    rows = []

    for food in food_options.values():
        food_name = food["name"]
        food_category = food.get("category") or "Altele"
        normalized_name = normalize_search_text(food_name)
        if search_terms and not all(term in normalized_name for term in search_terms):
            continue
        if category_filter != "Toate" and food_category != category_filter:
            continue

        rows.append({
            "_food_id": food["id"],
            "Denumire": food_name,
            "Categorie": food_category,
            "Sursă": food.get("source_label") or "MacroSense",
            "Kcal/100g": food["calories_100g"],
            "Proteine": food["protein_g"],
            "Carbohidrați": food["carbs_g"],
            "Grăsimi": food["fats_g"],
        })

    if max_rows is not None:
        rows = rows[:max_rows]
    return pd.DataFrame(rows)


def get_food_category_filter_options(food_options: dict) -> list[str]:
    """Returns category filter options for catalog food selectors."""
    categories = sorted({
        food.get("category") or "Altele"
        for food in food_options.values()
    })
    return ["Toate"] + categories


def build_food_selection_state_key(search_text: str, category_filter: str, key_prefix: str = "food_log_food_selection_table") -> str:
    """Builds a selection-table key that resets when the visible catalog changes."""
    normalized_context = f"{normalize_search_text(search_text)}|{category_filter or 'Toate'}"
    digest = hashlib.sha1(normalized_context.encode("utf-8")).hexdigest()[:10]
    return f"{key_prefix}_{digest}"
