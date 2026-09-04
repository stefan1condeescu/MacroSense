from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd

from models.tracking import ActivityLog
from services.analytics.energy import calculate_estimated_balance, calculate_estimated_tdee


MIN_QUANTITY_G = 1.0
MAX_QUANTITY_G = 5000.0
WEIGHT_CHANGE_KCAL_PER_KG = 7700.0


@dataclass(frozen=True)
class WhatIfFoodEntry:
    entry_id: str
    label: str
    entry_type: str
    quantity_g: float
    calories: float
    protein_g: float
    carbs_g: float
    fats_g: float
    source_label: str = "MacroSense"
    is_existing: bool = False


@dataclass(frozen=True)
class WhatIfActivityEntry:
    entry_id: str
    label: str
    category: str
    duration_min: float
    calories_burned: float
    met: float
    sets: int | None = None
    reps: int | None = None
    manual_calories_burned: float | None = None
    source_label: str = "MacroSense"
    is_existing: bool = False


@dataclass(frozen=True)
class WhatIfTotals:
    calories_in: float = 0.0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fats_g: float = 0.0
    activity_calories: float = 0.0
    estimated_tdee: float = 0.0
    estimated_balance: float | None = None
    has_food_entries: bool = False


@dataclass(frozen=True)
class WhatIfComparison:
    real: WhatIfTotals
    simulated: WhatIfTotals
    difference: WhatIfTotals


def build_food_entry(
    *,
    entry_id: str,
    label: str,
    entry_type: str,
    quantity_g: Any,
    calories_100g: Any,
    protein_100g: Any,
    carbs_100g: Any,
    fats_100g: Any,
    source_label: str = "MacroSense",
    is_existing: bool = False,
) -> WhatIfFoodEntry:
    """Builds one validated food scenario row without touching persistence."""
    quantity = _validate_quantity_g(quantity_g)
    calories_per_100g = _as_non_negative_float(calories_100g, "calories_100g")
    protein_per_100g = _as_non_negative_float(protein_100g, "protein_100g")
    carbs_per_100g = _as_non_negative_float(carbs_100g, "carbs_100g")
    fats_per_100g = _as_non_negative_float(fats_100g, "fats_100g")

    return WhatIfFoodEntry(
        entry_id=str(entry_id),
        label=str(label or "Aliment"),
        entry_type=str(entry_type or "Aliment"),
        quantity_g=round(quantity, 2),
        calories=calories_per_100g * quantity / 100.0,
        protein_g=protein_per_100g * quantity / 100.0,
        carbs_g=carbs_per_100g * quantity / 100.0,
        fats_g=fats_per_100g * quantity / 100.0,
        source_label=str(source_label or "MacroSense"),
        is_existing=bool(is_existing),
    )


def build_custom_meal_entry(
    *,
    entry_id: str,
    meal: dict[str, Any],
    quantity_g: Any,
    is_existing: bool = False,
) -> WhatIfFoodEntry:
    """Builds one food row from the current totals of a custom meal."""
    meal_quantity_g = _as_positive_float(meal.get("quantity_g"), "meal.quantity_g")
    factor = 100.0 / meal_quantity_g
    return build_food_entry(
        entry_id=entry_id,
        label=meal.get("recipe_name") or meal.get("name") or "Masă personalizată",
        entry_type="Masă personalizată",
        quantity_g=quantity_g,
        calories_100g=_as_non_negative_float(meal.get("calories"), "meal.calories") * factor,
        protein_100g=_as_non_negative_float(meal.get("protein_g"), "meal.protein_g") * factor,
        carbs_100g=_as_non_negative_float(meal.get("carbs_g"), "meal.carbs_g") * factor,
        fats_100g=_as_non_negative_float(meal.get("fats_g"), "meal.fats_g") * factor,
        source_label="Masă personalizată",
        is_existing=is_existing,
    )


def build_activity_entry(
    *,
    entry_id: str,
    label: str,
    category: str,
    duration_min: Any,
    met: Any,
    weight_kg: Any,
    sets: Any = None,
    reps: Any = None,
    manual_calories_burned: Any = None,
    source_label: str = "MacroSense",
    is_existing: bool = False,
) -> WhatIfActivityEntry:
    """Builds one validated activity scenario row without touching persistence."""
    ActivityLog.validate_duration(duration_min)
    duration = _as_positive_float(duration_min, "duration_min")
    met_value = _as_positive_float(met, "met")
    weight = _as_positive_float(weight_kg, "weight_kg")
    validated_manual = _validate_manual_calories(manual_calories_burned)
    validated_sets, validated_reps = _validate_sets_and_reps(sets, reps)

    if validated_manual is not None:
        calories = validated_manual
    else:
        calories = _calculate_activity_calories_raw(
            category,
            met_value,
            weight,
            duration,
            validated_sets,
            validated_reps,
        )

    return WhatIfActivityEntry(
        entry_id=str(entry_id),
        label=str(label or "Activitate"),
        category=str(category or "Altele"),
        duration_min=round(duration, 2),
        calories_burned=calories,
        met=round(met_value, 2),
        sets=validated_sets,
        reps=validated_reps,
        manual_calories_burned=validated_manual,
        source_label=str(source_label or "MacroSense"),
        is_existing=bool(is_existing),
    )


def calculate_totals(
    food_entries: Iterable[WhatIfFoodEntry],
    activity_entries: Iterable[WhatIfActivityEntry],
    base_tdee: Any,
) -> WhatIfTotals:
    """Calculates deterministic daily totals for a real or simulated scenario."""
    food_entries = list(food_entries)
    activity_entries = list(activity_entries)
    has_food_entries = bool(food_entries)
    calories_in = _sum_entry_values(food_entries, "calories")
    activity_calories = _sum_entry_values(activity_entries, "calories_burned")
    estimated_tdee = calculate_estimated_tdee(base_tdee, activity_calories)
    return WhatIfTotals(
        calories_in=calories_in,
        protein_g=_sum_entry_values(food_entries, "protein_g"),
        carbs_g=_sum_entry_values(food_entries, "carbs_g"),
        fats_g=_sum_entry_values(food_entries, "fats_g"),
        activity_calories=activity_calories,
        estimated_tdee=estimated_tdee,
        estimated_balance=(
            calculate_estimated_balance(calories_in, estimated_tdee)
            if has_food_entries
            else None
        ),
        has_food_entries=has_food_entries,
    )


def compare_totals(real: WhatIfTotals, simulated: WhatIfTotals) -> WhatIfComparison:
    """Compares the simulated scenario against the unchanged real day."""
    return WhatIfComparison(
        real=real,
        simulated=simulated,
        difference=WhatIfTotals(
            calories_in=round(simulated.calories_in - real.calories_in, 2),
            protein_g=round(simulated.protein_g - real.protein_g, 2),
            carbs_g=round(simulated.carbs_g - real.carbs_g, 2),
            fats_g=round(simulated.fats_g - real.fats_g, 2),
            activity_calories=round(simulated.activity_calories - real.activity_calories, 2),
            estimated_tdee=round(simulated.estimated_tdee - real.estimated_tdee, 2),
            estimated_balance=_calculate_optional_difference(
                real.estimated_balance,
                simulated.estimated_balance,
            ),
            has_food_entries=real.has_food_entries and simulated.has_food_entries,
        ),
    )


def scenario_matches_real_day(
    comparison: WhatIfComparison,
    tolerance: float = 0.05,
) -> bool:
    """Returns True when the simulated scenario is effectively unchanged."""
    differences = comparison.difference
    values = [
        differences.calories_in,
        differences.protein_g,
        differences.carbs_g,
        differences.fats_g,
        differences.activity_calories,
        differences.estimated_tdee,
    ]
    if differences.estimated_balance is not None:
        values.append(differences.estimated_balance)
    return all(abs(value) <= tolerance for value in values)


def calculate_repeated_daily_weight_impact(
    daily_balance_delta_kcal: Any,
    days: int,
) -> float:
    """Returns the theoretical kg impact if the same daily delta repeats."""
    if days <= 0:
        raise ValueError("days must be positive")
    balance_delta = _as_float(daily_balance_delta_kcal, "daily_balance_delta_kcal")
    return round((balance_delta * days) / WEIGHT_CHANGE_KCAL_PER_KG, 2)


def describe_balance_delta(daily_balance_delta_kcal: Any) -> str:
    """Builds a short English source-text interpretation of the balance change."""
    if daily_balance_delta_kcal is None:
        return (
            "The estimated balance cannot be compared because food data is missing "
            "from the real day or the scenario."
        )
    balance_delta = _as_float(daily_balance_delta_kcal, "daily_balance_delta_kcal")
    if abs(balance_delta) <= 0.05:
        return "The estimated balance remains unchanged compared with the real values."
    if balance_delta <= -100:
        return "The scenario lowers the estimated balance and moves further toward a deficit."
    if balance_delta >= 100:
        return "The scenario raises the estimated balance and moves further toward a surplus."
    return "The scenario changes the estimated balance only slightly compared with the real values."


def _validate_quantity_g(value: Any) -> float:
    quantity = _as_float(value, "quantity_g")
    if quantity < MIN_QUANTITY_G:
        raise ValueError(f"quantity_g must be at least {MIN_QUANTITY_G:.0f}")
    if quantity > MAX_QUANTITY_G:
        raise ValueError(f"quantity_g must be at most {MAX_QUANTITY_G:.0f}")
    return quantity


def _validate_manual_calories(value: Any) -> float | None:
    if value is None or value == "":
        return None
    ActivityLog.validate_manual_calories(value)
    return round(_as_positive_float(value, "manual_calories_burned"), 2)


def _validate_sets_and_reps(sets: Any, reps: Any) -> tuple[int | None, int | None]:
    normalized_sets = _normalize_optional_int(sets, "sets")
    normalized_reps = _normalize_optional_int(reps, "reps")
    ActivityLog.validate_sets_and_reps(normalized_sets, normalized_reps)
    return normalized_sets, normalized_reps


def _calculate_activity_calories_raw(
    category: str,
    met: float,
    weight_kg: float,
    duration_min: float,
    sets: int | None,
    reps: int | None,
) -> float:
    if category == "Forță" and sets is not None and reps is not None:
        active_time = min(duration_min, (sets * reps * 3.0) / 60.0)
        rest_time = max(0, duration_min - active_time)
        return (met * weight_kg * (active_time / 60.0)) + (
            1.5 * weight_kg * (rest_time / 60.0)
        )
    return met * weight_kg * (duration_min / 60.0)


def _normalize_optional_int(value: Any, field_name: str) -> int | None:
    if value in (None, "", "-"):
        return None
    numeric_value = _as_float(value, field_name)
    if not numeric_value.is_integer():
        raise ValueError(f"{field_name} must be a whole number")
    return int(numeric_value)


def _sum_entry_values(entries: Iterable[Any], field_name: str) -> float:
    total = 0.0
    for entry in entries:
        total += _as_float(getattr(entry, field_name), field_name)
    return round(total, 2)


def _calculate_optional_difference(
    real_value: float | None,
    simulated_value: float | None,
) -> float | None:
    if real_value is None or simulated_value is None:
        return None
    return round(simulated_value - real_value, 2)


def _as_positive_float(value: Any, field_name: str) -> float:
    numeric_value = _as_float(value, field_name)
    if numeric_value <= 0:
        raise ValueError(f"{field_name} must be positive")
    return numeric_value


def _as_non_negative_float(value: Any, field_name: str) -> float:
    numeric_value = _as_float(value, field_name)
    if numeric_value < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return numeric_value


def _as_float(value: Any, field_name: str) -> float:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if pd.isna(numeric_value):
        raise ValueError(f"{field_name} must be numeric")
    return numeric_value
