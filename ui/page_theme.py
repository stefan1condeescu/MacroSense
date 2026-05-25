import streamlit as st


PAGE_THEME_CLASSES = {
    "dashboard": "page-theme-dashboard",
    "food": "page-theme-food",
    "activity": "page-theme-activity",
    "weight": "page-theme-weight",
    "meals": "page-theme-meals",
    "what_if": "page-theme-what-if",
    "catalog_food": "page-theme-catalog-food",
    "catalog_activity": "page-theme-catalog-activity",
    "auth": "page-theme-auth",
}


def apply_page_theme(theme_key: str) -> None:
    """Adds an invisible marker used by the global CSS theme rules."""
    theme_class = PAGE_THEME_CLASSES.get(theme_key, PAGE_THEME_CLASSES["dashboard"])
    st.markdown(
        f'<div class="page-theme-marker {theme_class}" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )


def get_user_page_theme(menu_choice: str) -> str:
    """Returns the visual theme key for a user-facing menu option."""
    normalized_choice = str(menu_choice or "").lower()
    if "jurnal alimentar" in normalized_choice or "catalog alimente" in normalized_choice:
        return "food"
    if "jurnal activit" in normalized_choice or "catalog activit" in normalized_choice:
        return "activity"
    if "jurnal greutate" in normalized_choice:
        return "weight"
    if "mese personalizate" in normalized_choice:
        return "meals"
    if "what-if" in normalized_choice:
        return "what_if"
    return "dashboard"


def get_admin_page_theme(menu_choice: str) -> str:
    """Returns the visual theme key for an admin catalog page."""
    normalized_choice = str(menu_choice or "").lower()
    if "activit" in normalized_choice:
        return "catalog_activity"
    return "catalog_food"
