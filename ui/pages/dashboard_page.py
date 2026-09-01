from __future__ import annotations

from datetime import date, datetime
from html import escape
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
from ui.language import translate


INTERVAL_OPTIONS = {
    "7 zile": 7,
    "30 zile": 30,
    "90 zile": 90,
}
DEFAULT_INTERVAL_LABEL = "30 zile"
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


def render_dashboard_page() -> None:
    st.title(f"🏠 {translate('Home')}")
    st.caption(
        translate(
            "The dashboard is read-only. TDEE and calorie balance values are "
            "estimates calculated from your profile, weight, and journals."
        )
    )

    selected_interval = _resolve_interval_label(
        st.session_state.get(DASHBOARD_INTERVAL_KEY)
    )
    days = INTERVAL_OPTIONS.get(selected_interval, 30)

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
    st.subheader("Evoluție pe interval")
    st.radio(
        "Interval analiză",
        list(INTERVAL_OPTIONS.keys()),
        index=list(INTERVAL_OPTIONS.keys()).index(selected_interval),
        horizontal=True,
        key=DASHBOARD_INTERVAL_KEY,
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
    st.subheader("Predicție greutate")

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
            "Predicția ML nu este disponibilă momentan. Verifică modelele "
            "antrenate și conexiunea la baza de date."
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
            "Predicția apare după ce există suficiente alimente, cântăriri și "
            "modele ML antrenate pentru utilizatorul curent."
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
            label = f"Peste {horizon_days} zile"
            if uses_fallback_date:
                label = (
                    f"Peste {horizon_days} zile de la "
                    f"{_format_date(prediction.analysis_date)}"
                )
            cards.append(
                {
                    "label": label,
                    "value": _format_kg(prediction.predicted_weight_kg),
                    "caption": (
                        "Schimbare estimată: "
                        f"{_format_kg_delta(prediction.predicted_change_kg) or '—'} | "
                        f"Data: {_format_date(prediction.target_date)} | "
                        f"MAE: {_format_prediction_error(prediction.metrics.get('mae'))}"
                    ),
                    "accent": "prediction",
                    "help": (
                        "Predicție ML calculată din istoricul de "
                        "alimente, activități și greutate, fără date din viitor."
                    ),
                }
            )
            continue

        reason = prediction_result.unavailable_horizons.get(
            horizon_days,
            "Nu există suficiente date pentru acest interval.",
        )
        cards.append(
            {
                "label": f"Peste {horizon_days} zile",
                "value": "Indisponibil",
                "caption": _format_prediction_unavailable_reason(reason),
                "accent": "prediction",
                "help": "Predicția devine disponibilă după ce există date suficiente.",
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
        return (
            "Predicție calculată din datele disponibile până la "
            f"{_format_date(actual_date)}."
        )
    if requested_date == current_date:
        return (
            f"Predicția pornește de la {_format_date(actual_date)}, ultima zi "
            "cu date suficiente. Ziua curentă este evitată pentru că poate fi "
            "incompletă."
        )
    return (
        f"Predicția pornește de la {_format_date(actual_date)}, deoarece pentru "
        f"{_format_date(requested_date)} nu există suficiente date recente."
    )


def _format_prediction_error(value: Any) -> str:
    numeric_value = _as_float(value)
    if numeric_value is None:
        return "—"
    return f"{numeric_value:.2f} kg"


def _format_prediction_unavailable_reason(reason: str) -> str:
    if "Missing model artifact" in reason or "Missing metadata artifact" in reason:
        return "Modelele ML nu au fost antrenate încă."
    return reason


def _resolve_interval_label(value: Any) -> str:
    if value in INTERVAL_OPTIONS:
        return str(value)
    return DEFAULT_INTERVAL_LABEL


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
                "label": "Trend greutate interval",
                "value": _format_kg_delta(interval_weight_delta) or "—",
                "accent": "weight",
                "help": (
                    "Diferența dintre greutatea de referință din ultima zi a "
                    "intervalului și prima zi a intervalului. Nu înseamnă că ai "
                    "avut cântărire reală în fiecare zi."
                ),
            },
            {
                "label": "Consum mediu / zi logată",
                "value": _format_kcal(summary.get("avg_calories_in")),
                "accent": "food",
                "help": (
                    "Media caloriilor consumate doar pe zilele cu alimente "
                    "logate. Zilele fără alimente nu sunt tratate ca 0 kcal."
                ),
            },
            {
                "label": "TDEE mediu / zi alimentară",
                "value": _format_kcal(summary.get("avg_estimated_tdee")),
                "accent": "energy",
                "help": (
                    "Media TDEE-ului estimat doar pentru zilele cu alimentație "
                    "logată, ca să fie comparabil cu consumul alimentar."
                ),
            },
            {
                "label": "Balanță medie / zi alimentară",
                "value": _format_signed_kcal(summary.get("avg_estimated_balance")),
                "accent": "balance",
                "help": (
                    "Media valorilor zilnice calorii consumate - TDEE estimat, "
                    "calculată doar pe zilele cu alimente logate."
                ),
            },
        ],
        columns_count=4,
    )

    _render_card_grid(
        [
            {
                "label": "Consistență alimente",
                "value": _format_percent(summary.get("food_logging_consistency")),
                "caption": f"{summary.get('food_days', 0)} / {days} zile",
                "accent": "food",
                "help": "Procentul de zile din interval cu cel puțin un aliment logat.",
            },
            {
                "label": "Consistență antrenamente",
                "value": _format_percent(summary.get("activity_logging_consistency")),
                "caption": f"{summary.get('activity_days', 0)} / {days} zile",
                "accent": "activity",
                "help": "Procentul de zile din interval cu cel puțin un antrenament logat.",
            },
            {
                "label": "Consistență greutate",
                "value": _format_percent(summary.get("weight_logging_consistency")),
                "caption": f"{summary.get('weight_days', 0)} / {days} zile",
                "accent": "weight",
                "help": "Procentul de zile din interval cu o cântărire introdusă efectiv.",
            },
            {
                "label": "Consistență generală",
                "value": _format_percent(summary.get("overall_logging_consistency")),
                "caption": f"{summary.get('logged_days', 0)} / {days} zile",
                "accent": "quality",
                "help": (
                    "Procentul de zile din interval în care există alimente, "
                    "antrenament sau cântărire reală."
                ),
            },
        ],
        columns_count=4,
    )

    _render_card_grid(
        [
            {
                "label": "Calorii activități totale",
                "value": _format_kcal_zero(summary.get("activity_total_calories")),
                "accent": "activity",
                "help": "Totalul caloriilor arse prin antrenamente în intervalul selectat.",
            },
            {
                "label": "Înregistrări exerciții",
                "value": str(summary.get("workouts_count", 0)),
                "accent": "activity",
                "help": (
                    "Numărul total de exerciții/antrenamente logate în interval. "
                    "O singură zi poate avea mai multe înregistrări."
                ),
            },
            {
                "label": "Proteină medie",
                "value": _format_number(summary.get("avg_protein_g"), " g"),
                "accent": "food",
                "help": "Media proteinelor consumate pe zilele cu alimente logate.",
            },
            {
                "label": "Proteină / kg corp",
                "value": _format_number(summary.get("avg_protein_per_kg"), " g/kg"),
                "accent": "health",
                "help": (
                    "Media proteinelor zilnice împărțită la greutatea de referință "
                    "a zilei. Va fi utilă pentru recomandările alimentare."
                ),
            },
        ],
        columns_count=4,
    )

    if not summary.get("has_energy_estimates"):
        st.info(
            "Adaugă cel puțin o greutate pentru a putea calcula BMR, TDEE și "
            "balanța calorică estimată."
        )


def _render_weight_chart(data: dict[str, Any]) -> None:
    st.subheader("Evoluția greutății")
    reference_rows = _prepare_daily_weight_rows(data.get("daily_rows", pd.DataFrame()))
    actual_rows = _prepare_weight_rows(data.get("weight_rows", pd.DataFrame()))
    date_domain = _date_order_domain(reference_rows)
    if reference_rows.empty:
        st.info("Nu există greutate de referință pentru intervalul selectat.")
        return

    base = alt.Chart(reference_rows).encode(
        x=_daily_x_axis(date_domain),
        y=alt.Y(
            "Greutate (kg):Q",
            title="Greutate (kg)",
            scale=alt.Scale(zero=False),
        ),
        tooltip=[
            alt.Tooltip("Data:T", title="Data", format="%d.%m.%Y"),
            alt.Tooltip("Greutate (kg):Q", title="Greutate de referință", format=".1f"),
            alt.Tooltip("Sursă referință:N", title="Sursă"),
            alt.Tooltip("Distanță zile:Q", title="Distanță zile"),
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
            y=alt.Y("Greutate (kg):Q", title="Greutate (kg)", scale=alt.Scale(zero=False)),
            tooltip=[
                alt.Tooltip("Data:T", title="Cântărire reală", format="%d.%m.%Y"),
                alt.Tooltip("Greutate (kg):Q", title="Greutate", format=".1f"),
            ],
        )
        layers.append(actual_points)

    chart = alt.layer(*layers).properties(height=260)
    st.altair_chart(_configure_chart(chart), width="stretch")
    st.caption(
        "Linia arată greutatea de referință pentru fiecare zi. Punctele negre "
        "marchează zilele în care ai introdus efectiv o cântărire."
    )


def _render_calorie_chart(data: dict[str, Any]) -> None:
    st.subheader("Calorii consumate vs TDEE estimat")
    daily_rows = _prepare_daily_rows(data.get("daily_rows", pd.DataFrame()))
    date_domain = _date_order_domain(daily_rows)
    if daily_rows.empty:
        st.info("Nu există date în intervalul selectat.")
        return

    food_rows = daily_rows[daily_rows["has_food_logs"]].dropna(
        subset=["Calorii consumate"]
    )
    tdee_rows = daily_rows.dropna(subset=["TDEE estimat"])
    if food_rows.empty and tdee_rows.empty:
        st.info("Nu există suficiente date pentru graficul caloric.")
        return

    layers = []
    if not food_rows.empty:
        layers.append(
            alt.Chart(food_rows)
            .mark_bar(color=FOOD_COLOR, opacity=0.8)
            .encode(
                x=_daily_x_axis(date_domain),
                y=alt.Y("Calorii consumate:Q", title="kcal"),
                tooltip=[
                    alt.Tooltip("Data:T", title="Data", format="%d.%m.%Y"),
                    alt.Tooltip("Calorii consumate:Q", title="Consum", format=".0f"),
                ],
            )
        )

    if not tdee_rows.empty:
        line_base = alt.Chart(tdee_rows).encode(
            x=_daily_x_axis(date_domain),
            y=alt.Y("TDEE estimat:Q", title="kcal"),
            tooltip=[
                alt.Tooltip("Data:T", title="Data", format="%d.%m.%Y"),
                alt.Tooltip("TDEE estimat:Q", title="TDEE", format=".0f"),
            ],
        )
        layers.append(line_base.mark_line(color=TDEE_COLOR, strokeWidth=3))
        layers.append(line_base.mark_circle(color=TDEE_COLOR, size=55))

    chart = alt.layer(*layers).resolve_scale(y="shared").properties(height=280)
    st.altair_chart(_configure_chart(chart), width="stretch")
    st.caption(
        "Barele sunt zile cu alimente logate. Linia portocalie este TDEE-ul "
        "estimat. Lipsa unei bare înseamnă zi fără alimente logate."
    )


def _render_balance_chart(data: dict[str, Any]) -> None:
    st.subheader("Balanță calorică estimată")
    daily_rows = _prepare_daily_rows(data.get("daily_rows", pd.DataFrame()))
    date_domain = _date_order_domain(daily_rows)
    if daily_rows.empty or "Balanță kcal" not in daily_rows.columns:
        st.info("Nu există suficiente date pentru balanța calorică estimată.")
        return

    chart_rows = daily_rows.dropna(subset=["Balanță kcal"]).copy()
    if chart_rows.empty:
        st.info("Balanța se calculează doar pentru zilele cu alimentație logată.")
        return

    chart_rows["Tip"] = chart_rows["Balanță kcal"].apply(
        lambda value: "Deficit" if value < 0 else "Surplus"
    )
    bars = (
        alt.Chart(chart_rows)
        .mark_bar()
        .encode(
            x=_daily_x_axis(date_domain),
            y=alt.Y("Balanță kcal:Q", title="kcal", scale=alt.Scale(zero=True)),
            color=alt.Color(
                "Tip:N",
                scale=alt.Scale(
                    domain=["Deficit", "Surplus"],
                    range=[DEFICIT_COLOR, SURPLUS_COLOR],
                ),
                legend=alt.Legend(title=None, orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Data:T", title="Data", format="%d.%m.%Y"),
                alt.Tooltip("Balanță kcal:Q", title="Balanță", format="+.0f"),
                alt.Tooltip("Tip:N", title="Tip"),
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
        "Balanță = calorii consumate - TDEE estimat. Valorile negative indică "
        "deficit, iar cele pozitive indică surplus."
    )


def _render_macro_chart(data: dict[str, Any]) -> None:
    st.subheader("Macronutrienți")
    st.caption(
        "Distribuția macronutrienților pe proteine, carbohidrați și grăsimi."
    )
    daily_rows = _prepare_daily_rows(data.get("daily_rows", pd.DataFrame()))
    date_domain = _date_order_domain(daily_rows)
    macro_rows = _prepare_macro_rows(data.get("macro_rows", pd.DataFrame()))
    if macro_rows.empty:
        st.info("Nu există alimente logate în intervalul selectat.")
        return

    chart_rows = macro_rows.melt(
        id_vars=["Data", "DataLabel", "DataOrder"],
        value_vars=["Proteine", "Carbohidrați", "Grăsimi"],
        var_name="Macronutrient",
        value_name="Grame",
    )
    chart = (
        alt.Chart(chart_rows)
        .mark_bar()
        .encode(
            x=_daily_x_axis(date_domain),
            y=alt.Y("Grame:Q", title="Grame"),
            color=alt.Color(
                "Macronutrient:N",
                scale=alt.Scale(
                    domain=["Proteine", "Carbohidrați", "Grăsimi"],
                    range=[PROTEIN_COLOR, CARBS_COLOR, FATS_COLOR],
                ),
                legend=alt.Legend(title=None, orient="bottom"),
            ),
            tooltip=[
                alt.Tooltip("Data:T", title="Data", format="%d.%m.%Y"),
                alt.Tooltip("Macronutrient:N", title="Macro"),
                alt.Tooltip("Grame:Q", title="Grame", format=".1f"),
            ],
        )
        .properties(height=280)
    )
    st.altair_chart(_configure_chart(chart), width="stretch")


def _render_activity_section(data: dict[str, Any]) -> None:
    st.subheader("Activitate fizică")
    daily_rows = _prepare_daily_rows(data.get("daily_rows", pd.DataFrame()))
    date_domain = _date_order_domain(daily_rows)
    activity_breakdown = data.get("activity_breakdown", pd.DataFrame())

    if daily_rows.empty:
        st.info("Nu există date în intervalul selectat.")
        return

    chart_rows = daily_rows.copy()
    chart_rows["Status"] = chart_rows["has_activity_logs"].apply(
        lambda value: "Antrenament logat" if value else "Zi fără antrenament"
    )
    chart = (
        alt.Chart(chart_rows)
        .mark_bar(color=ACTIVITY_COLOR, opacity=0.85)
        .encode(
            x=_daily_x_axis(date_domain),
            y=alt.Y("Calorii activități:Q", title="kcal"),
            tooltip=[
                alt.Tooltip("Data:T", title="Data", format="%d.%m.%Y"),
                alt.Tooltip("Calorii activități:Q", title="Calorii activități", format=".0f"),
                alt.Tooltip("Status:N", title="Status"),
            ],
        )
        .properties(height=260)
    )
    st.altair_chart(_configure_chart(chart), width="stretch")
    st.caption(
        "Zilele fără antrenament sunt afișate ca 0 kcal arse, pentru că pot "
        "reprezenta zile normale de repaus."
    )

    if activity_breakdown.empty:
        st.info("Nu există antrenamente logate în intervalul selectat.")
        return

    st.caption(
        "Tabelul de mai jos grupează antrenamentele după categorie și metoda de "
        "calcul: estimare MacroSense sau calorii introduse manual."
    )
    method_rows = activity_breakdown.rename(
        columns={
            "category": "Categorie",
            "calculation_method": "Metodă",
            "entries_count": "Înregistrări",
            "total_duration_min": "Durată totală (min)",
            "total_calories_burned": "Calorii activități",
        }
    )
    st.dataframe(
        method_rows,
        hide_index=True,
        width="stretch",
        column_config={
            "Durată totală (min)": st.column_config.NumberColumn(format="%.1f"),
            "Calorii activități": st.column_config.NumberColumn(format="%.1f kcal"),
        },
    )


def _prepare_weight_rows(weight_rows: pd.DataFrame) -> pd.DataFrame:
    if weight_rows.empty:
        return pd.DataFrame()
    chart_rows = weight_rows.copy()
    chart_rows["Data"] = pd.to_datetime(chart_rows["log_date"])
    chart_rows = _add_date_display_columns(chart_rows)
    chart_rows["Greutate (kg)"] = pd.to_numeric(
        chart_rows["weight_kg"], errors="coerce"
    )
    return chart_rows.dropna(subset=["Data", "Greutate (kg)"])


def _prepare_daily_weight_rows(daily_rows: pd.DataFrame) -> pd.DataFrame:
    if daily_rows.empty or "reference_weight_kg" not in daily_rows.columns:
        return pd.DataFrame()
    chart_rows = daily_rows.copy()
    chart_rows["Data"] = pd.to_datetime(chart_rows["log_date"])
    chart_rows = _add_date_display_columns(chart_rows)
    chart_rows["Greutate (kg)"] = pd.to_numeric(
        chart_rows["reference_weight_kg"], errors="coerce"
    )
    if "reference_weight_days_distance" in chart_rows.columns:
        chart_rows["Distanță zile"] = pd.to_numeric(
            chart_rows["reference_weight_days_distance"], errors="coerce"
        )
    else:
        chart_rows["Distanță zile"] = None
    chart_rows["Sursă referință"] = chart_rows.apply(
        _format_reference_weight_source, axis=1
    )
    return chart_rows.dropna(subset=["Data", "Greutate (kg)"])


def _format_reference_weight_source(row: pd.Series) -> str:
    if pd.isna(row.get("reference_weight_kg")):
        return "Fără greutate"
    if row.get("reference_weight_days_distance") == 0:
        return "Cântărire reală"
    if bool(row.get("reference_weight_uses_future_reference")):
        return "Fallback din prima greutate viitoare"
    return "Greutate anterioară folosită ca referință"


def _prepare_daily_rows(daily_rows: pd.DataFrame) -> pd.DataFrame:
    if daily_rows.empty:
        return pd.DataFrame()
    chart_rows = daily_rows.copy()
    chart_rows["Data"] = pd.to_datetime(chart_rows["log_date"])
    chart_rows = _add_date_display_columns(chart_rows)
    chart_rows["Calorii consumate"] = pd.to_numeric(
        chart_rows["food_calories_in"], errors="coerce"
    )
    chart_rows["TDEE estimat"] = pd.to_numeric(
        chart_rows["estimated_tdee"], errors="coerce"
    )
    chart_rows["Balanță kcal"] = pd.to_numeric(
        chart_rows["estimated_balance"], errors="coerce"
    )
    chart_rows["Calorii activități"] = pd.to_numeric(
        chart_rows["activity_calories_burned"], errors="coerce"
    ).fillna(0.0)
    return chart_rows


def _prepare_macro_rows(macro_rows: pd.DataFrame) -> pd.DataFrame:
    if macro_rows.empty:
        return pd.DataFrame()
    chart_rows = macro_rows.copy()
    chart_rows["Data"] = pd.to_datetime(chart_rows["log_date"])
    chart_rows = _add_date_display_columns(chart_rows)
    chart_rows["Proteine"] = pd.to_numeric(chart_rows["protein_g"], errors="coerce")
    chart_rows["Carbohidrați"] = pd.to_numeric(chart_rows["carbs_g"], errors="coerce")
    chart_rows["Grăsimi"] = pd.to_numeric(chart_rows["fats_g"], errors="coerce")
    return chart_rows.dropna(subset=["Data"])


def _add_date_display_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    chart_rows = dataframe.copy()
    chart_rows["DataLabel"] = chart_rows["Data"].dt.strftime("%d.%m")
    chart_rows["DataOrder"] = chart_rows["Data"].dt.strftime("%Y-%m-%d")
    return chart_rows


def _date_order_domain(dataframe: pd.DataFrame) -> list[str] | None:
    if dataframe.empty or "DataOrder" not in dataframe.columns:
        return None
    domain = dataframe["DataOrder"].dropna().astype(str).drop_duplicates().tolist()
    return domain or None


def _daily_x_axis(domain: list[str] | None = None) -> alt.X:
    scale = alt.Scale(domain=domain) if domain else alt.Undefined
    return alt.X(
        "DataOrder:N",
        title="Data",
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
    first_weight = float(prepared_rows.iloc[0]["Greutate (kg)"])
    last_weight = float(prepared_rows.iloc[-1]["Greutate (kg)"])
    return round(last_weight - first_weight, 2)


def _calculate_interval_weight_delta_from_daily(
    daily_rows: pd.DataFrame | None,
) -> float | None:
    prepared_rows = _prepare_daily_weight_rows(
        daily_rows if daily_rows is not None else pd.DataFrame()
    )
    if prepared_rows.shape[0] < 2:
        return None
    first_weight = float(prepared_rows.iloc[0]["Greutate (kg)"])
    last_weight = float(prepared_rows.iloc[-1]["Greutate (kg)"])
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
