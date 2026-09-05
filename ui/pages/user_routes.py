import html
from datetime import date, datetime
from typing import Any

import streamlit as st
from database import get_connection
from services.analytics.energy import calculate_bmi
from ui.language import clear_session_preserving_language, translate
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


USER_PAGES = {
    "dashboard": {
        "label": "Home",
        "render": render_dashboard_page,
    },
    "food_journal": {
        "label": "Food journal",
        "render": render_food_journal_page,
    },
    "activity_journal": {
        "label": "Activity journal",
        "render": render_activity_journal_page,
    },
    "weight_journal": {
        "label": "Weight journal",
        "render": render_weight_journal_page,
    },
    "custom_meals": {
        "label": "Custom meals",
        "render": render_custom_meals_page,
    },
    "what_if": {
        "label": "What-if simulator",
        "render": render_what_if_page,
    },
    "food_catalog": {
        "label": "Food catalog",
        "render": render_user_food_catalog_page,
    },
    "activity_catalog": {
        "label": "Activity catalog",
        "render": render_user_activity_catalog_page,
    },
}
USER_MENU_OPTIONS = tuple(USER_PAGES)
USER_LAST_RENDERED_PAGE_KEY = "user_last_rendered_page"
PROFILE_GOAL_SOURCE_TEXT = {
    "Slabire": "Weight loss",
    "Mentinere": "Maintenance",
    "Crestere": "Muscle gain",
}
JOURNAL_DATE_SELECTOR_KEYS = {
    FOOD_JOURNAL_DATE_KEY,
    ACTIVITY_JOURNAL_DATE_KEY,
    "weight_log_add_date",
}
JOURNAL_DATE_SELECTOR_PREFIXES = (WEIGHT_LOG_ADD_DATE_KEY_PREFIX,)


def render_user_routes() -> None:
    st.sidebar.title(
        translate(
            "Hello, {name}!",
            name=st.session_state["user_full_name"],
        )
    )
    _render_sidebar_profile_summary()

    selected_page = st.sidebar.radio(
        translate("Main menu"),
        options=list(USER_PAGES),
        format_func=display_page_name,
        key="user_main_menu",
    )

    last_rendered_page = st.session_state.get(USER_LAST_RENDERED_PAGE_KEY)
    if last_rendered_page is None:
        st.session_state[USER_LAST_RENDERED_PAGE_KEY] = selected_page
    elif last_rendered_page != selected_page:
        _reset_journal_date_selectors()
        st.session_state[USER_LAST_RENDERED_PAGE_KEY] = selected_page
        st.rerun()

    page_slot = st.empty()
    with page_slot.container():
        apply_page_theme(get_user_page_theme(selected_page))
        _render_selected_user_page(selected_page)

    st.sidebar.divider()
    if st.sidebar.button(
        translate("Log out"),
        width="stretch",
        type="tertiary",
    ):
        clear_session_preserving_language()
        st.rerun()


def _render_sidebar_profile_summary() -> None:
    user_id = st.session_state.get("user_id")
    if not user_id:
        return

    with st.sidebar.expander(translate("My profile")):
        try:
            profile = load_user_profile_summary(int(user_id))
        except RuntimeError:
            st.caption(translate("The profile cannot be loaded right now."))
            return
        if not profile:
            st.caption(translate("The profile cannot be loaded right now."))
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
        (translate("Email"), _format_profile_text(profile.get("email"))),
        (translate("Name"), _format_profile_text(profile.get("full_name"))),
        (
            translate("Registration"),
            _format_profile_date(profile.get("registration_date")),
        ),
        (
            translate("Height"),
            _format_profile_number(profile.get("height_cm"), " cm", 0),
        ),
        (translate("Gender"), _format_profile_text(profile.get("gender"))),
        (translate("Age"), _format_profile_age(profile.get("age"))),
        (translate("Goal"), _format_profile_goal(profile.get("goal"))),
        (
            translate("Weight"),
            _format_profile_weight(
                profile.get("latest_weight_kg"),
                profile.get("latest_weight_date"),
            ),
        ),
        (translate("BMI"), _format_profile_number(profile.get("bmi"), "", 1)),
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


def _format_profile_age(value: Any) -> str:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return "—"
    return translate("{age:.0f} years", age=numeric_value)


def _format_profile_goal(value: Any) -> str:
    goal = _format_profile_text(value)
    if goal == "—":
        return goal
    source_text = PROFILE_GOAL_SOURCE_TEXT.get(goal)
    if source_text is None:
        return goal
    return translate(source_text)


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


def display_page_name(page_id: str) -> str:
    """Return the translated label for a stable user page ID."""
    page = USER_PAGES.get(page_id)
    if page is None:
        return page_id
    return translate(str(page["label"]))


def _render_selected_user_page(page_id: str) -> None:
    USER_PAGES[page_id]["render"]()
