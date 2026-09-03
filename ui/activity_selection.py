import hashlib

import pandas as pd

from ui.food_selection import normalize_search_text
from ui.language import translate


ACTIVITY_CATEGORY_SOURCE_TEXT = {
    "Toate": "All",
    "Cardio": "Cardio",
    "Forță": "Strength",
    "Flexibilitate": "Flexibility",
    "Sport de echipă": "Team sport",
    "Activități zilnice": "Daily activities",
    "Altele": "Other",
}
ACTIVITY_MET_METHOD_SOURCE_TEXT = {
    "official_compendium": "Official Compendium",
    "Oficial Compendium": "Official Compendium",
    "compendium_mapping": "MacroSense mapping",
    "Mapare MacroSense": "MacroSense mapping",
    "manual_admin": "Manual admin",
    "Manual Admin": "Manual admin",
    "Necunoscut": "Unknown",
}
ACTIVITY_CALCULATION_METHOD_SOURCE_TEXT = {
    "Manual": "Manual",
    "Estimare MacroSense": "MacroSense estimate",
}


def _format_mapped_value(value, source_text_by_value: dict) -> str:
    source_text = source_text_by_value.get(value)
    if source_text is None:
        return str(value)
    return translate(source_text)


def format_activity_category_for_display(value) -> str:
    """Return a translated category label without changing its stored value."""
    return _format_mapped_value(value, ACTIVITY_CATEGORY_SOURCE_TEXT)


def format_activity_met_method_for_display(value) -> str:
    """Return a translated MET-method label without changing its model value."""
    return _format_mapped_value(value, ACTIVITY_MET_METHOD_SOURCE_TEXT)


def format_activity_calculation_method_for_display(value) -> str:
    """Return a translated log-calculation label without changing service data."""
    return _format_mapped_value(value, ACTIVITY_CALCULATION_METHOD_SOURCE_TEXT)


def build_activity_selection_display_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return a translated selector copy while preserving activity IDs and MET."""
    display_dataframe = dataframe.copy()
    if "Categorie" in display_dataframe.columns:
        display_dataframe["Categorie"] = display_dataframe["Categorie"].map(
            format_activity_category_for_display
        )
    if "Metodă MET" in display_dataframe.columns:
        display_dataframe["Metodă MET"] = display_dataframe["Metodă MET"].map(
            format_activity_met_method_for_display
        )
    return display_dataframe


def build_activity_selection_dataframe(
    activity_options: dict,
    search_text: str,
    category_filter: str,
    max_rows: int | None = None,
) -> pd.DataFrame:
    """Builds a filtered activity catalog table for activity selection workflows."""
    search_terms = [
        term for term in normalize_search_text(search_text).split()
        if term
    ]
    rows = []

    for activity in activity_options.values():
        activity_name = activity["name"]
        activity_category = activity.get("category") or "Altele"
        normalized_name = normalize_search_text(activity_name)
        if search_terms and not all(term in normalized_name for term in search_terms):
            continue
        if category_filter != "Toate" and activity_category != category_filter:
            continue

        rows.append({
            "_activity_id": activity["id"],
            "Denumire": activity_name,
            "Categorie": activity_category,
            "Sursă": activity.get("source_label") or "MacroSense",
            "Metodă MET": activity.get("met_method_label") or "Manual Admin",
            "MET": activity["met"],
        })

    if max_rows is not None:
        rows = rows[:max_rows]
    return pd.DataFrame(rows)


def get_activity_category_filter_options(activity_options: dict) -> list[str]:
    """Returns category filter options for catalog activity selectors."""
    categories = sorted({
        activity.get("category") or "Altele"
        for activity in activity_options.values()
    })
    return ["Toate"] + categories


def build_activity_selection_state_key(
    search_text: str,
    category_filter: str,
    key_prefix: str = "activity_log_activity_selection_table",
) -> str:
    """Builds a selection-table key that resets when the visible catalog changes."""
    normalized_context = f"{normalize_search_text(search_text)}|{category_filter or 'Toate'}"
    digest = hashlib.sha1(normalized_context.encode("utf-8")).hexdigest()[:10]
    return f"{key_prefix}_{digest}"
