"""Prediction helpers for applying saved MacroSense ML models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from database import get_connection
from services.ml.artifacts import (
    DEFAULT_MODEL_ARTIFACT_DIR,
    load_weight_model_artifact,
    predict_weight_change,
)
from services.ml.feature_engineering import (
    build_default_weight_prediction_feature_config,
    build_weight_prediction_feature_row,
)


DEFAULT_PREDICTION_HORIZONS = (14, 30)


@dataclass(frozen=True)
class WeightPrediction:
    """One weight prediction for a configured future horizon."""

    horizon_days: int
    analysis_date: date
    target_date: date
    current_weight_kg: float
    predicted_change_kg: float
    predicted_weight_kg: float
    model_name: str
    metrics: dict[str, float]


@dataclass(frozen=True)
class UserWeightPredictions:
    """Prediction bundle for a user and analysis date."""

    user_id: int
    analysis_date: date
    predictions: list[WeightPrediction]
    unavailable_horizons: dict[int, str]


def get_user_weight_predictions(
    user_id: int,
    analysis_date: date | None = None,
    artifact_dir: Path | str = DEFAULT_MODEL_ARTIFACT_DIR,
    horizons: tuple[int, ...] = DEFAULT_PREDICTION_HORIZONS,
    prefer_complete_days: bool = False,
    today: date | None = None,
) -> UserWeightPredictions:
    """Load user history from DB and apply saved weight prediction models."""

    target_date = _resolve_analysis_date(
        analysis_date,
        prefer_complete_days=prefer_complete_days,
        today=today,
    )
    profile, food_rows, activity_rows, weight_rows = fetch_user_prediction_frames(
        user_id, target_date
    )
    if profile is None:
        return UserWeightPredictions(
            user_id=user_id,
            analysis_date=target_date,
            predictions=[],
            unavailable_horizons={horizon: "Utilizatorul nu există." for horizon in horizons},
        )

    return predict_weight_changes_from_frames(
        profile,
        food_rows,
        activity_rows,
        weight_rows,
        target_date,
        artifact_dir,
        horizons,
    )


def get_latest_available_user_weight_predictions(
    user_id: int,
    analysis_date: date | None = None,
    artifact_dir: Path | str = DEFAULT_MODEL_ARTIFACT_DIR,
    horizons: tuple[int, ...] = DEFAULT_PREDICTION_HORIZONS,
    max_lookback_days: int = 14,
    prefer_complete_days: bool = False,
    today: date | None = None,
) -> UserWeightPredictions:
    """Return predictions for the newest date that has enough ML input data."""

    if max_lookback_days < 0:
        raise ValueError("max_lookback_days cannot be negative.")

    requested_date = _to_date(analysis_date) if analysis_date else _to_date(today or date.today())
    target_date = _resolve_analysis_date(
        analysis_date,
        prefer_complete_days=prefer_complete_days,
        today=today,
    )
    fetch_until_date = max(requested_date, target_date)
    profile, food_rows, activity_rows, weight_rows = fetch_user_prediction_frames(
        user_id, fetch_until_date
    )
    if profile is None:
        return UserWeightPredictions(
            user_id=user_id,
            analysis_date=target_date,
            predictions=[],
            unavailable_horizons={horizon: "Utilizatorul nu există." for horizon in horizons},
        )

    last_result: UserWeightPredictions | None = None
    for offset_days in range(max_lookback_days + 1):
        candidate_date = target_date - timedelta(days=offset_days)
        result = predict_weight_changes_from_frames(
            profile,
            food_rows,
            activity_rows,
            weight_rows,
            candidate_date,
            artifact_dir,
            horizons,
        )
        if result.predictions:
            return result
        last_result = result

    if prefer_complete_days and requested_date != target_date:
        current_day_result = predict_weight_changes_from_frames(
            profile,
            food_rows,
            activity_rows,
            weight_rows,
            requested_date,
            artifact_dir,
            horizons,
        )
        if current_day_result.predictions:
            return current_day_result
        last_result = current_day_result

    return last_result or UserWeightPredictions(
        user_id=int(profile["user_id"]),
        analysis_date=target_date,
        predictions=[],
        unavailable_horizons={
            horizon: "Nu există suficiente date recente pentru predicție."
            for horizon in horizons
        },
    )


def predict_weight_changes_from_frames(
    profile: dict[str, Any],
    food_rows: pd.DataFrame,
    activity_rows: pd.DataFrame,
    weight_rows: pd.DataFrame,
    analysis_date: date,
    artifact_dir: Path | str = DEFAULT_MODEL_ARTIFACT_DIR,
    horizons: tuple[int, ...] = DEFAULT_PREDICTION_HORIZONS,
) -> UserWeightPredictions:
    """Apply saved models to prepared user history frames."""

    analysis_date = _to_date(analysis_date)
    predictions: list[WeightPrediction] = []
    unavailable_horizons: dict[int, str] = {}

    for horizon_days in horizons:
        config = build_default_weight_prediction_feature_config(horizon_days)
        feature_row = build_weight_prediction_feature_row(
            profile,
            food_rows,
            activity_rows,
            weight_rows,
            analysis_date,
            config,
        )
        if feature_row is None:
            unavailable_horizons[horizon_days] = (
                "Nu există suficiente date recente pentru predicție."
            )
            continue

        try:
            artifact = load_weight_model_artifact(horizon_days, artifact_dir)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            unavailable_horizons[horizon_days] = str(exc)
            continue

        predicted_change = predict_weight_change(artifact, feature_row)
        current_weight = float(feature_row["current_weight_kg"])
        metadata = artifact.metadata
        model_name = metadata["best_model_name"]
        predictions.append(
            WeightPrediction(
                horizon_days=horizon_days,
                analysis_date=analysis_date,
                target_date=analysis_date + timedelta(days=horizon_days),
                current_weight_kg=round(current_weight, 2),
                predicted_change_kg=predicted_change,
                predicted_weight_kg=round(current_weight + predicted_change, 2),
                model_name=model_name,
                metrics=metadata["metrics_by_model"][model_name],
            )
        )

    return UserWeightPredictions(
        user_id=int(profile["user_id"]),
        analysis_date=analysis_date,
        predictions=predictions,
        unavailable_horizons=unavailable_horizons,
    )


def fetch_user_prediction_frames(
    user_id: int, analysis_date: date
) -> tuple[dict[str, Any] | None, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch raw app history and transform it into ML-safe input frames."""

    conn = None
    try:
        conn = get_connection()
        if not conn:
            return None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        cur = conn.cursor()
        profile = _fetch_profile(cur, user_id)
        if profile is None:
            return None, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        weight_rows = _fetch_weight_rows(cur, user_id, analysis_date)
        food_rows = _fetch_food_rows(cur, user_id, analysis_date)
        raw_activity_rows = _fetch_raw_activity_rows(cur, user_id, analysis_date)
        activity_rows = prepare_activity_rows_for_ml(raw_activity_rows, weight_rows)

        return profile, food_rows, activity_rows, weight_rows
    except Exception as exc:
        raise RuntimeError(f"Could not fetch ML prediction inputs: {exc}") from exc
    finally:
        if conn:
            conn.close()


def prepare_activity_rows_for_ml(
    raw_activity_rows: pd.DataFrame, weight_rows: pd.DataFrame
) -> pd.DataFrame:
    """Calculate ML-safe activity calories using only past weight references."""

    if raw_activity_rows.empty:
        return pd.DataFrame()

    activities = raw_activity_rows.copy()
    if "log_date" in activities.columns:
        activities["log_date"] = activities["log_date"].apply(_to_date)

    prepared_records: list[dict[str, Any]] = []
    for activity in activities.to_dict("records"):
        manual_calories = activity.get("manual_calories_burned")
        if manual_calories is not None and not pd.isna(manual_calories):
            calories_burned = round(float(manual_calories), 2)
        else:
            reference_weight = _find_past_weight(weight_rows, activity["log_date"])
            if reference_weight is None:
                continue
            calories_burned = _calculate_activity_calories(
                activity,
                reference_weight,
            )

        prepared_records.append(
            {
                "user_id": int(activity["user_id"]),
                "log_date": activity["log_date"],
                "activity_name": activity.get("activity_name"),
                "category": activity.get("category"),
                "duration_min": activity.get("duration_min"),
                "calories_burned": calories_burned,
            }
        )

    return pd.DataFrame(prepared_records)


def _fetch_profile(cur: Any, user_id: int) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT id, full_name, height_cm, age, gender, goal
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None

    return {
        "user_id": row[0],
        "full_name": row[1],
        "height_cm": row[2],
        "age": row[3],
        "gender": row[4],
        "goal": row[5],
    }


def _fetch_weight_rows(cur: Any, user_id: int, analysis_date: date) -> pd.DataFrame:
    cur.execute(
        """
        SELECT user_id, log_date, weight_kg
        FROM weight_logs
        WHERE user_id = %s
          AND log_date <= %s
        ORDER BY log_date ASC, id ASC
        """,
        (user_id, analysis_date),
    )
    return _rows_to_dataframe(cur.fetchall(), ["user_id", "log_date", "weight_kg"])


def _fetch_food_rows(cur: Any, user_id: int, analysis_date: date) -> pd.DataFrame:
    cur.execute(
        """
        SELECT
            dl.user_id,
            dl.log_date,
            fl.meal_type,
            CASE
                WHEN fl.food_id IS NOT NULL THEN fi.name
                ELSE fl.snapshot_name
            END AS food_name,
            CASE
                WHEN fl.food_id IS NOT NULL THEN 'catalog_food'
                ELSE 'custom_meal'
            END AS source_type,
            ROUND(CASE
                WHEN fl.food_id IS NOT NULL THEN fi.calories_100g * fl.quantity_g / 100.0
                ELSE fl.snapshot_calories_100g * fl.quantity_g / 100.0
            END, 2) AS calories,
            ROUND(CASE
                WHEN fl.food_id IS NOT NULL THEN fi.protein_g * fl.quantity_g / 100.0
                ELSE fl.snapshot_protein_100g * fl.quantity_g / 100.0
            END, 2) AS protein_g,
            ROUND(CASE
                WHEN fl.food_id IS NOT NULL THEN fi.carbs_g * fl.quantity_g / 100.0
                ELSE fl.snapshot_carbs_100g * fl.quantity_g / 100.0
            END, 2) AS carbs_g,
            ROUND(CASE
                WHEN fl.food_id IS NOT NULL THEN fi.fats_g * fl.quantity_g / 100.0
                ELSE fl.snapshot_fats_100g * fl.quantity_g / 100.0
            END, 2) AS fats_g
        FROM daily_logs dl
        JOIN food_logs fl ON fl.log_id = dl.id
        LEFT JOIN food_items fi ON fi.id = fl.food_id
        WHERE dl.user_id = %s
          AND dl.log_date <= %s
        ORDER BY dl.log_date ASC, fl.id ASC
        """,
        (user_id, analysis_date),
    )
    return _rows_to_dataframe(
        cur.fetchall(),
        [
            "user_id",
            "log_date",
            "meal_type",
            "food_name",
            "source_type",
            "calories",
            "protein_g",
            "carbs_g",
            "fats_g",
        ],
    )


def _fetch_raw_activity_rows(
    cur: Any, user_id: int, analysis_date: date
) -> pd.DataFrame:
    cur.execute(
        """
        SELECT
            dl.user_id,
            dl.log_date,
            a.name AS activity_name,
            a.category,
            al.duration_min,
            al.sets,
            al.reps,
            al.manual_calories_burned,
            a.met_multiplier
        FROM daily_logs dl
        JOIN activity_logs al ON al.log_id = dl.id
        JOIN activities a ON a.id = al.activity_id
        WHERE dl.user_id = %s
          AND dl.log_date <= %s
        ORDER BY dl.log_date ASC, al.id ASC
        """,
        (user_id, analysis_date),
    )
    return _rows_to_dataframe(
        cur.fetchall(),
        [
            "user_id",
            "log_date",
            "activity_name",
            "category",
            "duration_min",
            "sets",
            "reps",
            "manual_calories_burned",
            "met_multiplier",
        ],
    )


def _calculate_activity_calories(
    activity: dict[str, Any], reference_weight_kg: float
) -> float:
    duration = float(activity["duration_min"])
    met = float(activity["met_multiplier"])
    sets = activity.get("sets")
    reps = activity.get("reps")
    if _is_strength_category(activity.get("category")) and sets and reps:
        sets_value = int(sets)
        reps_value = int(reps)
        active_time = min(duration, (sets_value * reps_value * 3.0) / 60.0)
        rest_time = max(0.0, duration - active_time)
        return round(
            (met * reference_weight_kg * (active_time / 60.0))
            + (1.5 * reference_weight_kg * (rest_time / 60.0)),
            2,
        )
    return round(met * reference_weight_kg * (duration / 60.0), 2)


def _is_strength_category(category: Any) -> bool:
    normalized = str(category or "").strip().lower()
    return normalized in {"forta", "forță", "forÈ›Äƒ".lower()}


def _find_past_weight(weight_rows: pd.DataFrame, target_date: date) -> float | None:
    if weight_rows.empty:
        return None

    weights = weight_rows.copy()
    weights["log_date"] = weights["log_date"].apply(_to_date)
    weights["weight_kg"] = pd.to_numeric(weights["weight_kg"], errors="coerce")
    weights = weights.dropna(subset=["weight_kg"])
    past_weights = weights[weights["log_date"] <= _to_date(target_date)]
    if past_weights.empty:
        return None
    return round(float(past_weights.sort_values("log_date").iloc[-1]["weight_kg"]), 3)


def _resolve_analysis_date(
    analysis_date: date | None,
    prefer_complete_days: bool = False,
    today: date | None = None,
) -> date:
    resolved_date = (
        _to_date(analysis_date) if analysis_date else _to_date(today or date.today())
    )
    current_date = _to_date(today or date.today())
    if prefer_complete_days and resolved_date >= current_date:
        return current_date - timedelta(days=1)
    return resolved_date


def _rows_to_dataframe(rows: list[tuple[Any, ...]], columns: list[str]) -> pd.DataFrame:
    dataframe = pd.DataFrame(rows, columns=columns)
    if "log_date" in dataframe.columns and not dataframe.empty:
        dataframe["log_date"] = dataframe["log_date"].apply(_to_date)
    return dataframe


def _to_date(value: Any) -> date:
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.to_datetime(value).date()
