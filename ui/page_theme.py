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

USER_PAGE_THEMES = {
    "dashboard": "dashboard",
    "food_journal": "food",
    "activity_journal": "activity",
    "weight_journal": "weight",
    "custom_meals": "meals",
    "what_if": "what_if",
    "food_catalog": "food",
    "activity_catalog": "activity",
}

ADMIN_PAGE_THEMES = {
    "food_catalog": "catalog_food",
    "activity_catalog": "catalog_activity",
}


def apply_page_theme(theme_key: str) -> None:
    """Adds an invisible marker used by the global CSS theme rules."""
    theme_class = PAGE_THEME_CLASSES.get(theme_key, PAGE_THEME_CLASSES["dashboard"])
    st.markdown(
        f'<div class="page-theme-marker {theme_class}" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )


def get_user_page_theme(page_id: str) -> str:
    """Return the visual theme key for a stable user page ID."""
    return USER_PAGE_THEMES.get(page_id, "dashboard")


def get_admin_page_theme(page_id: str) -> str:
    """Return the visual theme key for a stable administrator page ID."""
    return ADMIN_PAGE_THEMES.get(page_id, "catalog_food")
