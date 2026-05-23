"""Read-only dashboard aggregations for MacroSense."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from database import get_connection
from services.analytics.energy import (
    calculate_base_tdee,
    calculate_bmi,
    calculate_bmr,
    calculate_estimated_balance,
    calculate_estimated_tdee,
)

DEFAULT_DASHBOARD_DAYS = 30


def get_interval_bounds(
    days: int = DEFAULT_DASHBOARD_DAYS, end_date: date | None = None
) -> tuple[date, date]:
    days_value = int(days)
    if days_value <= 0:
        raise ValueError("days must be positive.")

    interval_end = end_date or date.today()
    interval_start = interval_end - timedelta(days=days_value - 1)
    return interval_start, interval_end


def get_dashboard_data(
    user_id: int, days: int = DEFAULT_DASHBOARD_DAYS, end_date: date | None = None
) -> dict[str, Any]:
    start_date, interval_end = get_interval_bounds(days, end_date)
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        profile = _fetch_user_profile(cur, user_id)
        if profile is None:
            return empty_dashboard_data(days, start_date, interval_end)

        weight_rows = _fetch_weight_rows(cur, user_id)
        daily_log_rows = _fetch_daily_log_rows(cur, user_id, start_date, interval_end)
        macro_rows = _fetch_macro_rows(cur, user_id, start_date, interval_end)
        activity_breakdown = _fetch_activity_breakdown(
            cur, user_id, start_date, interval_end
        )

        daily_rows = prepare_daily_analytics(
            profile, daily_log_rows, weight_rows, start_date, interval_end
        )
        weight_interval_rows = _filter_by_interval(
            weight_rows, "log_date", start_date, interval_end
        )
        summary = summarize_dashboard(
            profile,
            daily_rows,
            weight_rows,
            macro_rows,
            activity_breakdown,
            days,
        )
        current = summarize_current_state(profile, daily_rows, weight_rows, interval_end)

        return {
            "profile": profile,
            "current": current,
            "summary": summary,
            "daily_rows": daily_rows,
            "weight_rows": weight_interval_rows,
            "all_weight_rows": weight_rows,
            "macro_rows": macro_rows,
            "activity_breakdown": activity_breakdown,
            "start_date": start_date,
            "end_date": interval_end,
            "days": days,
        }
    except Exception as exc:
        raise RuntimeError(f"Could not load dashboard data: {exc}") from exc
    finally:
        if conn:
            conn.close()


def get_daily_energy_estimate(user_id: int, target_date: date) -> dict[str, Any]:
    """Returns the dashboard-compatible energy estimate for one calendar day."""
    data = get_dashboard_data(user_id, days=1, end_date=target_date)
    daily_row = _get_daily_row(data.get("daily_rows", pd.DataFrame()), target_date)
    if daily_row is None:
        return {}

    return {
        "log_date": _to_date(daily_row.get("log_date")),
        "reference_weight_kg": _optional_float(daily_row.get("reference_weight_kg")),
        "base_tdee": _optional_float(daily_row.get("base_tdee")),
        "estimated_tdee": _optional_float(daily_row.get("estimated_tdee")),
        "estimated_balance": _optional_float(daily_row.get("estimated_balance")),
        "activity_calories_burned": _optional_float(
            daily_row.get("activity_calories_burned")
        ),
        "food_calories_in": _optional_float(daily_row.get("food_calories_in")),
        "has_food_logs": bool(daily_row.get("has_food_logs")),
        "has_activity_logs": bool(daily_row.get("has_activity_logs")),
        "activity_breakdown": data.get("activity_breakdown", pd.DataFrame()),
    }


def empty_dashboard_data(
    days: int = DEFAULT_DASHBOARD_DAYS,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    interval_start, interval_end = (
        (start_date, end_date) if start_date and end_date else get_interval_bounds(days)
    )
    return {
        "profile": None,
        "current": {},
        "summary": {},
        "daily_rows": pd.DataFrame(),
        "weight_rows": pd.DataFrame(),
        "all_weight_rows": pd.DataFrame(),
        "macro_rows": pd.DataFrame(),
        "activity_breakdown": pd.DataFrame(),
        "start_date": interval_start,
        "end_date": interval_end,
        "days": days,
    }


def prepare_daily_analytics(
    profile: dict[str, Any],
    daily_log_rows: pd.DataFrame,
    weight_rows: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    date_index = pd.date_range(start=start_date, end=end_date, freq="D")
    daily_rows = pd.DataFrame({"log_date": [item.date() for item in date_index]})

    logs = daily_log_rows.copy()
    if not logs.empty:
        logs["log_date"] = logs["log_date"].apply(_to_date)
        daily_rows = daily_rows.merge(logs, on="log_date", how="left")

    for column in ("has_food_logs", "has_activity_logs"):
        if column not in daily_rows.columns:
            daily_rows[column] = False
        daily_rows[column] = daily_rows[column].fillna(False).astype(bool)

    numeric_columns = [
        "total_calories_in",
        "activity_calories_burned",
        "workouts_count",
    ]
    for column in numeric_columns:
        if column not in daily_rows.columns:
            daily_rows[column] = 0.0
        daily_rows[column] = pd.to_numeric(daily_rows[column], errors="coerce").fillna(0.0)

    daily_rows["food_calories_in"] = daily_rows.apply(
        lambda row: row["total_calories_in"] if row["has_food_logs"] else None,
        axis=1,
    )
    reference_weight_info = daily_rows["log_date"].apply(
        lambda log_date: pd.Series(find_reference_weight_info(weight_rows, log_date))
    )
    daily_rows = pd.concat([daily_rows, reference_weight_info], axis=1)

    estimates = daily_rows.apply(
        lambda row: _calculate_daily_energy_estimates(profile, row),
        axis=1,
        result_type="expand",
    )
    if estimates.empty:
        estimates = pd.DataFrame(
            columns=["bmi", "bmr", "base_tdee", "estimated_tdee", "estimated_balance"]
        )

    daily_rows = pd.concat([daily_rows, estimates], axis=1)
    return daily_rows


def find_reference_weight_info(
    weight_rows: pd.DataFrame, target_date: date
) -> dict[str, Any]:
    target_date = _to_date(target_date)
    empty_info = {
        "reference_weight_kg": None,
        "reference_weight_source_date": None,
        "reference_weight_is_imputed": False,
        "reference_weight_uses_future_reference": False,
        "reference_weight_days_distance": None,
    }
    if weight_rows.empty or "log_date" not in weight_rows.columns:
        return empty_info

    normalized = weight_rows.copy()
    normalized["log_date"] = normalized["log_date"].apply(_to_date)
    normalized["weight_kg"] = pd.to_numeric(normalized["weight_kg"], errors="coerce")
    normalized = normalized.dropna(subset=["weight_kg"]).sort_values("log_date")
    if normalized.empty:
        return empty_info

    past_rows = normalized[normalized["log_date"] <= target_date]
    if not past_rows.empty:
        source_row = past_rows.iloc[-1]
        source_date = source_row["log_date"]
        days_distance = abs((target_date - source_date).days)
        return {
            "reference_weight_kg": round(float(source_row["weight_kg"]), 2),
            "reference_weight_source_date": source_date,
            "reference_weight_is_imputed": days_distance != 0,
            "reference_weight_uses_future_reference": False,
            "reference_weight_days_distance": days_distance,
        }

    future_rows = normalized[normalized["log_date"] > target_date]
    if not future_rows.empty:
        source_row = future_rows.iloc[0]
        source_date = source_row["log_date"]
        days_distance = abs((source_date - target_date).days)
        return {
            "reference_weight_kg": round(float(source_row["weight_kg"]), 2),
            "reference_weight_source_date": source_date,
            "reference_weight_is_imputed": True,
            "reference_weight_uses_future_reference": True,
            "reference_weight_days_distance": days_distance,
        }

    return empty_info


def find_reference_weight(weight_rows: pd.DataFrame, target_date: date) -> float | None:
    return find_reference_weight_info(weight_rows, target_date)["reference_weight_kg"]


def find_past_reference_weight_info(
    weight_rows: pd.DataFrame, target_date: date
) -> dict[str, Any]:
    """Return a leakage-safe reference weight for ML datasets."""

    target_date = _to_date(target_date)
    empty_info = {
        "reference_weight_kg": None,
        "reference_weight_source_date": None,
        "reference_weight_is_imputed": False,
        "reference_weight_uses_future_reference": False,
        "reference_weight_days_distance": None,
    }
    if weight_rows.empty or "log_date" not in weight_rows.columns:
        return empty_info

    normalized = weight_rows.copy()
    normalized["log_date"] = normalized["log_date"].apply(_to_date)
    normalized["weight_kg"] = pd.to_numeric(normalized["weight_kg"], errors="coerce")
    normalized = normalized.dropna(subset=["weight_kg"]).sort_values("log_date")
    if normalized.empty:
        return empty_info

    past_rows = normalized[normalized["log_date"] <= target_date]
    if past_rows.empty:
        return empty_info

    source_row = past_rows.iloc[-1]
    source_date = source_row["log_date"]
    days_distance = abs((target_date - source_date).days)
    return {
        "reference_weight_kg": round(float(source_row["weight_kg"]), 2),
        "reference_weight_source_date": source_date,
        "reference_weight_is_imputed": days_distance != 0,
        "reference_weight_uses_future_reference": False,
        "reference_weight_days_distance": days_distance,
    }


def summarize_dashboard(
    profile: dict[str, Any],
    daily_rows: pd.DataFrame,
    weight_rows: pd.DataFrame,
    macro_rows: pd.DataFrame,
    activity_breakdown: pd.DataFrame,
    days: int,
) -> dict[str, Any]:
    latest_weight = _latest_weight_summary(weight_rows)
    food_rows = daily_rows[daily_rows["has_food_logs"]] if not daily_rows.empty else pd.DataFrame()
    activity_rows = (
        daily_rows[daily_rows["has_activity_logs"]] if not daily_rows.empty else pd.DataFrame()
    )
    weight_days = _count_actual_weight_days(daily_rows)

    logged_days = 0
    if not daily_rows.empty:
        logged_days = int(
            (
                daily_rows["has_food_logs"]
                | daily_rows["has_activity_logs"]
                | _actual_weight_mask(daily_rows)
            ).sum()
        )

    return {
        "latest_weight_kg": latest_weight["latest_weight_kg"],
        "latest_weight_date": latest_weight["latest_weight_date"],
        "weight_delta_kg": latest_weight["weight_delta_kg"],
        "bmi": _mean_or_none(daily_rows.get("bmi")) if not daily_rows.empty else None,
        "avg_calories_in": _mean_or_none(food_rows.get("food_calories_in")),
        "avg_activity_calories": _mean_or_none(
            activity_rows.get("activity_calories_burned")
        ),
        "avg_estimated_tdee": _mean_or_none(food_rows.get("estimated_tdee")),
        "avg_estimated_balance": _mean_or_none(food_rows.get("estimated_balance")),
        "avg_protein_g": _mean_or_none(macro_rows.get("protein_g")),
        "avg_protein_per_kg": _calculate_average_protein_per_kg(
            macro_rows, daily_rows
        ),
        "avg_carbs_g": _mean_or_none(macro_rows.get("carbs_g")),
        "avg_fats_g": _mean_or_none(macro_rows.get("fats_g")),
        "logged_days": logged_days,
        "logging_consistency": round((logged_days / int(days)) * 100, 1),
        "overall_logging_consistency": round((logged_days / int(days)) * 100, 1),
        "food_logging_consistency": round((int(food_rows.shape[0]) / int(days)) * 100, 1),
        "activity_logging_consistency": round(
            (int(activity_rows.shape[0]) / int(days)) * 100, 1
        ),
        "weight_logging_consistency": round((weight_days / int(days)) * 100, 1),
        "food_days": int(food_rows.shape[0]),
        "activity_days": int(activity_rows.shape[0]),
        "weight_days": weight_days,
        "workouts_count": int(daily_rows["workouts_count"].sum())
        if not daily_rows.empty
        else 0,
        "activity_total_calories": _sum_or_none(
            activity_breakdown.get("total_calories_burned")
        ),
        "has_energy_estimates": bool(
            not daily_rows.empty and daily_rows["estimated_tdee"].notna().any()
        ),
        "goal": profile.get("goal") if profile else None,
    }


def summarize_current_state(
    profile: dict[str, Any],
    daily_rows: pd.DataFrame,
    weight_rows: pd.DataFrame,
    current_date: date,
) -> dict[str, Any]:
    latest_weight = _latest_weight_summary(weight_rows)
    current_weight = latest_weight["latest_weight_kg"]
    today_row = _get_daily_row(daily_rows, current_date)

    bmr = None
    base_tdee = None
    bmi = None
    today_tdee = None
    today_balance = None
    if current_weight is not None:
        try:
            bmi = calculate_bmi(current_weight, profile["height_cm"])
            bmr = calculate_bmr(
                current_weight,
                profile["height_cm"],
                profile["age"],
                profile["gender"],
            )
            base_tdee = calculate_base_tdee(bmr)
            activity_calories = (
                _safe_float(today_row.get("activity_calories_burned"))
                if today_row is not None
                else 0.0
            )
            today_tdee = calculate_estimated_tdee(base_tdee, activity_calories)
            if today_row is not None and bool(today_row.get("has_food_logs")):
                today_balance = calculate_estimated_balance(
                    today_row.get("food_calories_in"), today_tdee
                )
        except (TypeError, ValueError):
            bmi = None
            bmr = None
            base_tdee = None
            today_tdee = None
            today_balance = None

    return {
        "full_name": profile.get("full_name"),
        "height_cm": profile.get("height_cm"),
        "age": profile.get("age"),
        "gender": profile.get("gender"),
        "goal": profile.get("goal"),
        "current_weight_kg": current_weight,
        "current_weight_date": latest_weight["latest_weight_date"],
        "weight_delta_kg": latest_weight["weight_delta_kg"],
        "current_bmi": bmi,
        "current_bmr": bmr,
        "current_base_tdee": base_tdee,
        "today_estimated_tdee": today_tdee,
        "today_has_food_logs": bool(today_row.get("has_food_logs"))
        if today_row is not None
        else False,
        "today_has_activity_logs": bool(today_row.get("has_activity_logs"))
        if today_row is not None
        else False,
        "today_calories_in": today_row.get("food_calories_in")
        if today_row is not None and bool(today_row.get("has_food_logs"))
        else None,
        "today_activity_calories": _safe_float(
            today_row.get("activity_calories_burned")
        )
        if today_row is not None
        else 0.0,
        "today_estimated_balance": today_balance,
    }


def _fetch_user_profile(cur: Any, user_id: int) -> dict[str, Any] | None:
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
        "id": row[0],
        "full_name": row[1],
        "height_cm": row[2],
        "age": row[3],
        "gender": row[4],
        "goal": row[5],
    }


def _fetch_weight_rows(cur: Any, user_id: int) -> pd.DataFrame:
    cur.execute(
        """
        SELECT log_date, weight_kg
        FROM weight_logs
        WHERE user_id = %s
        ORDER BY log_date ASC, id ASC
        """,
        (user_id,),
    )
    return _rows_to_dataframe(cur.fetchall(), ["log_date", "weight_kg"])


def _fetch_daily_log_rows(
    cur: Any, user_id: int, start_date: date, end_date: date
) -> pd.DataFrame:
    cur.execute(
        """
        SELECT
            dl.log_date,
            dl.total_calories_in,
            dl.total_calories_burned AS activity_calories_burned,
            EXISTS (
                SELECT 1 FROM food_logs fl WHERE fl.log_id = dl.id
            ) AS has_food_logs,
            EXISTS (
                SELECT 1 FROM activity_logs al WHERE al.log_id = dl.id
            ) AS has_activity_logs,
            COALESCE((
                SELECT COUNT(*) FROM activity_logs al WHERE al.log_id = dl.id
            ), 0) AS workouts_count
        FROM daily_logs dl
        WHERE dl.user_id = %s
          AND dl.log_date BETWEEN %s AND %s
        ORDER BY dl.log_date ASC
        """,
        (user_id, start_date, end_date),
    )
    return _rows_to_dataframe(
        cur.fetchall(),
        [
            "log_date",
            "total_calories_in",
            "activity_calories_burned",
            "has_food_logs",
            "has_activity_logs",
            "workouts_count",
        ],
    )


def _fetch_macro_rows(
    cur: Any, user_id: int, start_date: date, end_date: date
) -> pd.DataFrame:
    cur.execute(
        """
        SELECT
            dl.log_date,
            ROUND(COALESCE(SUM(CASE
                WHEN fl.food_id IS NOT NULL THEN COALESCE(fi.protein_g, 0) * fl.quantity_g / 100.0
                WHEN fl.custom_meal_id IS NOT NULL THEN fl.snapshot_protein_100g * fl.quantity_g / 100.0
                ELSE 0
            END), 0), 2) AS protein_g,
            ROUND(COALESCE(SUM(CASE
                WHEN fl.food_id IS NOT NULL THEN COALESCE(fi.carbs_g, 0) * fl.quantity_g / 100.0
                WHEN fl.custom_meal_id IS NOT NULL THEN fl.snapshot_carbs_100g * fl.quantity_g / 100.0
                ELSE 0
            END), 0), 2) AS carbs_g,
            ROUND(COALESCE(SUM(CASE
                WHEN fl.food_id IS NOT NULL THEN COALESCE(fi.fats_g, 0) * fl.quantity_g / 100.0
                WHEN fl.custom_meal_id IS NOT NULL THEN fl.snapshot_fats_100g * fl.quantity_g / 100.0
                ELSE 0
            END), 0), 2) AS fats_g
        FROM daily_logs dl
        JOIN food_logs fl ON fl.log_id = dl.id
        LEFT JOIN food_items fi ON fi.id = fl.food_id
        WHERE dl.user_id = %s
          AND dl.log_date BETWEEN %s AND %s
        GROUP BY dl.log_date
        ORDER BY dl.log_date ASC
        """,
        (user_id, start_date, end_date),
    )
    return _rows_to_dataframe(cur.fetchall(), ["log_date", "protein_g", "carbs_g", "fats_g"])


def _fetch_activity_breakdown(
    cur: Any, user_id: int, start_date: date, end_date: date
) -> pd.DataFrame:
    cur.execute(
        """
        WITH activity_rows AS (
            SELECT
                a.category,
                al.duration_min,
                al.sets,
                al.reps,
                al.manual_calories_burned,
                CASE
                    WHEN al.manual_calories_burned IS NOT NULL THEN 'Manual'
                    ELSE 'Estimare MacroSense'
                END AS calculation_method,
                a.met_multiplier,
                COALESCE(past_weight.weight_kg, future_weight.weight_kg, 70.0) AS reference_weight
            FROM daily_logs dl
            JOIN activity_logs al ON al.log_id = dl.id
            JOIN activities a ON a.id = al.activity_id
            LEFT JOIN LATERAL (
                SELECT wl.weight_kg
                FROM weight_logs wl
                WHERE wl.user_id = dl.user_id
                  AND wl.log_date <= dl.log_date
                ORDER BY wl.log_date DESC, wl.id DESC
                LIMIT 1
            ) past_weight ON TRUE
            LEFT JOIN LATERAL (
                SELECT wl.weight_kg
                FROM weight_logs wl
                WHERE wl.user_id = dl.user_id
                  AND wl.log_date > dl.log_date
                ORDER BY wl.log_date ASC, wl.id ASC
                LIMIT 1
            ) future_weight ON past_weight.weight_kg IS NULL
            WHERE dl.user_id = %s
              AND dl.log_date BETWEEN %s AND %s
        )
        SELECT
            COALESCE(category, 'Altele') AS category,
            calculation_method,
            COUNT(*) AS entries_count,
            ROUND(COALESCE(SUM(duration_min), 0), 2) AS total_duration_min,
            ROUND(COALESCE(SUM(CASE
                WHEN manual_calories_burned IS NOT NULL THEN manual_calories_burned
                WHEN category = 'Forță' AND sets IS NOT NULL AND reps IS NOT NULL THEN
                    (met_multiplier * reference_weight *
                        (LEAST(duration_min, (sets * reps * 3.0) / 60.0) / 60.0))
                    +
                    (1.5 * reference_weight *
                        (GREATEST(0, duration_min - ((sets * reps * 3.0) / 60.0)) / 60.0))
                ELSE met_multiplier * reference_weight * (duration_min / 60.0)
            END), 0), 2) AS total_calories_burned
        FROM activity_rows
        GROUP BY category, calculation_method
        ORDER BY total_calories_burned DESC, category ASC
        """,
        (user_id, start_date, end_date),
    )
    return _rows_to_dataframe(
        cur.fetchall(),
        [
            "category",
            "calculation_method",
            "entries_count",
            "total_duration_min",
            "total_calories_burned",
        ],
    )


def _calculate_daily_energy_estimates(
    profile: dict[str, Any], row: pd.Series
) -> dict[str, float | None]:
    reference_weight = row.get("reference_weight_kg")
    if reference_weight is None or pd.isna(reference_weight):
        return _empty_estimate()

    try:
        bmi = calculate_bmi(reference_weight, profile["height_cm"])
        bmr = calculate_bmr(
            reference_weight,
            profile["height_cm"],
            profile["age"],
            profile["gender"],
        )
        base_tdee = calculate_base_tdee(bmr)
        estimated_tdee = calculate_estimated_tdee(
            base_tdee, row.get("activity_calories_burned", 0.0)
        )
        estimated_balance = (
            calculate_estimated_balance(row["food_calories_in"], estimated_tdee)
            if row.get("has_food_logs")
            else None
        )
        return {
            "bmi": bmi,
            "bmr": bmr,
            "base_tdee": base_tdee,
            "estimated_tdee": estimated_tdee,
            "estimated_balance": estimated_balance,
        }
    except (TypeError, ValueError):
        return _empty_estimate()


def _empty_estimate() -> dict[str, None]:
    return {
        "bmi": None,
        "bmr": None,
        "base_tdee": None,
        "estimated_tdee": None,
        "estimated_balance": None,
    }


def _rows_to_dataframe(rows: list[tuple[Any, ...]], columns: list[str]) -> pd.DataFrame:
    dataframe = pd.DataFrame(rows, columns=columns)
    if "log_date" in dataframe.columns and not dataframe.empty:
        dataframe["log_date"] = dataframe["log_date"].apply(_to_date)
    return dataframe


def _filter_by_interval(
    dataframe: pd.DataFrame, date_column: str, start_date: date, end_date: date
) -> pd.DataFrame:
    if dataframe.empty or date_column not in dataframe.columns:
        return dataframe.copy()
    filtered = dataframe.copy()
    filtered[date_column] = filtered[date_column].apply(_to_date)
    return filtered[
        (filtered[date_column] >= start_date) & (filtered[date_column] <= end_date)
    ].reset_index(drop=True)


def _to_date(value: Any) -> date:
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    return value


def _mean_or_none(series: pd.Series | None) -> float | None:
    if series is None:
        return None
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None
    return round(float(values.mean()), 2)


def _sum_or_none(series: pd.Series | None) -> float | None:
    if series is None:
        return None
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None
    return round(float(values.sum()), 2)


def _calculate_average_protein_per_kg(
    macro_rows: pd.DataFrame, daily_rows: pd.DataFrame
) -> float | None:
    if macro_rows.empty or daily_rows.empty:
        return None

    macros = macro_rows.copy()
    macros["log_date"] = macros["log_date"].apply(_to_date)
    macros["protein_g"] = pd.to_numeric(macros["protein_g"], errors="coerce")

    weights = daily_rows[["log_date", "reference_weight_kg"]].copy()
    weights["log_date"] = weights["log_date"].apply(_to_date)
    weights["reference_weight_kg"] = pd.to_numeric(
        weights["reference_weight_kg"], errors="coerce"
    )

    merged = macros.merge(weights, on="log_date", how="left")
    merged = merged.dropna(subset=["protein_g", "reference_weight_kg"])
    merged = merged[merged["reference_weight_kg"] > 0]
    if merged.empty:
        return None

    protein_per_kg = merged["protein_g"] / merged["reference_weight_kg"]
    return round(float(protein_per_kg.mean()), 2)


def _actual_weight_mask(daily_rows: pd.DataFrame) -> pd.Series:
    if daily_rows.empty or "reference_weight_days_distance" not in daily_rows.columns:
        return pd.Series(False, index=daily_rows.index)

    distance = pd.to_numeric(
        daily_rows["reference_weight_days_distance"], errors="coerce"
    )
    return distance.eq(0)


def _count_actual_weight_days(daily_rows: pd.DataFrame) -> int:
    if daily_rows.empty:
        return 0
    return int(_actual_weight_mask(daily_rows).sum())


def _latest_weight_summary(weight_rows: pd.DataFrame) -> dict[str, Any]:
    if weight_rows.empty:
        return {
            "latest_weight_kg": None,
            "latest_weight_date": None,
            "weight_delta_kg": None,
        }

    normalized = weight_rows.copy()
    normalized["log_date"] = normalized["log_date"].apply(_to_date)
    normalized["weight_kg"] = pd.to_numeric(normalized["weight_kg"], errors="coerce")
    normalized = normalized.dropna(subset=["weight_kg"]).sort_values("log_date")
    if normalized.empty:
        return {
            "latest_weight_kg": None,
            "latest_weight_date": None,
            "weight_delta_kg": None,
        }

    latest = normalized.iloc[-1]
    previous = normalized.iloc[-2] if len(normalized) >= 2 else None
    return {
        "latest_weight_kg": round(float(latest["weight_kg"]), 2),
        "latest_weight_date": latest["log_date"],
        "weight_delta_kg": round(
            float(latest["weight_kg"]) - float(previous["weight_kg"]), 2
        )
        if previous is not None
        else None,
    }


def _get_daily_row(daily_rows: pd.DataFrame, target_date: date) -> pd.Series | None:
    if daily_rows.empty or "log_date" not in daily_rows.columns:
        return None

    matching_rows = daily_rows[daily_rows["log_date"].apply(_to_date) == target_date]
    if matching_rows.empty:
        return None
    return matching_rows.iloc[0]


def _safe_float(value: Any) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return float(value)


def _optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)
