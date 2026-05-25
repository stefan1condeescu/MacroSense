import html
from datetime import date, datetime
from typing import Any

import streamlit as st
from database import get_connection
from services.analytics.energy import calculate_bmi
from ui.page_theme import apply_page_theme, get_user_page_theme
from ui.pages.activity_journal_page import (
    ACTIVITY_JOURNAL_DATE_KEY,
    render_activity_journal_page,
)
from ui.pages.custom_meals_page import render_custom_meals_page
from ui.pages.dashboard_page import render_dashboard_page
from ui.pages.food_journal_page import FOOD_JOURNAL_DATE_KEY, render_food_journal_page
from ui.pages.user_catalog_pages import render_user_activity_catalog_page, render_user_food_catalog_page
from ui.pages.weight_journal_page import (
    WEIGHT_LOG_ADD_DATE_KEY_PREFIX,
    render_weight_journal_page,
)
from ui.pages.what_if_page import render_what_if_page


USER_MENU_OPTIONS = [
    "Acasă",
    "Jurnal Alimentar",
    "Jurnal Activități",
    "Jurnal Greutate",
    "Mese Personalizate",
    "Simulator What-if",
    "Catalog Alimente",
    "Catalog Activități",
]
USER_LAST_RENDERED_PAGE_KEY = "user_last_rendered_page"
JOURNAL_DATE_SELECTOR_KEYS = {
    FOOD_JOURNAL_DATE_KEY,
    ACTIVITY_JOURNAL_DATE_KEY,
    "weight_log_add_date",
}
JOURNAL_DATE_SELECTOR_PREFIXES = (WEIGHT_LOG_ADD_DATE_KEY_PREFIX,)


def render_user_routes() -> None:
    st.sidebar.title(f"Salut, {st.session_state['user_full_name']}!")
    _render_sidebar_profile_summary()

    choice = st.sidebar.radio("Meniu Principal", USER_MENU_OPTIONS, key="user_main_menu")

    last_rendered_page = st.session_state.get(USER_LAST_RENDERED_PAGE_KEY)
    if last_rendered_page is None:
        st.session_state[USER_LAST_RENDERED_PAGE_KEY] = choice
    elif last_rendered_page != choice:
        _reset_journal_date_selectors()
        st.session_state[USER_LAST_RENDERED_PAGE_KEY] = choice
        st.rerun()

    page_slot = st.empty()
    with page_slot.container():
        apply_page_theme(get_user_page_theme(choice))
        _render_selected_user_page(choice)

    st.sidebar.divider()
    if st.sidebar.button("Deconectare", width="stretch", type="tertiary"):
        st.session_state.clear()
        st.rerun()


def _render_sidebar_profile_summary() -> None:
    user_id = st.session_state.get("user_id")
    if not user_id:
        return

    with st.sidebar.expander("Profilul meu"):
        try:
            profile = load_user_profile_summary(int(user_id))
        except RuntimeError:
            st.caption("Profilul nu poate fi încărcat momentan.")
            return
        if not profile:
            st.caption("Profilul nu poate fi încărcat momentan.")
            return
        st.markdown(build_user_profile_summary_html(profile), unsafe_allow_html=True)


def load_user_profile_summary(user_id: int) -> dict[str, Any] | None:
    """Load read-only profile details for the sidebar summary."""
    conn = None
    try:
        conn = get_connection()
        if not conn:
            return None

        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT email, full_name, height_cm, age, gender, goal, registration_date
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        user_row = cursor.fetchone()
        if not user_row:
            return None

        cursor.execute(
            """
            SELECT log_date, weight_kg
            FROM weight_logs
            WHERE user_id = %s
            ORDER BY log_date DESC, id DESC
            LIMIT 1
            """,
            (user_id,),
        )
        weight_row = cursor.fetchone()
        latest_weight_kg = float(weight_row[1]) if weight_row else None
        latest_weight_date = weight_row[0] if weight_row else None
        bmi = _calculate_profile_bmi(user_row[2], latest_weight_kg)

        return {
            "email": user_row[0],
            "full_name": user_row[1],
            "height_cm": user_row[2],
            "age": user_row[3],
            "gender": user_row[4],
            "goal": user_row[5],
            "registration_date": user_row[6],
            "latest_weight_kg": latest_weight_kg,
            "latest_weight_date": latest_weight_date,
            "bmi": bmi,
        }
    except Exception as exc:
        raise RuntimeError(f"Could not load user profile summary: {exc}") from exc
    finally:
        if conn:
            conn.close()


def build_user_profile_summary_html(profile: dict[str, Any]) -> str:
    """Build escaped read-only sidebar profile details."""
    rows = [
        ("Email", _format_profile_text(profile.get("email"))),
        ("Nume", _format_profile_text(profile.get("full_name"))),
        ("Înregistrare", _format_profile_date(profile.get("registration_date"))),
        ("Înălțime", _format_profile_number(profile.get("height_cm"), " cm", 0)),
        ("Sex", _format_profile_text(profile.get("gender"))),
        ("Vârstă", _format_profile_number(profile.get("age"), " ani", 0)),
        ("Obiectiv", _format_profile_text(profile.get("goal"))),
        (
            "Greutate",
            _format_profile_weight(
                profile.get("latest_weight_kg"),
                profile.get("latest_weight_date"),
            ),
        ),
        ("BMI", _format_profile_number(profile.get("bmi"), "", 1)),
    ]
    row_html = "".join(
        [
            '<div class="user-profile-row">'
            f"<span>{html.escape(label, quote=True)}</span>"
            f"<strong>{html.escape(value, quote=True)}</strong>"
            "</div>"
            for label, value in rows
        ]
    )
    return f'<div class="user-profile-card">{row_html}</div>'


def _calculate_profile_bmi(height_cm: Any, weight_kg: Any) -> float | None:
    try:
        if weight_kg is None:
            return None
        return calculate_bmi(float(weight_kg), float(height_cm))
    except (TypeError, ValueError):
        return None


def _format_profile_text(value: Any) -> str:
    if value is None or str(value).strip() == "":
        return "—"
    return str(value)


def _format_profile_number(value: Any, suffix: str, decimals: int) -> str:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return "—"
    if decimals == 0:
        return f"{numeric_value:.0f}{suffix}"
    return f"{numeric_value:.{decimals}f}{suffix}"


def _format_profile_weight(weight_kg: Any, weight_date: Any) -> str:
    weight_text = _format_profile_number(weight_kg, " kg", 1)
    date_text = _format_profile_date(weight_date)
    if weight_text == "—":
        return "—"
    if date_text == "—":
        return weight_text
    return f"{weight_text} ({date_text})"


def _format_profile_date(value: Any) -> str:
    if value is None:
        return "—"
    try:
        date_value = value.date() if isinstance(value, datetime) else value
        if not isinstance(date_value, date):
            date_value = datetime.fromisoformat(str(value)).date()
    except (TypeError, ValueError):
        return "—"
    return date_value.strftime("%d.%m.%Y")


def _reset_journal_date_selectors() -> None:
    for key in list(st.session_state.keys()):
        if key in JOURNAL_DATE_SELECTOR_KEYS or key.startswith(
            JOURNAL_DATE_SELECTOR_PREFIXES
        ):
            del st.session_state[key]


def _render_selected_user_page(choice: str) -> None:
    if choice == "Acasă":
        render_dashboard_page()
    elif choice == "Jurnal Alimentar":
        render_food_journal_page()
    elif choice == "Jurnal Activități":
        render_activity_journal_page()
    elif choice == "Jurnal Greutate":
        render_weight_journal_page()
    elif choice == "Mese Personalizate":
        render_custom_meals_page()
    elif choice == "Simulator What-if":
        render_what_if_page()
    elif choice == "Catalog Alimente":
        render_user_food_catalog_page()
    elif choice == "Catalog Activități":
        render_user_activity_catalog_page()
