from __future__ import annotations

from datetime import date, datetime
from html import escape
import json
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from services.analytics.dashboard_data import (
    get_dashboard_data,
    get_latest_user_data_date,
)
from services.ml.prediction import (
    DEFAULT_PREDICTION_HORIZONS,
    UserWeightPredictions,
    get_latest_available_user_weight_predictions,
)
from services.recommendations.simple_recommendations import (
    RECOMMENDATION_DAYS,
    RecommendationCard,
    build_dashboard_recommendation_cards,
)
from ui.language import translate, translated_selection_key


INTERVAL_OPTIONS = (7, 30, 90)
DEFAULT_INTERVAL_DAYS = 30
LEGACY_INTERVAL_DAYS = {
    "7 zile": 7,
    "30 zile": 30,
    "90 zile": 90,
}
DASHBOARD_INTERVAL_KEY = "dashboard_interval_selection"
DASHBOARD_ANALYSIS_DATE_KEY = "dashboard_analysis_date"

GOAL_HELP_SOURCE_TEXT = (
    "Possible goals: Weight loss = a suggested calorie deficit; Maintenance = "
    "weight stability; Muscle gain = a controlled surplus that supports training."
)

PROTEIN_COLOR = "#D64545"
CARBS_COLOR = "#3D7CC9"
FATS_COLOR = "#D89B22"
TDEE_COLOR = "#F28E2B"
FOOD_COLOR = "#4E79A7"
ACTIVITY_COLOR = "#6F52ED"
DEFICIT_COLOR = "#2E7D32"
SURPLUS_COLOR = "#C94C4C"

REFERENCE_WEIGHT_SOURCE_TEXT = {
    "missing": "No weight",
    "actual": "Actual weigh-in",
    "future_fallback": "Fallback from the first future weight",
    "previous": "Previous weight used as reference",
}
BALANCE_TYPE_SOURCE_TEXT = {
    "deficit": "Deficit",
    "surplus": "Surplus",
}
MACRONUTRIENT_SOURCE_TEXT = {
    "protein_g": "Protein",
    "carbs_g": "Carbohydrates",
    "fats_g": "Fats",
}
ACTIVITY_STATUS_SOURCE_TEXT = {
    "logged": "Workout logged",
    "rest_day": "Day without a workout",
}
ACTIVITY_CATEGORY_SOURCE_TEXT = {
    "Cardio": "Cardio",
    "Forță": "Strength",
    "Flexibilitate": "Flexibility",
    "Sport de echipă": "Team sport",
    "Activități zilnice": "Daily activities",
    "Altele": "Other",
}
ACTIVITY_METHOD_SOURCE_TEXT = {
    "Manual": "Manual",
    "Estimare MacroSense": "MacroSense estimate",
}


def render_dashboard_page() -> None:
    st.title(f"🏠 {translate('Home')}")
    st.caption(
        translate(
            "The dashboard is read-only. TDEE and calorie balance values are "
            "estimates calculated from your profile, weight, and journals."
        )
    )

    days = _initialize_interval_selection()

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.warning(translate("Log in to view the dashboard."))
        return

    today = date.today()
    try:
        latest_data_date = get_latest_user_data_date(int(user_id), today)
    except RuntimeError as exc:
        st.error(
            translate(
                "Error loading the analysis date: {error}",
                error=exc,
            )
        )
        return

    selected_analysis_date = _render_analysis_date_selector(
        latest_data_date=latest_data_date,
        today=today,
    )

    try:
        data = get_dashboard_data(
            user_id=user_id,
            days=days,
            end_date=selected_analysis_date,
        )
    except RuntimeError as exc:
        st.error(
            translate(
                "Error loading the dashboard: {error}",
                error=exc,
            )
        )
        return

    _render_current_state(data.get("current", {}), data.get("end_date"), today=today)
    prediction_result = _render_weight_prediction_section(
        user_id,
        data.get("end_date"),
        today=today,
    )
    _render_recommendation_section(
        user_id,
        days,
        data,
        prediction_result,
        data.get("end_date"),
    )

    st.divider()
    st.subheader(translate("Progress over the interval"))
    st.radio(
        translate("Analysis interval"),
        list(INTERVAL_OPTIONS),
        format_func=_display_interval_name,
        horizontal=True,
        key=translated_selection_key(DASHBOARD_INTERVAL_KEY),
        **_interval_radio_kwargs(days),
    )

    _render_interval_summary(data)
    st.divider()
    _render_weight_chart(data)
    _render_calorie_chart(data)
    _render_balance_chart(data)
    _render_macro_chart(data)
    _render_activity_section(data)


def _render_analysis_date_selector(
    latest_data_date: date | None,
    today: date,
) -> date:
    default_date = latest_data_date or today
    current_value = st.session_state.get(DASHBOARD_ANALYSIS_DATE_KEY)
    initial_date = _resolve_dashboard_analysis_date(
        current_value,
        default_date=default_date,
        today=today,
    )
    if current_value is not None and current_value != initial_date:
        st.session_state[DASHBOARD_ANALYSIS_DATE_KEY] = initial_date

    selected_date = st.date_input(
        translate("Analysis date"),
        value=initial_date,
        max_value=today,
        key=DASHBOARD_ANALYSIS_DATE_KEY,
        help=translate(
            "The dashboard, recommendations, and ML prediction are calculated "
            "through this date."
        ),
    )
    selected_date = _resolve_dashboard_analysis_date(
        selected_date,
        default_date=default_date,
        today=today,
    )
    if latest_data_date and selected_date == latest_data_date and selected_date != today:
        st.caption(
            translate("The analysis date is the latest day with logged data.")
        )
    elif selected_date != today:
        st.caption(translate("Dashboard recalculated through the selected date."))
    return selected_date


def _resolve_dashboard_analysis_date(
    value: Any,
    default_date: date,
    today: date,
) -> date:
    try:
        resolved_date = _to_date(value) if value else _to_date(default_date)
    except (TypeError, ValueError):
        resolved_date = _to_date(default_date)
    if resolved_date > today:
        return today
    return resolved_date


def _analysis_date_context(
    analysis_date: date | None,
    today: date | None = None,
) -> dict[str, str | bool]:
    resolved_today = today or date.today()
    is_today = _to_date(analysis_date or resolved_today) == resolved_today
    return {
        "is_today": is_today,
        "state_title": translate(
            "Current state" if is_today else "State on the analysis date"
        ),
        "day_phrase": translate("today" if is_today else "on the analysis date"),
        "day_sentence": translate("Today" if is_today else "On the analysis date"),
    }


def _render_current_state(
    current: dict[str, Any],
    analysis_date: date | None,
    today: date | None = None,
) -> None:
    day_context = _analysis_date_context(analysis_date, today=today)
    day_phrase = str(day_context["day_phrase"])
    is_today = bool(day_context["is_today"])

    st.subheader(str(day_context["state_title"]))

    _render_card_grid(
        [
            {
                "label": translate("Height"),
                "value": _format_cm(current.get("height_cm")),
                "accent": "profile",
                "help": translate(
                    "The height saved when the profile was created. It is used "
                    "to calculate BMI and BMR."
                ),
            },
            {
                "label": translate("Gender"),
                "value": _format_gender(current.get("gender")),
                "accent": "profile",
                "help": translate(
                    "The biological sex selected in the profile. It is used in "
                    "the Mifflin-St Jeor BMR formula."
                ),
            },
            {
                "label": translate("Age"),
                "value": _format_age(current.get("age")),
                "accent": "profile",
                "help": translate(
                    "The age saved in the profile. It is used in the Mifflin-St "
                    "Jeor BMR formula."
                ),
            },
            {
                "label": translate("Goal"),
                "value": _format_goal(current.get("goal")),
                "accent": "goal",
                "help": _goal_description(current.get("goal"))
                or translate(GOAL_HELP_SOURCE_TEXT),
            },
        ],
        columns_count=4,
    )

    _render_card_grid(
        [
            {
                "label": translate("Current weight")
                if is_today
                else translate("Weight on the analysis date"),
                "value": _format_kg(current.get("current_weight_kg")),
                "delta": _format_kg_delta(current.get("weight_delta_kg")),
                "accent": "weight",
                "help": translate(
                    "The latest weight saved through the analysis date. The delta "
                    "shows the difference from the previous available weigh-in."
                ),
            },
            {
                "label": translate("Current BMI")
                if is_today
                else translate("BMI on the analysis date"),
                "value": _format_number(current.get("current_bmi"), ""),
                "accent": "health",
                "help": translate(
                    "BMI = reference weight / height². It is a general indicator, "
                    "not a medical diagnosis."
                ),
            },
            {
                "label": translate("Estimated BMR"),
                "value": _format_kcal(current.get("current_bmr")),
                "accent": "energy",
                "help": translate(
                    "BMR is the basal energy expenditure estimated with the "
                    "Mifflin-St Jeor formula, using current weight, height, age, "
                    "and biological sex."
                ),
            },
            {
                "label": translate(
                    "Estimated TDEE {day_phrase}",
                    day_phrase=day_phrase,
                ),
                "value": _format_kcal(current.get("today_estimated_tdee")),
                "accent": "energy",
                "help": translate(
                    "Estimated TDEE {day_phrase} = BMR * 1.2 + calories burned "
                    "through activities logged {day_phrase}. The 1.2 factor "
                    "represents the sedentary baseline.",
                    day_phrase=day_phrase,
                ),
            },
        ],
        columns_count=4,
    )

    _render_card_grid(
        [
            {
                "label": translate(
                    "Calories consumed {day_phrase}",
                    day_phrase=day_phrase,
                ),
                "value": _format_kcal_or_missing(current.get("today_calories_in")),
                "accent": "food",
                "help": translate(
                    "Total calories from food logged {day_phrase}. If no food is "
                    "logged, the value is Not logged, not 0 kcal.",
                    day_phrase=day_phrase,
                ),
            },
            {
                "label": translate(
                    "Activity calories {day_phrase}",
                    day_phrase=day_phrase,
                ),
                "value": _format_kcal_zero(current.get("today_activity_calories")),
                "accent": "activity",
                "help": translate(
                    "Calories burned through activities logged {day_phrase}. If "
                    "there are no workouts, 0 kcal is displayed as a rest day.",
                    day_phrase=day_phrase,
                ),
            },
            {
                "label": translate(
                    "Estimated balance {day_phrase}",
                    day_phrase=day_phrase,
                ),
                "value": _format_signed_kcal(current.get("today_estimated_balance")),
                "accent": "balance",
                "help": translate(
                    "Estimated balance {day_phrase} = calories consumed "
                    "{day_phrase} - estimated TDEE {day_phrase}. It is calculated "
                    "only when food is logged {day_phrase}.",
                    day_phrase=day_phrase,
                ),
            },
        ],
        columns_count=3,
    )

    status_messages = []
    if not current.get("today_has_food_logs"):
        if is_today:
            status_messages.append(
                translate(
                    "Add today's meals to see calorie intake and energy balance."
                )
            )
        else:
            status_messages.append(
                translate(
                    "No meals are logged on the analysis date; calorie intake "
                    "and energy balance remain unlogged."
                )
            )
    if not current.get("today_has_activity_logs"):
        if is_today:
            status_messages.append(
                translate(
                    "No workouts today: logged activity is 0 kcal, so the day is "
                    "treated as a rest day."
                )
            )
        else:
            status_messages.append(
                translate(
                    "No workouts are logged on the analysis date; activity is "
                    "0 kcal, as on a rest day."
                )
            )
    if status_messages:
        st.info(" ".join(status_messages))


def _render_weight_prediction_section(
    user_id: int,
    analysis_date: date | None,
    today: date | None = None,
) -> UserWeightPredictions | None:
    st.subheader(translate("Weight prediction"))

    try:
        prediction_result = get_latest_available_user_weight_predictions(
            user_id=int(user_id),
            analysis_date=analysis_date,
            max_lookback_days=14,
            prefer_complete_days=True,
            today=today,
        )
    except RuntimeError:
        st.info(
            translate(
                "The ML prediction is temporarily unavailable. Check the "
                "trained models and database connection."
            )
        )
        return None

    cards = _build_weight_prediction_cards(
        prediction_result,
        requested_analysis_date=analysis_date,
    )
    _render_card_grid(cards, columns_count=2)

    if prediction_result.predictions:
        st.caption(
            _format_prediction_source_caption(
                prediction_result,
                requested_analysis_date=analysis_date,
                today=today,
            )
        )
    else:
        st.info(
            translate(
                "The prediction appears once there are enough logged meals, "
                "weigh-ins, and trained ML models for the current user."
            )
        )

    return prediction_result


def _render_recommendation_section(
    user_id: int,
    selected_days: int,
    dashboard_data: dict[str, Any],
    prediction_result: UserWeightPredictions | None,
    analysis_date: date | None,
) -> None:
    recommendation_data = dashboard_data
    if selected_days != RECOMMENDATION_DAYS:
        try:
            recommendation_data = get_dashboard_data(
                user_id=int(user_id),
                days=RECOMMENDATION_DAYS,
                end_date=analysis_date,
            )
        except RuntimeError:
            recommendation_data = dashboard_data

    st.subheader(translate("Recommendations"))
    day_context = _analysis_date_context(analysis_date)
    if bool(day_context["is_today"]):
        st.caption(
            translate(
                "Based on the last {days} days.",
                days=RECOMMENDATION_DAYS,
            )
        )
    else:
        st.caption(
            translate(
                "Based on the last {days} days through the analysis date.",
                days=RECOMMENDATION_DAYS,
            )
        )
    cards = build_dashboard_recommendation_cards(
        recommendation_data,
        prediction_result,
    )
    _render_recommendation_grid(cards)


def _render_recommendation_grid(cards: list[RecommendationCard]) -> None:
    columns = st.columns(4)
    for index, card in enumerate(cards):
        with columns[index % 4]:
            st.markdown(_build_recommendation_card_html(card), unsafe_allow_html=True)


def _build_recommendation_card_html(card: RecommendationCard) -> str:
    category = escape(translate(card.category))
    status = escape(translate(card.status))
    message = escape(translate(card.message))
    return "".join(
        [
            f'<div class="recommendation-card {escape(card.accent)}">',
            f'<div class="recommendation-card-category">{category}</div>',
            f'<div class="recommendation-card-status">{status}</div>',
            f'<div class="recommendation-card-message">{message}</div>',
            "</div>",
        ]
    )


def _build_weight_prediction_cards(
    prediction_result: UserWeightPredictions,
    requested_analysis_date: date | None = None,
) -> list[dict[str, Any]]:
    predictions_by_horizon = {
        prediction.horizon_days: prediction
        for prediction in prediction_result.predictions
    }
    requested_date = _to_date(requested_analysis_date) if requested_analysis_date else None
    uses_fallback_date = (
        requested_date is not None
        and prediction_result.analysis_date != requested_date
    )
    cards: list[dict[str, Any]] = []
    for horizon_days in DEFAULT_PREDICTION_HORIZONS:
        prediction = predictions_by_horizon.get(horizon_days)
        if prediction:
            label = translate("In {days} days", days=horizon_days)
            if uses_fallback_date:
                label = translate(
                    "In {days} days from {date}",
                    days=horizon_days,
                    date=_format_date(prediction.analysis_date),
                )
            cards.append(
                {
                    "label": label,
                    "value": _format_kg(prediction.predicted_weight_kg),
                    "caption": translate(
                        "Estimated change: {change} | Date: {date} | MAE: {mae}",
                        change=_format_kg_delta(prediction.predicted_change_kg)
                        or "—",
                        date=_format_date(prediction.target_date),
                        mae=_format_prediction_error(prediction.metrics.get("mae")),
                    ),
                    "accent": "prediction",
                    "help": translate(
                        "ML prediction calculated from food, activity, and weight "
                        "history, without future data."
                    ),
                }
            )
            continue

        reason = prediction_result.unavailable_horizons.get(
            horizon_days,
            "There is not enough data for this interval.",
        )
        cards.append(
            {
                "label": translate("In {days} days", days=horizon_days),
                "value": translate("Unavailable"),
                "caption": _format_prediction_unavailable_reason(reason),
                "accent": "prediction",
                "help": translate(
                    "The prediction becomes available once enough data exists."
                ),
            }
        )
    return cards


def _format_prediction_source_caption(
    prediction_result: UserWeightPredictions,
    requested_analysis_date: date | None,
    today: date | None = None,
) -> str:
    actual_date = _to_date(prediction_result.analysis_date)
    requested_date = (
        _to_date(requested_analysis_date)
        if requested_analysis_date
        else actual_date
    )
    current_date = today or date.today()
    if actual_date == requested_date:
        return translate(
            "Prediction calculated from data available through {date}.",
            date=_format_date(actual_date),
        )
    if requested_date == current_date:
        return translate(
            "The prediction starts from {actual_date}, the latest day with enough "
            "data. The current day is skipped because it may be incomplete.",
            actual_date=_format_date(actual_date),
        )
    return translate(
        "The prediction starts from {actual_date} because there is not enough "
        "recent data for {requested_date}.",
        actual_date=_format_date(actual_date),
        requested_date=_format_date(requested_date),
    )


def _format_prediction_error(value: Any) -> str:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return "—"
    return f"{numeric_value:.2f} kg"


def _format_prediction_unavailable_reason(reason: str) -> str:
    if "Missing model artifact" in reason or "Missing metadata artifact" in reason:
        return translate("The ML models have not been trained yet.")
    if reason in {
        "Nu există suficiente date pentru acest interval.",
        "There is not enough data for this interval.",
    }:
        return translate("There is not enough data for this interval.")
    if reason in {
        "Nu există suficiente date recente pentru predicție.",
        "There is not enough recent data for a prediction.",
    }:
        return translate("There is not enough recent data for a prediction.")
    if reason in {"Utilizatorul nu există.", "The user could not be found."}:
        return translate("The user could not be found.")
    return translate("The ML prediction is temporarily unavailable.")


def _resolve_interval_days(value: Any) -> int:
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value in INTERVAL_OPTIONS
    ):
        return int(value)
    if isinstance(value, str) and value in LEGACY_INTERVAL_DAYS:
        return LEGACY_INTERVAL_DAYS[value]
    return DEFAULT_INTERVAL_DAYS


def _initialize_interval_selection() -> int:
    current_value = st.session_state.get(DASHBOARD_INTERVAL_KEY)
    selected_days = _resolve_interval_days(current_value)
    if current_value is not None and current_value != selected_days:
        st.session_state[DASHBOARD_INTERVAL_KEY] = selected_days
    return selected_days


def _interval_radio_kwargs(days: int) -> dict[str, int]:
    if DASHBOARD_INTERVAL_KEY in st.session_state:
        return {}
    return {"index": list(INTERVAL_OPTIONS).index(days)}


def _display_interval_name(days: int) -> str:
    return translate("{days} days", days=days)


def _render_card_grid(cards: list[dict[str, Any]], columns_count: int) -> None:
    columns = st.columns(columns_count)
    for index, card in enumerate(cards):
        with columns[index % columns_count]:
            _render_dashboard_card(**card)


def _render_dashboard_card(
    label: str,
    value: str,
    accent: str = "neutral",
    delta: str | None = None,
    caption: str | None = None,
    help: str | None = None,
) -> None:
    st.markdown(
        _build_dashboard_card_html(
            label=label,
            value=value,
            accent=accent,
            delta=delta,
            caption=caption,
            help=help,
        ),
        unsafe_allow_html=True,
    )


def _build_dashboard_card_html(
    label: str,
    value: str,
    accent: str = "neutral",
    delta: str | None = None,
    caption: str | None = None,
    help: str | None = None,
) -> str:
    help_html = ""
    if help:
        help_html = (
            f'<span class="dashboard-card-help" title="{escape(help)}">?</span>'
        )

    delta_html = ""
    if delta:
        delta_class = "positive" if str(delta).startswith("+") else "negative"
        delta_html = (
            f'<span class="dashboard-card-delta {delta_class}">'
            f"{escape(delta)}</span>"
        )

    caption_html = ""
    if caption:
        caption_html = f'<div class="dashboard-card-caption">{escape(caption)}</div>'

    return "".join(
        [
            f'<div class="dashboard-card {escape(accent)}">',
            '<div class="dashboard-card-label">',
            f"<span>{escape(label)}</span>",
            help_html,
            "</div>",
            f'<div class="dashboard-card-value">{escape(value)}</div>',
            delta_html,
            caption_html,
            "</div>",
        ]
    )


def _render_interval_summary(data: dict[str, Any]) -> None:
    summary = data.get("summary", {})
    days = data.get("days", 30)
    interval_weight_delta = _calculate_interval_weight_delta_from_daily(
        data.get("daily_rows")
    )

    _render_card_grid(
        [
            {
                "label": translate("Interval weight trend"),
                "value": _format_kg_delta(interval_weight_delta) or "—",
                "accent": "weight",
                "help": translate(
                    "The difference between the reference weight on the last day "
                    "of the interval and the first day. It does not mean that you "
                    "had an actual weigh-in every day."
                ),
            },
            {
                "label": translate("Average intake / logged day"),
                "value": _format_kcal(summary.get("avg_calories_in")),
                "accent": "food",
                "help": translate(
                    "Average calories consumed only on days with logged food. "
                    "Days without logged food are not treated as 0 kcal."
                ),
            },
            {
                "label": translate("Average TDEE / food-logged day"),
                "value": _format_kcal(summary.get("avg_estimated_tdee")),
                "accent": "energy",
                "help": translate(
                    "Average estimated TDEE only on days with logged food, so it "
                    "can be compared with food intake."
                ),
            },
            {
                "label": translate("Average balance / food-logged day"),
                "value": _format_signed_kcal(summary.get("avg_estimated_balance")),
                "accent": "balance",
                "help": translate(
                    "Average daily calories consumed - estimated TDEE, calculated "
                    "only on days with logged food."
                ),
            },
        ],
        columns_count=4,
    )

    _render_card_grid(
        [
            {
                "label": translate("Food logging consistency"),
                "value": _format_percent(summary.get("food_logging_consistency")),
                "caption": translate(
                    "{logged_days} / {days} days",
                    logged_days=summary.get("food_days", 0),
                    days=days,
                ),
                "accent": "food",
                "help": translate(
                    "Percentage of days in the interval with at least one logged food."
                ),
            },
            {
                "label": translate("Activity logging consistency"),
                "value": _format_percent(summary.get("activity_logging_consistency")),
                "caption": translate(
                    "{logged_days} / {days} days",
                    logged_days=summary.get("activity_days", 0),
                    days=days,
                ),
                "accent": "activity",
                "help": translate(
                    "Percentage of days in the interval with at least one logged workout."
                ),
            },
            {
                "label": translate("Weight logging consistency"),
                "value": _format_percent(summary.get("weight_logging_consistency")),
                "caption": translate(
                    "{logged_days} / {days} days",
                    logged_days=summary.get("weight_days", 0),
                    days=days,
                ),
                "accent": "weight",
                "help": translate(
                    "Percentage of days in the interval with an actual weigh-in."
                ),
            },
            {
                "label": translate("Overall logging consistency"),
                "value": _format_percent(summary.get("overall_logging_consistency")),
                "caption": translate(
                    "{logged_days} / {days} days",
                    logged_days=summary.get("logged_days", 0),
                    days=days,
                ),
                "accent": "quality",
                "help": translate(
                    "Percentage of days in the interval with logged food, a "
                    "workout, or an actual weigh-in."
                ),
            },
        ],
        columns_count=4,
    )

    _render_card_grid(
        [
            {
                "label": translate("Total activity calories"),
                "value": _format_kcal_zero(summary.get("activity_total_calories")),
                "accent": "activity",
                "help": translate(
                    "Total calories burned through workouts in the selected interval."
                ),
            },
            {
                "label": translate("Exercise entries"),
                "value": str(summary.get("workouts_count", 0)),
                "accent": "activity",
                "help": translate(
                    "Total number of logged exercises or workouts in the interval. "
                    "A single day can have multiple entries."
                ),
            },
            {
                "label": translate("Average protein"),
                "value": _format_number(summary.get("avg_protein_g"), " g"),
                "accent": "food",
                "help": translate(
                    "Average protein consumed on days with logged food."
                ),
            },
            {
                "label": translate("Protein / kg body weight"),
                "value": _format_number(summary.get("avg_protein_per_kg"), " g/kg"),
                "accent": "health",
                "help": translate(
                    "Average daily protein divided by the reference weight for "
                    "that day. It will be useful for food recommendations."
                ),
            },
        ],
        columns_count=4,
    )

    if not summary.get("has_energy_estimates"):
        st.info(
            translate(
                "Add at least one weight entry to calculate BMR, TDEE, and the "
                "estimated calorie balance."
            )
        )


def _render_weight_chart(data: dict[str, Any]) -> None:
    st.subheader(translate("Weight trend"))
    reference_rows = _prepare_daily_weight_rows(data.get("daily_rows", pd.DataFrame()))
    actual_rows = _prepare_weight_rows(data.get("weight_rows", pd.DataFrame()))
    date_domain = _date_order_domain(reference_rows)
    if reference_rows.empty:
        st.info(
            translate(
                "No reference weight is available for the selected interval."
            )
        )
        return

    reference_rows = reference_rows.copy()
    reference_rows["reference_weight_source_label"] = reference_rows[
        "reference_weight_source_id"
    ].map(_format_reference_weight_source)

    base = alt.Chart(reference_rows).encode(
        x=_daily_x_axis(date_domain),
        y=alt.Y(
            "reference_weight_kg:Q",
            title=translate("Weight (kg)"),
            scale=alt.Scale(zero=False),
        ),
        tooltip=[
            alt.Tooltip(
                "log_date:T",
                title=translate("Date"),
                format="%d.%m.%Y",
            ),
            alt.Tooltip(
                "reference_weight_kg:Q",
                title=translate("Reference weight"),
                format=".1f",
            ),
            alt.Tooltip(
                "reference_weight_source_label:N",
                title=translate("Source"),
            ),
            alt.Tooltip(
                "reference_weight_days_distance:Q",
                title=translate("Distance in days"),
            ),
        ],
    )
    layers = [
        base.mark_line(color="#2563EB", strokeWidth=3),
        base.mark_circle(color="#2563EB", size=55),
    ]
    if not actual_rows.empty:
        actual_points = alt.Chart(actual_rows).mark_point(
            color="#111827", filled=True, size=90
        ).encode(
            x=_daily_x_axis(date_domain),
            y=alt.Y(
                "weight_kg:Q",
                title=translate("Weight (kg)"),
                scale=alt.Scale(zero=False),
            ),
            tooltip=[
                alt.Tooltip(
                    "log_date:T",
                    title=translate("Actual weigh-in"),
                    format="%d.%m.%Y",
                ),
                alt.Tooltip(
                    "weight_kg:Q",
                    title=translate("Weight"),
                    format=".1f",
                ),
            ],
        )
        layers.append(actual_points)

    chart = alt.layer(*layers).properties(height=260)
    st.altair_chart(_configure_chart(chart), width="stretch")
    st.caption(
        translate(
            "The line shows the reference weight for each day. The black points "
            "mark the days when you entered an actual weigh-in."
        )
    )


def _render_calorie_chart(data: dict[str, Any]) -> None:
    st.subheader(translate("Calories consumed vs estimated TDEE"))
    daily_rows = _prepare_daily_rows(data.get("daily_rows", pd.DataFrame()))
    date_domain = _date_order_domain(daily_rows)
    if daily_rows.empty:
        st.info(translate("No data is available for the selected interval."))
        return

    food_rows = daily_rows[daily_rows["has_food_logs"]].dropna(
        subset=["food_calories_in"]
    )
    tdee_rows = daily_rows.dropna(subset=["estimated_tdee"])
    if food_rows.empty and tdee_rows.empty:
        st.info(
            translate("Not enough data is available for the calorie chart.")
        )
        return

    layers = []
    if not food_rows.empty:
        layers.append(
            alt.Chart(food_rows)
            .mark_bar(color=FOOD_COLOR, opacity=0.8)
            .encode(
                x=_daily_x_axis(date_domain),
                y=alt.Y("food_calories_in:Q", title="kcal"),
                tooltip=[
                    alt.Tooltip(
                        "log_date:T",
                        title=translate("Date"),
                        format="%d.%m.%Y",
                    ),
                    alt.Tooltip(
                        "food_calories_in:Q",
                        title=translate("Intake"),
                        format=".0f",
                    ),
                ],
            )
        )

    if not tdee_rows.empty:
        line_base = alt.Chart(tdee_rows).encode(
            x=_daily_x_axis(date_domain),
            y=alt.Y("estimated_tdee:Q", title="kcal"),
            tooltip=[
                alt.Tooltip(
                    "log_date:T",
                    title=translate("Date"),
                    format="%d.%m.%Y",
                ),
                alt.Tooltip("estimated_tdee:Q", title="TDEE", format=".0f"),
            ],
        )
        layers.append(line_base.mark_line(color=TDEE_COLOR, strokeWidth=3))
        layers.append(line_base.mark_circle(color=TDEE_COLOR, size=55))

    chart = alt.layer(*layers).resolve_scale(y="shared").properties(height=280)
    st.altair_chart(_configure_chart(chart), width="stretch")
    st.caption(
        translate(
            "Bars represent days with logged food. The orange line is estimated "
            "TDEE. A missing bar means no food was logged that day."
        )
    )


def _render_balance_chart(data: dict[str, Any]) -> None:
    st.subheader(translate("Estimated calorie balance"))
    daily_rows = _prepare_daily_rows(data.get("daily_rows", pd.DataFrame()))
    date_domain = _date_order_domain(daily_rows)
    if daily_rows.empty or "estimated_balance" not in daily_rows.columns:
        st.info(
            translate(
                "Not enough data is available for the estimated calorie balance."
            )
        )
        return

    chart_rows = daily_rows.dropna(subset=["estimated_balance"]).copy()
    if chart_rows.empty:
        st.info(
            translate("The balance is calculated only for days with logged food.")
        )
        return

    chart_rows["balance_type_id"] = chart_rows["estimated_balance"].apply(
        lambda value: "deficit" if value < 0 else "surplus"
    )
    chart_rows["balance_type_label"] = chart_rows["balance_type_id"].map(
        lambda value: _translate_stable_value(value, BALANCE_TYPE_SOURCE_TEXT)
    )
    bars = (
        alt.Chart(chart_rows)
        .mark_bar()
        .encode(
            x=_daily_x_axis(date_domain),
            y=alt.Y(
                "estimated_balance:Q",
                title="kcal",
                scale=alt.Scale(zero=True),
            ),
            color=alt.Color(
                "balance_type_id:N",
                scale=alt.Scale(
                    domain=["deficit", "surplus"],
                    range=[DEFICIT_COLOR, SURPLUS_COLOR],
                ),
                legend=alt.Legend(
                    title=None,
                    orient="bottom",
                    labelExpr=_legend_label_expression(BALANCE_TYPE_SOURCE_TEXT),
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "log_date:T",
                    title=translate("Date"),
                    format="%d.%m.%Y",
                ),
                alt.Tooltip(
                    "estimated_balance:Q",
                    title=translate("Balance"),
                    format="+.0f",
                ),
                alt.Tooltip(
                    "balance_type_label:N",
                    title=translate("Type"),
                ),
            ],
        )
    )
    zero_line = (
        alt.Chart(pd.DataFrame({"zero": [0]}))
        .mark_rule(color="#111827", strokeWidth=2)
        .encode(y=alt.Y("zero:Q"))
    )
    chart = alt.layer(bars, zero_line).properties(height=260)
    st.altair_chart(_configure_chart(chart), width="stretch")
    st.caption(
        translate(
            "Balance = calories consumed - estimated TDEE. Negative values "
            "indicate a deficit, while positive values indicate a surplus."
        )
    )


def _render_macro_chart(data: dict[str, Any]) -> None:
    st.subheader(translate("Macronutrients"))
    st.caption(
        translate(
            "Macronutrient distribution across protein, carbohydrates, and fats."
        )
    )
    daily_rows = _prepare_daily_rows(data.get("daily_rows", pd.DataFrame()))
    date_domain = _date_order_domain(daily_rows)
    macro_rows = _prepare_macro_rows(data.get("macro_rows", pd.DataFrame()))
    if macro_rows.empty:
        st.info(translate("No food is logged in the selected interval."))
        return

    chart_rows = macro_rows.melt(
        id_vars=["log_date", "date_label", "date_order"],
        value_vars=list(MACRONUTRIENT_SOURCE_TEXT),
        var_name="macronutrient_id",
        value_name="grams",
    )
    chart_rows["macronutrient_label"] = chart_rows["macronutrient_id"].map(
        lambda value: _translate_stable_value(value, MACRONUTRIENT_SOURCE_TEXT)
    )
    chart = (
        alt.Chart(chart_rows)
        .mark_bar()
        .encode(
            x=_daily_x_axis(date_domain),
            y=alt.Y("grams:Q", title=translate("Grams")),
            color=alt.Color(
                "macronutrient_id:N",
                scale=alt.Scale(
                    domain=list(MACRONUTRIENT_SOURCE_TEXT),
                    range=[PROTEIN_COLOR, CARBS_COLOR, FATS_COLOR],
                ),
                legend=alt.Legend(
                    title=None,
                    orient="bottom",
                    labelExpr=_legend_label_expression(MACRONUTRIENT_SOURCE_TEXT),
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "log_date:T",
                    title=translate("Date"),
                    format="%d.%m.%Y",
                ),
                alt.Tooltip(
                    "macronutrient_label:N",
                    title=translate("Macro"),
                ),
                alt.Tooltip(
                    "grams:Q",
                    title=translate("Grams"),
                    format=".1f",
                ),
            ],
        )
        .properties(height=280)
    )
    st.altair_chart(_configure_chart(chart), width="stretch")


def _render_activity_section(data: dict[str, Any]) -> None:
    st.subheader(translate("Physical activity"))
    daily_rows = _prepare_daily_rows(data.get("daily_rows", pd.DataFrame()))
    date_domain = _date_order_domain(daily_rows)
    activity_breakdown = data.get("activity_breakdown", pd.DataFrame())

    if daily_rows.empty:
        st.info(translate("No data is available for the selected interval."))
        return

    chart_rows = daily_rows.copy()
    chart_rows["activity_status_id"] = chart_rows["has_activity_logs"].apply(
        lambda value: "logged" if value else "rest_day"
    )
    chart_rows["activity_status_label"] = chart_rows["activity_status_id"].map(
        lambda value: _translate_stable_value(value, ACTIVITY_STATUS_SOURCE_TEXT)
    )
    chart = (
        alt.Chart(chart_rows)
        .mark_bar(color=ACTIVITY_COLOR, opacity=0.85)
        .encode(
            x=_daily_x_axis(date_domain),
            y=alt.Y("activity_calories_burned:Q", title="kcal"),
            tooltip=[
                alt.Tooltip(
                    "log_date:T",
                    title=translate("Date"),
                    format="%d.%m.%Y",
                ),
                alt.Tooltip(
                    "activity_calories_burned:Q",
                    title=translate("Activity calories"),
                    format=".0f",
                ),
                alt.Tooltip(
                    "activity_status_label:N",
                    title=translate("Status"),
                ),
            ],
        )
        .properties(height=260)
    )
    st.altair_chart(_configure_chart(chart), width="stretch")
    st.caption(
        translate(
            "Days without a workout are shown as 0 kcal burned because they can "
            "represent normal rest days."
        )
    )

    if activity_breakdown.empty:
        st.info(translate("No workouts are logged in the selected interval."))
        return

    st.caption(
        translate(
            "The table below groups workouts by category and calculation method: "
            "MacroSense estimate or manually entered calories."
        )
    )
    method_rows = activity_breakdown.copy()
    if "category" in method_rows.columns:
        method_rows["category"] = method_rows["category"].map(
            _format_activity_category
        )
    if "calculation_method" in method_rows.columns:
        method_rows["calculation_method"] = method_rows[
            "calculation_method"
        ].map(_format_activity_method)
    st.dataframe(
        method_rows,
        hide_index=True,
        width="stretch",
        column_config={
            "category": st.column_config.TextColumn(translate("Category")),
            "calculation_method": st.column_config.TextColumn(translate("Method")),
            "entries_count": st.column_config.NumberColumn(translate("Entries")),
            "total_duration_min": st.column_config.NumberColumn(
                translate("Total duration (min)"),
                format="%.1f",
            ),
            "total_calories_burned": st.column_config.NumberColumn(
                translate("Activity calories"),
                format="%.1f kcal",
            ),
        },
    )


def _prepare_weight_rows(weight_rows: pd.DataFrame) -> pd.DataFrame:
    if weight_rows.empty:
        return pd.DataFrame()
    chart_rows = weight_rows.copy()
    chart_rows["log_date"] = pd.to_datetime(chart_rows["log_date"])
    chart_rows = _add_date_display_columns(chart_rows)
    chart_rows["weight_kg"] = pd.to_numeric(chart_rows["weight_kg"], errors="coerce")
    return chart_rows.dropna(subset=["log_date", "weight_kg"])


def _prepare_daily_weight_rows(daily_rows: pd.DataFrame) -> pd.DataFrame:
    if daily_rows.empty or "reference_weight_kg" not in daily_rows.columns:
        return pd.DataFrame()
    chart_rows = daily_rows.copy()
    chart_rows["log_date"] = pd.to_datetime(chart_rows["log_date"])
    chart_rows = _add_date_display_columns(chart_rows)
    chart_rows["reference_weight_kg"] = pd.to_numeric(
        chart_rows["reference_weight_kg"], errors="coerce"
    )
    if "reference_weight_days_distance" in chart_rows.columns:
        chart_rows["reference_weight_days_distance"] = pd.to_numeric(
            chart_rows["reference_weight_days_distance"], errors="coerce"
        )
    else:
        chart_rows["reference_weight_days_distance"] = None
    chart_rows["reference_weight_source_id"] = chart_rows.apply(
        _reference_weight_source_id,
        axis=1,
    )
    return chart_rows.dropna(subset=["log_date", "reference_weight_kg"])


def _reference_weight_source_id(row: pd.Series) -> str:
    if pd.isna(row.get("reference_weight_kg")):
        return "missing"
    if row.get("reference_weight_days_distance") == 0:
        return "actual"
    if bool(row.get("reference_weight_uses_future_reference")):
        return "future_fallback"
    return "previous"


def _format_reference_weight_source(source_id: str) -> str:
    return _translate_stable_value(source_id, REFERENCE_WEIGHT_SOURCE_TEXT)


def _translate_stable_value(
    value: Any,
    source_text_by_value: dict[str, str],
) -> str:
    stable_value = str(value)
    source_text = source_text_by_value.get(stable_value)
    if source_text is None:
        return _format_text(value)
    return translate(source_text)


def _legend_label_expression(source_text_by_id: dict[str, str]) -> str:
    expression = "datum.label"
    for stable_id, source_text in reversed(list(source_text_by_id.items())):
        translated_label = translate(source_text)
        expression = (
            f"datum.label == {json.dumps(stable_id)} ? "
            f"{json.dumps(translated_label, ensure_ascii=False)} : ({expression})"
        )
    return expression


def _format_activity_category(value: Any) -> str:
    return _translate_stable_value(value, ACTIVITY_CATEGORY_SOURCE_TEXT)


def _format_activity_method(value: Any) -> str:
    return _translate_stable_value(value, ACTIVITY_METHOD_SOURCE_TEXT)


def _prepare_daily_rows(daily_rows: pd.DataFrame) -> pd.DataFrame:
    if daily_rows.empty:
        return pd.DataFrame()
    chart_rows = daily_rows.copy()
    chart_rows["log_date"] = pd.to_datetime(chart_rows["log_date"])
    chart_rows = _add_date_display_columns(chart_rows)
    chart_rows["food_calories_in"] = pd.to_numeric(
        chart_rows["food_calories_in"], errors="coerce"
    )
    chart_rows["estimated_tdee"] = pd.to_numeric(
        chart_rows["estimated_tdee"], errors="coerce"
    )
    chart_rows["estimated_balance"] = pd.to_numeric(
        chart_rows["estimated_balance"], errors="coerce"
    )
    chart_rows["activity_calories_burned"] = pd.to_numeric(
        chart_rows["activity_calories_burned"], errors="coerce"
    ).fillna(0.0)
    return chart_rows


def _prepare_macro_rows(macro_rows: pd.DataFrame) -> pd.DataFrame:
    if macro_rows.empty:
        return pd.DataFrame()
    chart_rows = macro_rows.copy()
    chart_rows["log_date"] = pd.to_datetime(chart_rows["log_date"])
    chart_rows = _add_date_display_columns(chart_rows)
    chart_rows["protein_g"] = pd.to_numeric(chart_rows["protein_g"], errors="coerce")
    chart_rows["carbs_g"] = pd.to_numeric(chart_rows["carbs_g"], errors="coerce")
    chart_rows["fats_g"] = pd.to_numeric(chart_rows["fats_g"], errors="coerce")
    return chart_rows.dropna(subset=["log_date"])


def _add_date_display_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    chart_rows = dataframe.copy()
    chart_rows["date_label"] = chart_rows["log_date"].dt.strftime("%d.%m")
    chart_rows["date_order"] = chart_rows["log_date"].dt.strftime("%Y-%m-%d")
    return chart_rows


def _date_order_domain(dataframe: pd.DataFrame) -> list[str] | None:
    if dataframe.empty or "date_order" not in dataframe.columns:
        return None
    domain = dataframe["date_order"].dropna().astype(str).drop_duplicates().tolist()
    return domain or None


def _daily_x_axis(domain: list[str] | None = None) -> alt.X:
    scale = alt.Scale(domain=domain) if domain else alt.Undefined
    return alt.X(
        "date_order:N",
        title=translate("Date"),
        scale=scale,
        axis=alt.Axis(
            labelAngle=0,
            labelExpr="substring(datum.label, 8, 10) + '.' + substring(datum.label, 5, 7)",
            labelOverlap=True,
        ),
    )


def _configure_chart(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure_axis(labelFontSize=12, titleFontSize=12)
        .configure_legend(labelFontSize=12, titleFontSize=12)
        .configure_view(strokeWidth=0)
    )


def _calculate_interval_weight_delta(weight_rows: pd.DataFrame | None) -> float | None:
    prepared_rows = _prepare_weight_rows(
        weight_rows if weight_rows is not None else pd.DataFrame()
    )
    if prepared_rows.shape[0] < 2:
        return None
    first_weight = float(prepared_rows.iloc[0]["weight_kg"])
    last_weight = float(prepared_rows.iloc[-1]["weight_kg"])
    return round(last_weight - first_weight, 2)


def _calculate_interval_weight_delta_from_daily(
    daily_rows: pd.DataFrame | None,
) -> float | None:
    prepared_rows = _prepare_daily_weight_rows(
        daily_rows if daily_rows is not None else pd.DataFrame()
    )
    if prepared_rows.shape[0] < 2:
        return None
    first_weight = float(prepared_rows.iloc[0]["reference_weight_kg"])
    last_weight = float(prepared_rows.iloc[-1]["reference_weight_kg"])
    return round(last_weight - first_weight, 2)


def _format_kcal(value: Any) -> str:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return "—"
    return f"{numeric_value:.0f} kcal"


def _format_kcal_zero(value: Any) -> str:
    numeric_value = _as_float(value)
    if numeric_value is None:
        numeric_value = 0.0
    return f"{numeric_value:.0f} kcal"


def _format_kcal_or_missing(value: Any) -> str:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return translate("Not logged")
    return f"{numeric_value:.0f} kcal"


def _format_signed_kcal(value: Any) -> str:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return "—"
    return f"{numeric_value:+.0f} kcal"


def _format_kg(value: Any) -> str:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return "—"
    return f"{numeric_value:.1f} kg"


def _format_kg_delta(value: Any) -> str | None:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return None
    return f"{numeric_value:+.1f} kg"


def _format_cm(value: Any) -> str:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return "—"
    return f"{numeric_value:.0f} cm"


def _format_age(value: Any) -> str:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return "—"
    return translate("{age:.0f} years", age=numeric_value)


def _format_gender(value: Any) -> str:
    if value == "M":
        return "M"
    if value == "F":
        return "F"
    return "—"


def _format_goal(value: Any) -> str:
    goal_key = _normalize_goal(value)
    source_labels = {
        "slabire": "Weight loss",
        "mentinere": "Maintenance",
        "masa_musculara": "Muscle gain",
        "crestere": "Muscle gain",
    }
    source_label = source_labels.get(goal_key)
    if source_label is None:
        return _format_text(value)
    return translate(source_label)


def _goal_description(value: Any) -> str | None:
    goal_key = _normalize_goal(value)
    source_descriptions = {
        "slabire": "Focus on a controlled calorie deficit.",
        "mentinere": "Focus on weight stability.",
        "masa_musculara": (
            "Focus on a controlled surplus, protein, and strength training."
        ),
        "crestere": (
            "Focus on a controlled surplus, protein, and strength training."
        ),
    }
    source_description = source_descriptions.get(goal_key)
    if source_description is None:
        return None
    return translate(source_description)


def _normalize_goal(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    replacements = {
        "ă": "a",
        "â": "a",
        "î": "i",
        "ș": "s",
        "ş": "s",
        "ț": "t",
        "ţ": "t",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = text.replace(" ", "_").replace("-", "_")
    return text


def _format_text(value: Any) -> str:
    if value is None or str(value).strip() == "":
        return "—"
    return str(value)


def _format_percent(value: Any) -> str:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return "—"
    return f"{numeric_value:.1f}%"


def _format_number(value: Any, suffix: str = "") -> str:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return "—"
    return f"{numeric_value:.1f}{suffix}"


def _format_date(value: Any) -> str:
    if value is None:
        return "—"
    try:
        date_value = value.date() if isinstance(value, datetime) else value
        if not isinstance(date_value, date):
            date_value = pd.to_datetime(value).date()
    except (TypeError, ValueError):
        return "—"
    return date_value.strftime("%d.%m.%Y")


def _to_date(value: Any) -> date:
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.to_datetime(value).date()


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric_value):
        return None
    return numeric_value
