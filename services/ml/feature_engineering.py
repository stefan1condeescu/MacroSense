"""Leakage-safe feature engineering for MacroSense ML datasets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from services.analytics.energy import (
    calculate_base_tdee,
    calculate_bmr,
    calculate_estimated_balance,
    calculate_estimated_tdee,
)


@dataclass(frozen=True)
class WeightPredictionFeatureConfig:
    """Configuration for weight-change prediction feature rows."""

    horizon_days: int
    feature_window_days: int | None = None
    min_food_days: int = 7
    min_weight_days: int = 2
    target_tolerance_days: int = 3

    def __post_init__(self) -> None:
        if self.horizon_days <= 0:
            raise ValueError("horizon_days must be positive.")
        if self.feature_window_days is not None and self.feature_window_days <= 0:
            raise ValueError("feature_window_days must be positive.")
        if self.min_food_days < 0:
            raise ValueError("min_food_days cannot be negative.")
        if self.min_weight_days < 1:
            raise ValueError("min_weight_days must be at least 1.")
        if self.target_tolerance_days < 0:
            raise ValueError("target_tolerance_days cannot be negative.")

    @property
    def resolved_feature_window_days(self) -> int:
        return self.feature_window_days or self.horizon_days


def build_default_weight_prediction_feature_config(
    horizon_days: int,
    feature_window_days: int | None = None,
    min_food_days: int | None = None,
    min_weight_days: int | None = None,
) -> WeightPredictionFeatureConfig:
    """Build the shared feature policy used by training and live prediction."""

    resolved_window_days = feature_window_days or horizon_days
    resolved_min_food_days = (
        min_food_days
        if min_food_days is not None
        else min(resolved_window_days, max(7, round(resolved_window_days * 0.45)))
    )
    resolved_min_weight_days = (
        min_weight_days
        if min_weight_days is not None
        else (2 if resolved_window_days <= 14 else 3)
    )
    return WeightPredictionFeatureConfig(
        horizon_days=horizon_days,
        feature_window_days=resolved_window_days,
        min_food_days=resolved_min_food_days,
        min_weight_days=resolved_min_weight_days,
    )


FEATURE_COLUMNS = [
    "user_id",
    "analysis_date",
    "horizon_days",
    "feature_window_days",
    "current_weight_kg",
    "current_weight_source_date",
    "target_date",
    "target_weight_kg",
    "target_weight_source_date",
    "target_weight_change_kg",
    "calories_avg_logged_days",
    "calories_total",
    "food_days",
    "food_consistency",
    "protein_avg_logged_days",
    "protein_per_kg_avg_logged_days",
    "carbs_avg_logged_days",
    "fats_avg_logged_days",
    "activity_calories_avg_all_days",
    "activity_calories_total",
    "activity_days",
    "activity_consistency",
    "workouts_count",
    "weight_days",
    "weight_consistency",
    "weight_trend_kg",
    "estimated_balance_avg_logged_days",
]


def build_weight_prediction_dataset(
    profile_rows: pd.DataFrame,
    food_rows: pd.DataFrame,
    activity_rows: pd.DataFrame,
    weight_rows: pd.DataFrame,
    config: WeightPredictionFeatureConfig,
) -> pd.DataFrame:
    """Build supervised rows for future weight-change prediction.

    Feature columns use only data available on or before ``analysis_date``.
    Future weight is used only as the supervised target.
    """

    profiles = _normalize_profiles(profile_rows)
    foods = _normalize_food_rows(food_rows)
    activities = _normalize_activity_rows(activity_rows)
    weights = _normalize_weight_rows(weight_rows)

    if profiles.empty or weights.empty:
        return _empty_feature_frame()

    feature_rows: list[dict[str, Any]] = []
    for profile in profiles.to_dict("records"):
        user_id = int(profile["user_id"])
        user_weights = _rows_for_user(weights, user_id)
        if user_weights.empty:
            continue
        user_foods = _rows_for_user(foods, user_id)
        user_activities = _rows_for_user(activities, user_id)

        candidate_dates = _candidate_analysis_dates(
            user_weights, foods, activities, user_id, config
        )
        for analysis_date in candidate_dates:
            feature_row = _build_weight_prediction_feature_row_from_normalized(
                profile,
                user_foods,
                user_activities,
                user_weights,
                analysis_date,
                config,
            )
            if feature_row is None:
                continue

            target_date = analysis_date + timedelta(days=config.horizon_days)
            target_weight = _find_target_weight(
                user_weights,
                target_date,
                config.target_tolerance_days,
            )
            if target_weight is None:
                continue

            feature_row.update(
                {
                    "target_date": target_date,
                    "target_weight_kg": target_weight["weight_kg"],
                    "target_weight_source_date": target_weight["log_date"],
                    "target_weight_change_kg": round(
                        target_weight["weight_kg"] - feature_row["current_weight_kg"],
                        3,
                    ),
                }
            )
            feature_rows.append(feature_row)

    if not feature_rows:
        return _empty_feature_frame()

    return pd.DataFrame(feature_rows, columns=FEATURE_COLUMNS)


def build_weight_prediction_feature_row(
    profile: dict[str, Any],
    food_rows: pd.DataFrame,
    activity_rows: pd.DataFrame,
    weight_rows: pd.DataFrame,
    analysis_date: date,
    config: WeightPredictionFeatureConfig,
) -> dict[str, Any] | None:
    """Build one ML input row using only data available up to ``analysis_date``."""

    analysis_date = _to_date(analysis_date)
    window_days = config.resolved_feature_window_days
    window_start = analysis_date - timedelta(days=window_days - 1)

    foods = _normalize_food_rows(food_rows)
    activities = _normalize_activity_rows(activity_rows)
    weights = _normalize_weight_rows(weight_rows)
    if weights.empty:
        return None

    return _build_weight_prediction_feature_row_from_normalized(
        profile, foods, activities, weights, analysis_date, config
    )


def _build_weight_prediction_feature_row_from_normalized(
    profile: dict[str, Any],
    foods: pd.DataFrame,
    activities: pd.DataFrame,
    weights: pd.DataFrame,
    analysis_date: date,
    config: WeightPredictionFeatureConfig,
) -> dict[str, Any] | None:
    analysis_date = _to_date(analysis_date)
    window_days = config.resolved_feature_window_days
    window_start = analysis_date - timedelta(days=window_days - 1)

    current_weight = _find_past_weight(weights, analysis_date)
    if current_weight is None:
        return None

    window_weights = _filter_between(weights, "log_date", window_start, analysis_date)
    weight_days = int(window_weights["log_date"].nunique()) if not window_weights.empty else 0
    if weight_days < config.min_weight_days:
        return None

    window_foods = _filter_between(foods, "log_date", window_start, analysis_date)
    window_activities = _filter_between(
        activities, "log_date", window_start, analysis_date
    )
    daily_rows = _build_daily_window_rows(
        profile, window_foods, window_activities, weights, window_start, analysis_date
    )
    food_days = int(daily_rows["has_food_logs"].sum())
    if food_days < config.min_food_days:
        return None

    food_logged_rows = daily_rows[daily_rows["has_food_logs"]]
    activity_days = int(daily_rows["has_activity_logs"].sum())
    weight_trend = _calculate_weight_trend(window_weights, current_weight["weight_kg"])

    return {
        "user_id": int(profile["user_id"]),
        "analysis_date": analysis_date,
        "horizon_days": config.horizon_days,
        "feature_window_days": window_days,
        "current_weight_kg": round(float(current_weight["weight_kg"]), 3),
        "current_weight_source_date": current_weight["log_date"],
        "target_date": None,
        "target_weight_kg": None,
        "target_weight_source_date": None,
        "target_weight_change_kg": None,
        "calories_avg_logged_days": _mean_or_none(
            food_logged_rows["total_calories_in"]
        ),
        "calories_total": _sum_or_zero(food_logged_rows["total_calories_in"]),
        "food_days": food_days,
        "food_consistency": _ratio(food_days, window_days),
        "protein_avg_logged_days": _mean_or_none(food_logged_rows["protein_g"]),
        "protein_per_kg_avg_logged_days": _mean_or_none(
            food_logged_rows["protein_per_kg"]
        ),
        "carbs_avg_logged_days": _mean_or_none(food_logged_rows["carbs_g"]),
        "fats_avg_logged_days": _mean_or_none(food_logged_rows["fats_g"]),
        "activity_calories_avg_all_days": _mean_or_none(
            daily_rows["activity_calories_burned"]
        ),
        "activity_calories_total": _sum_or_zero(
            daily_rows["activity_calories_burned"]
        ),
        "activity_days": activity_days,
        "activity_consistency": _ratio(activity_days, window_days),
        "workouts_count": int(daily_rows["workouts_count"].sum()),
        "weight_days": weight_days,
        "weight_consistency": _ratio(weight_days, window_days),
        "weight_trend_kg": weight_trend,
        "estimated_balance_avg_logged_days": _mean_or_none(
            food_logged_rows["estimated_balance"]
        ),
    }


def _build_daily_window_rows(
    profile: dict[str, Any],
    food_rows: pd.DataFrame,
    activity_rows: pd.DataFrame,
    weight_rows: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    date_index = pd.date_range(start=start_date, end=end_date, freq="D")
    daily_rows = pd.DataFrame({"log_date": [item.date() for item in date_index]})

    food_daily = _aggregate_food_rows(food_rows)
    if not food_daily.empty:
        daily_rows = daily_rows.merge(food_daily, on="log_date", how="left")

    activity_daily = _aggregate_activity_rows(activity_rows)
    if not activity_daily.empty:
        daily_rows = daily_rows.merge(activity_daily, on="log_date", how="left")

    for column in ("total_calories_in", "protein_g", "carbs_g", "fats_g"):
        if column not in daily_rows.columns:
            daily_rows[column] = pd.NA

    if "food_entries_count" not in daily_rows.columns:
        daily_rows["food_entries_count"] = 0
    daily_rows["food_entries_count"] = (
        pd.to_numeric(daily_rows["food_entries_count"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    daily_rows["has_food_logs"] = daily_rows["food_entries_count"] > 0

    if "activity_calories_burned" not in daily_rows.columns:
        daily_rows["activity_calories_burned"] = 0.0
    daily_rows["activity_calories_burned"] = pd.to_numeric(
        daily_rows["activity_calories_burned"], errors="coerce"
    ).fillna(0.0)

    if "workouts_count" not in daily_rows.columns:
        daily_rows["workouts_count"] = 0
    daily_rows["workouts_count"] = (
        pd.to_numeric(daily_rows["workouts_count"], errors="coerce")
        .fillna(0)
        .astype(int)
    )
    daily_rows["has_activity_logs"] = daily_rows["workouts_count"] > 0

    estimates = daily_rows.apply(
        lambda row: _calculate_daily_ml_estimates(profile, weight_rows, row),
        axis=1,
        result_type="expand",
    )
    daily_rows = pd.concat([daily_rows, estimates], axis=1)
    return daily_rows


def _calculate_daily_ml_estimates(
    profile: dict[str, Any], weight_rows: pd.DataFrame, row: pd.Series
) -> dict[str, float | None]:
    reference_weight = _find_past_weight(weight_rows, row["log_date"])
    if reference_weight is None:
        return {
            "reference_weight_kg": None,
            "estimated_tdee": None,
            "estimated_balance": None,
            "protein_per_kg": None,
        }

    weight_kg = float(reference_weight["weight_kg"])
    protein = row.get("protein_g")
    protein_per_kg = None
    if row.get("has_food_logs") and protein is not None and not pd.isna(protein):
        protein_per_kg = round(float(protein) / weight_kg, 3)

    try:
        bmr = calculate_bmr(
            weight_kg,
            profile["height_cm"],
            profile["age"],
            profile["gender"],
        )
        base_tdee = calculate_base_tdee(bmr)
        estimated_tdee = calculate_estimated_tdee(
            base_tdee, row.get("activity_calories_burned", 0.0)
        )
        estimated_balance = (
            calculate_estimated_balance(row.get("total_calories_in"), estimated_tdee)
            if row.get("has_food_logs")
            else None
        )
    except (TypeError, ValueError):
        estimated_tdee = None
        estimated_balance = None

    return {
        "reference_weight_kg": round(weight_kg, 3),
        "estimated_tdee": estimated_tdee,
        "estimated_balance": estimated_balance,
        "protein_per_kg": protein_per_kg,
    }


def _aggregate_food_rows(food_rows: pd.DataFrame) -> pd.DataFrame:
    if food_rows.empty:
        return pd.DataFrame()

    foods = food_rows.copy()
    aggregate_columns = {
        "calories": "total_calories_in",
        "total_calories_in": "total_calories_in",
        "calories_in": "total_calories_in",
        "protein_g": "protein_g",
        "carbs_g": "carbs_g",
        "fats_g": "fats_g",
        "fat_g": "fats_g",
    }
    for source, target in aggregate_columns.items():
        if source in foods.columns and target not in foods.columns:
            foods[target] = foods[source]

    for column in ("total_calories_in", "protein_g", "carbs_g", "fats_g"):
        if column not in foods.columns:
            foods[column] = 0.0
        foods[column] = pd.to_numeric(foods[column], errors="coerce").fillna(0.0)

    grouped = (
        foods.groupby("log_date", as_index=False)
        .agg(
            total_calories_in=("total_calories_in", "sum"),
            protein_g=("protein_g", "sum"),
            carbs_g=("carbs_g", "sum"),
            fats_g=("fats_g", "sum"),
            food_entries_count=("log_date", "size"),
        )
        .sort_values("log_date")
        .reset_index(drop=True)
    )
    return grouped


def _aggregate_activity_rows(activity_rows: pd.DataFrame) -> pd.DataFrame:
    if activity_rows.empty:
        return pd.DataFrame()

    activities = activity_rows.copy()
    if "activity_calories_burned" not in activities.columns:
        if "calories_burned" in activities.columns:
            activities["activity_calories_burned"] = activities["calories_burned"]
        elif "total_calories_burned" in activities.columns:
            activities["activity_calories_burned"] = activities["total_calories_burned"]
        else:
            activities["activity_calories_burned"] = 0.0

    activities["activity_calories_burned"] = pd.to_numeric(
        activities["activity_calories_burned"], errors="coerce"
    ).fillna(0.0)

    grouped = (
        activities.groupby("log_date", as_index=False)
        .agg(
            activity_calories_burned=("activity_calories_burned", "sum"),
            workouts_count=("log_date", "size"),
        )
        .sort_values("log_date")
        .reset_index(drop=True)
    )
    return grouped


def _candidate_analysis_dates(
    weight_rows: pd.DataFrame,
    food_rows: pd.DataFrame,
    activity_rows: pd.DataFrame,
    user_id: int,
    config: WeightPredictionFeatureConfig,
) -> list[date]:
    user_foods = _rows_for_user(food_rows, user_id)
    user_activities = _rows_for_user(activity_rows, user_id)
    date_frames = [weight_rows]
    if not user_foods.empty:
        date_frames.append(user_foods)
    if not user_activities.empty:
        date_frames.append(user_activities)

    min_date = min(frame["log_date"].min() for frame in date_frames)
    max_weight_date = weight_rows["log_date"].max()
    first_analysis_date = min_date + timedelta(
        days=config.resolved_feature_window_days - 1
    )
    last_analysis_date = max_weight_date - timedelta(days=config.horizon_days)
    if first_analysis_date > last_analysis_date:
        return []

    return [
        item.date()
        for item in pd.date_range(
            start=first_analysis_date, end=last_analysis_date, freq="D"
        )
    ]


def _normalize_profiles(profile_rows: pd.DataFrame) -> pd.DataFrame:
    if profile_rows is None or profile_rows.empty:
        return pd.DataFrame()

    profiles = profile_rows.copy()
    if "user_id" not in profiles.columns and "id" in profiles.columns:
        profiles["user_id"] = profiles["id"]

    required_columns = ["user_id", "height_cm", "age", "gender"]
    _require_columns(profiles, required_columns, "profile_rows")
    profiles["user_id"] = pd.to_numeric(profiles["user_id"], errors="coerce")
    profiles = profiles.dropna(subset=["user_id"])
    profiles["user_id"] = profiles["user_id"].astype(int)
    return profiles


def _normalize_food_rows(food_rows: pd.DataFrame) -> pd.DataFrame:
    return _normalize_event_rows(food_rows, "food_rows")


def _normalize_activity_rows(activity_rows: pd.DataFrame) -> pd.DataFrame:
    return _normalize_event_rows(activity_rows, "activity_rows")


def _normalize_event_rows(rows: pd.DataFrame, frame_name: str) -> pd.DataFrame:
    if rows is None or rows.empty:
        return pd.DataFrame()

    normalized = rows.copy()
    _require_columns(normalized, ["user_id", "log_date"], frame_name)
    normalized["user_id"] = pd.to_numeric(normalized["user_id"], errors="coerce")
    normalized["log_date"] = normalized["log_date"].apply(_to_date)
    normalized = normalized.dropna(subset=["user_id", "log_date"])
    normalized["user_id"] = normalized["user_id"].astype(int)
    return normalized.sort_values(["user_id", "log_date"]).reset_index(drop=True)


def _normalize_weight_rows(weight_rows: pd.DataFrame) -> pd.DataFrame:
    if weight_rows is None or weight_rows.empty:
        return pd.DataFrame()

    weights = weight_rows.copy()
    _require_columns(weights, ["user_id", "log_date", "weight_kg"], "weight_rows")
    weights["user_id"] = pd.to_numeric(weights["user_id"], errors="coerce")
    weights["log_date"] = weights["log_date"].apply(_to_date)
    weights["weight_kg"] = pd.to_numeric(weights["weight_kg"], errors="coerce")
    weights = weights.dropna(subset=["user_id", "log_date", "weight_kg"])
    weights["user_id"] = weights["user_id"].astype(int)
    return weights.sort_values(["user_id", "log_date"]).reset_index(drop=True)


def _require_columns(
    dataframe: pd.DataFrame, required_columns: list[str], frame_name: str
) -> None:
    missing = [column for column in required_columns if column not in dataframe.columns]
    if missing:
        raise ValueError(f"{frame_name} is missing columns: {', '.join(missing)}.")


def _rows_for_user(dataframe: pd.DataFrame, user_id: int) -> pd.DataFrame:
    if dataframe.empty or "user_id" not in dataframe.columns:
        return pd.DataFrame()
    return dataframe[dataframe["user_id"] == user_id].reset_index(drop=True)


def _filter_between(
    dataframe: pd.DataFrame, date_column: str, start_date: date, end_date: date
) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe.copy()
    return dataframe[
        (dataframe[date_column] >= start_date) & (dataframe[date_column] <= end_date)
    ].reset_index(drop=True)


def _find_past_weight(weight_rows: pd.DataFrame, target_date: date) -> dict[str, Any] | None:
    if weight_rows.empty:
        return None

    target_date = _to_date(target_date)
    past_rows = weight_rows[weight_rows["log_date"] <= target_date]
    if past_rows.empty:
        return None

    source_row = past_rows.sort_values("log_date").iloc[-1]
    return {
        "log_date": source_row["log_date"],
        "weight_kg": round(float(source_row["weight_kg"]), 3),
    }


def _find_target_weight(
    weight_rows: pd.DataFrame, target_date: date, tolerance_days: int
) -> dict[str, Any] | None:
    if weight_rows.empty:
        return None

    target_date = _to_date(target_date)
    max_target_date = target_date + timedelta(days=tolerance_days)
    target_rows = weight_rows[
        (weight_rows["log_date"] >= target_date)
        & (weight_rows["log_date"] <= max_target_date)
    ]
    if target_rows.empty:
        return None

    target_row = target_rows.sort_values("log_date").iloc[0]
    return {
        "log_date": target_row["log_date"],
        "weight_kg": round(float(target_row["weight_kg"]), 3),
    }


def _calculate_weight_trend(
    window_weights: pd.DataFrame, current_weight_kg: float
) -> float | None:
    if window_weights.empty:
        return None

    first_weight = window_weights.sort_values("log_date").iloc[0]
    return round(float(current_weight_kg) - float(first_weight["weight_kg"]), 3)


def _to_date(value: Any) -> date:
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.to_datetime(value).date()


def _mean_or_none(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None
    return round(float(values.mean()), 3)


def _sum_or_zero(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return 0.0
    return round(float(values.sum()), 3)


def _ratio(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(float(value) / float(total), 3)


def _empty_feature_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=FEATURE_COLUMNS)
