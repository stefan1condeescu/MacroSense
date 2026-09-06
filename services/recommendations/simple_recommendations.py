"""Simple explainable recommendation cards for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from services.ml.prediction import UserWeightPredictions


RECOMMENDATION_DAYS = 14
MIN_FOOD_DAYS = 5
MIN_ACTIVITY_DAYS_FOR_JUDGEMENT = 3
MIN_WEIGHT_DAYS = 2


@dataclass(frozen=True)
class RecommendationCard:
    """Small recommendation card rendered by the dashboard."""

    category: str
    status: str
    message: str
    accent: str


@dataclass(frozen=True)
class RecommendationContext:
    """Compact recommendation input built from dashboard and ML data."""

    goal: str | None
    days: int
    food_days: int
    activity_days: int
    weight_days: int
    workouts_count: int
    avg_estimated_balance: float | None
    avg_protein_per_kg: float | None
    avg_activity_calories_per_active_day: float | None
    activity_total_calories: float | None
    current_weight_kg: float | None
    current_bmi: float | None
    interval_weight_delta_kg: float | None
    predicted_change_kg: float | None
    predicted_horizon_days: int | None


def build_recommendation_context(
    dashboard_data: dict[str, Any],
    prediction_result: UserWeightPredictions | None = None,
) -> RecommendationContext:
    """Build the compact context used by the recommendation rules."""

    summary = dashboard_data.get("summary", {}) or {}
    current = dashboard_data.get("current", {}) or {}
    days = int(dashboard_data.get("days") or RECOMMENDATION_DAYS)
    activity_days = int(summary.get("activity_days") or 0)
    activity_total = _optional_float(summary.get("activity_total_calories"))
    avg_activity_per_active_day = (
        round(activity_total / activity_days, 2)
        if activity_total is not None and activity_days > 0
        else None
    )
    predicted_change, predicted_horizon = _select_prediction_signal(prediction_result)

    return RecommendationContext(
        goal=summary.get("goal") or current.get("goal"),
        days=days,
        food_days=int(summary.get("food_days") or 0),
        activity_days=activity_days,
        weight_days=int(summary.get("weight_days") or 0),
        workouts_count=int(summary.get("workouts_count") or 0),
        avg_estimated_balance=_optional_float(summary.get("avg_estimated_balance")),
        avg_protein_per_kg=_optional_float(summary.get("avg_protein_per_kg")),
        avg_activity_calories_per_active_day=avg_activity_per_active_day,
        activity_total_calories=activity_total,
        current_weight_kg=_optional_float(current.get("current_weight_kg")),
        current_bmi=_optional_float(current.get("current_bmi")),
        interval_weight_delta_kg=_calculate_interval_weight_delta(
            dashboard_data.get("daily_rows", pd.DataFrame())
        ),
        predicted_change_kg=predicted_change,
        predicted_horizon_days=predicted_horizon,
    )


def build_recommendation_cards(
    context: RecommendationContext,
) -> list[RecommendationCard]:
    """Return the four fixed dashboard recommendation cards."""

    return [
        _build_meal_card(context),
        _build_protein_card(context),
        _build_activity_card(context),
        _build_progress_card(context),
    ]


def build_dashboard_recommendation_cards(
    dashboard_data: dict[str, Any],
    prediction_result: UserWeightPredictions | None = None,
) -> list[RecommendationCard]:
    """Build recommendation cards directly from dashboard and prediction data."""

    context = build_recommendation_context(dashboard_data, prediction_result)
    return build_recommendation_cards(context)


def _build_meal_card(context: RecommendationContext) -> RecommendationCard:
    if context.food_days < MIN_FOOD_DAYS or context.avg_estimated_balance is None:
        return RecommendationCard(
            "Meals",
            "Not enough data",
            "Log meals more often.",
            "quality",
        )

    goal = _normalize_goal(context.goal)
    balance = context.avg_estimated_balance

    if goal == "slabire":
        if balance < -900:
            return RecommendationCard(
                "Meals", "Too little food", "Eat a little more.", "energy"
            )
        if balance > -150:
            return RecommendationCard(
                "Meals",
                "Meals too heavy",
                "Choose slightly lighter portions.",
                "balance",
            )
        return RecommendationCard(
            "Meals", "Meals on track", "Your meals support weight loss.", "food"
        )

    if goal == "crestere":
        if balance < 150:
            return RecommendationCard(
                "Meals",
                "Too little food",
                "Eat a little more.",
                "energy",
            )
        if balance > 800:
            return RecommendationCard(
                "Meals",
                "Meals too heavy",
                "Increase your intake more gradually.",
                "balance",
            )
        return RecommendationCard(
            "Meals", "Meals on track", "Your meals support weight gain.", "food"
        )

    if balance < -350:
        return RecommendationCard(
            "Meals", "Too little food", "Eat a little more.", "energy"
        )
    if balance > 350:
        return RecommendationCard(
            "Meals",
            "Meals too heavy",
            "Choose slightly lighter portions.",
            "balance",
        )
    return RecommendationCard(
        "Meals", "Meals on track", "Your meals support maintenance.", "food"
    )


def _build_protein_card(context: RecommendationContext) -> RecommendationCard:
    if context.food_days < MIN_FOOD_DAYS or context.avg_protein_per_kg is None:
        return RecommendationCard(
            "Protein",
            "Not enough data",
            "Log meals more often.",
            "quality",
        )

    threshold = _protein_threshold_for_context(context)
    if context.avg_protein_per_kg < threshold:
        return RecommendationCard(
            "Protein",
            "Low protein",
            "Add a protein source.",
            "food",
        )
    return RecommendationCard(
        "Protein",
        "Enough protein",
        "Your protein intake looks good.",
        "health",
    )


def _build_activity_card(context: RecommendationContext) -> RecommendationCard:
    activity_total = context.activity_total_calories or 0.0
    avg_active_day = context.avg_activity_calories_per_active_day or 0.0

    if (
        context.food_days < MIN_FOOD_DAYS
        and context.activity_days < MIN_ACTIVITY_DAYS_FOR_JUDGEMENT
    ):
        return RecommendationCard(
            "Movement",
            "Not enough data",
            "Log activities more often.",
            "quality",
        )

    if _has_excessive_activity_volume(context):
        return RecommendationCard(
            "Movement",
            "Training load too high",
            "Include rest days too.",
            "activity",
        )

    if context.activity_days <= 2 and avg_active_day >= 650:
        return RecommendationCard(
            "Movement",
            "Intense activity",
            "You logged demanding activities.",
            "activity",
        )

    if (
        context.activity_days < MIN_ACTIVITY_DAYS_FOR_JUDGEMENT
        and activity_total < 900
    ):
        return RecommendationCard(
            "Movement",
            "Low activity",
            "Add some light activity.",
            "activity",
        )

    return RecommendationCard(
        "Movement",
        "Consistent activity",
        "Your activity level looks consistent.",
        "activity",
    )


def _build_progress_card(context: RecommendationContext) -> RecommendationCard:
    if (
        context.weight_days < MIN_WEIGHT_DAYS
        or context.current_weight_kg is None
        or context.interval_weight_delta_kg is None
    ):
        return RecommendationCard(
            "Progress",
            "Not enough data",
            "Log your weight more often.",
            "quality",
        )

    actual_status = _classify_progress(
        _weekly_weight_change_percent(
            context.interval_weight_delta_kg,
            context.current_weight_kg,
            context.days,
        ),
        context.goal,
    )
    prediction_status = _classify_prediction_progress(context)
    if _progress_signals_conflict(actual_status, prediction_status):
        return RecommendationCard(
            "Progress",
            "Keep monitoring",
            "Log a few more days.",
            "quality",
        )

    if actual_status == "good":
        if _normalize_goal(context.goal) == "mentinere":
            return RecommendationCard(
                "Progress",
                "Stable weight",
                "Your weight remains nearly stable.",
                "weight",
            )
        return RecommendationCard(
            "Progress",
            "Good progress",
            "Your weight is moving toward your goal.",
            "weight",
        )
    if actual_status == "too_fast":
        return RecommendationCard(
            "Progress",
            "Progress too fast",
            "Make changes more gradually.",
            "balance",
        )
    if actual_status == "variable":
        return RecommendationCard(
            "Progress",
            "Variable weight",
            "Keep monitoring for a few more days.",
            "weight",
        )
    return RecommendationCard(
        "Progress",
        "Slow progress",
        "Adjust your meals or activity.",
        "energy",
    )


def _protein_threshold_for_context(context: RecommendationContext) -> float:
    goal = _normalize_goal(context.goal)
    threshold_by_goal = {
        "slabire": 1.4,
        "mentinere": 1.2,
        "crestere": 1.55,
    }
    threshold = threshold_by_goal.get(goal, 1.2)
    if context.current_bmi is not None and context.current_bmi >= 30:
        threshold -= 0.2
    return round(max(1.0, threshold), 2)


def _has_excessive_activity_volume(context: RecommendationContext) -> bool:
    activity_total = context.activity_total_calories or 0.0
    avg_active_day = context.avg_activity_calories_per_active_day or 0.0
    return (
        context.activity_days >= 10
        or context.workouts_count >= 14
        or activity_total >= 5000
        or (context.activity_days >= 4 and avg_active_day >= 750)
    )


def _classify_progress(
    weekly_change_percent: float | None,
    goal: str | None,
) -> str:
    if weekly_change_percent is None:
        return "unknown"

    goal_key = _normalize_goal(goal)
    if goal_key == "slabire":
        if weekly_change_percent <= -1.0:
            return "too_fast"
        if weekly_change_percent <= -0.25:
            return "good"
        return "slow"

    if goal_key == "crestere":
        if weekly_change_percent >= 0.7:
            return "too_fast"
        if weekly_change_percent >= 0.1:
            return "good"
        return "slow"

    if abs(weekly_change_percent) <= 0.3:
        return "good"
    return "variable"


def _classify_prediction_progress(context: RecommendationContext) -> str | None:
    if (
        context.predicted_change_kg is None
        or context.predicted_horizon_days is None
        or context.current_weight_kg is None
    ):
        return None
    weekly_change = _weekly_weight_change_percent(
        context.predicted_change_kg,
        context.current_weight_kg,
        context.predicted_horizon_days,
    )
    return _classify_progress(weekly_change, context.goal)


def _progress_signals_conflict(
    actual_status: str,
    prediction_status: str | None,
) -> bool:
    if prediction_status is None:
        return False
    stable_statuses = {"good", "variable"}
    if actual_status in stable_statuses and prediction_status in {"good", "variable"}:
        return False
    if actual_status == prediction_status:
        return False
    if "too_fast" in {actual_status, prediction_status}:
        return False
    return actual_status != prediction_status


def _weekly_weight_change_percent(
    weight_change_kg: float | None,
    current_weight_kg: float | None,
    days: int | None,
) -> float | None:
    if weight_change_kg is None or current_weight_kg is None or current_weight_kg <= 0:
        return None
    if not days or days <= 0:
        return None
    return (weight_change_kg / current_weight_kg) * (7 / days) * 100


def _calculate_interval_weight_delta(daily_rows: Any) -> float | None:
    if daily_rows is None or not isinstance(daily_rows, pd.DataFrame) or daily_rows.empty:
        return None
    if "reference_weight_kg" not in daily_rows.columns or "log_date" not in daily_rows.columns:
        return None

    rows = daily_rows.copy()
    rows["reference_weight_kg"] = pd.to_numeric(
        rows["reference_weight_kg"], errors="coerce"
    )
    rows = rows.dropna(subset=["reference_weight_kg"]).sort_values("log_date")
    if rows.shape[0] < 2:
        return None
    return round(
        float(rows.iloc[-1]["reference_weight_kg"])
        - float(rows.iloc[0]["reference_weight_kg"]),
        2,
    )


def _select_prediction_signal(
    prediction_result: UserWeightPredictions | None,
) -> tuple[float | None, int | None]:
    if prediction_result is None or not prediction_result.predictions:
        return None, None
    predictions_by_horizon = {
        prediction.horizon_days: prediction for prediction in prediction_result.predictions
    }
    prediction = predictions_by_horizon.get(14) or prediction_result.predictions[0]
    return float(prediction.predicted_change_kg), int(prediction.horizon_days)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(numeric_value):
        return None
    return numeric_value


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
    return text.replace(" ", "_").replace("-", "_")
