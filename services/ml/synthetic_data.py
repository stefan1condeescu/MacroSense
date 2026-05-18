"""Synthetic raw histories for MacroSense ML experiments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import random
from typing import Any

import pandas as pd

from services.analytics.energy import calculate_base_tdee, calculate_bmr


FOOD_NAMES = [
    "Greek yogurt bowl",
    "Chicken rice plate",
    "Turkey sandwich",
    "Oatmeal with fruit",
    "Tuna salad",
    "Egg breakfast",
    "Beef potato bowl",
    "Lentil soup",
    "Protein smoothie",
    "Cottage cheese snack",
    "Salmon potatoes plate",
    "Chicken quinoa salad",
    "Pork tenderloin meal",
    "Tofu vegetable stir fry",
    "Cottage cheese toast",
    "Whole wheat pasta bowl",
    "Rice beans avocado bowl",
    "Skyr fruit snack",
    "Turkey omelette",
    "Lean beef wrap",
    "Chickpea salad",
    "Milk cereal breakfast",
    "Peanut butter banana toast",
    "Vegetable chicken soup",
    "Protein pancakes",
]

CUSTOM_MEAL_NAMES = [
    "Protein bowl",
    "Chicken meal prep",
    "Lean breakfast wrap",
    "High protein pasta",
    "Recovery smoothie",
    "Balanced lunch box",
    "Training day bowl",
    "Light dinner plate",
    "High carb workout meal",
    "Maintenance meal prep",
]

ACTIVITY_OPTIONS = [
    ("Brisk walking", "Cardio", 180, 320),
    ("Easy running", "Cardio", 300, 650),
    ("Cycling", "Cardio", 240, 560),
    ("Strength training", "Forta", 180, 380),
    ("Full body circuit", "Forta", 220, 460),
    ("Mobility session", "Flexibilitate", 60, 180),
    ("Incline treadmill", "Cardio", 220, 520),
    ("Swimming", "Cardio", 260, 620),
    ("Rowing machine", "Cardio", 260, 600),
    ("Upper body strength", "Forta", 150, 340),
    ("Lower body strength", "Forta", 190, 420),
    ("Core workout", "Forta", 100, 260),
    ("Yoga session", "Flexibilitate", 80, 220),
    ("Long walk", "Cardio", 170, 360),
]


@dataclass(frozen=True)
class SyntheticDatasetConfig:
    """Configuration for synthetic user history generation."""

    user_count: int = 120
    history_days: int = 180
    start_date: date = date(2025, 9, 1)
    random_seed: int = 42
    custom_meal_probability: float = 0.22
    min_user_history_days: int = 45
    history_days_jitter: int = 45
    start_date_jitter_days: int = 45
    food_log_calorie_noise: float = 0.06

    def __post_init__(self) -> None:
        if self.user_count <= 0:
            raise ValueError("user_count must be positive.")
        if self.history_days < 45:
            raise ValueError("history_days must be at least 45.")
        if not 0 <= self.custom_meal_probability <= 1:
            raise ValueError("custom_meal_probability must be between 0 and 1.")
        if self.min_user_history_days < 45:
            raise ValueError("min_user_history_days must be at least 45.")
        if self.min_user_history_days > self.history_days:
            raise ValueError("min_user_history_days cannot exceed history_days.")
        if self.history_days_jitter < 0:
            raise ValueError("history_days_jitter cannot be negative.")
        if self.start_date_jitter_days < 0:
            raise ValueError("start_date_jitter_days cannot be negative.")
        if self.food_log_calorie_noise < 0:
            raise ValueError("food_log_calorie_noise cannot be negative.")


@dataclass(frozen=True)
class SyntheticHistories:
    """Raw synthetic histories shaped like simplified app logs."""

    profile_rows: pd.DataFrame
    food_rows: pd.DataFrame
    activity_rows: pd.DataFrame
    weight_rows: pd.DataFrame

    def as_dict(self) -> dict[str, pd.DataFrame]:
        return {
            "profile_rows": self.profile_rows,
            "food_rows": self.food_rows,
            "activity_rows": self.activity_rows,
            "weight_rows": self.weight_rows,
        }


def generate_synthetic_histories(
    config: SyntheticDatasetConfig | None = None,
) -> SyntheticHistories:
    """Generate raw user histories for ML training and validation."""

    cfg = config or SyntheticDatasetConfig()
    rng = random.Random(cfg.random_seed)

    profile_records: list[dict[str, Any]] = []
    food_records: list[dict[str, Any]] = []
    activity_records: list[dict[str, Any]] = []
    weight_records: list[dict[str, Any]] = []

    for user_id in range(1, cfg.user_count + 1):
        user_profile = _generate_user_profile(rng, user_id)
        user_start_date = cfg.start_date + timedelta(
            days=rng.randint(0, cfg.start_date_jitter_days)
        )
        max_history_jitter = min(
            cfg.history_days_jitter,
            cfg.history_days - cfg.min_user_history_days,
        )
        user_history_days = cfg.history_days - rng.randint(0, max_history_jitter)
        user_profile["profile"].update(
            {
                "history_start_date": user_start_date,
                "history_days": user_history_days,
            }
        )
        profile_records.append(user_profile["profile"])

        simulated_weight = user_profile["start_weight_kg"]
        goal_balance = user_profile["goal_balance"]
        calorie_reporting_bias = user_profile["calorie_reporting_bias"]
        food_logging_probability = user_profile["food_logging_probability"]
        weight_logging_probability = user_profile["weight_logging_probability"]
        workout_probability = user_profile["workout_probability"]
        protein_per_kg_target = user_profile["protein_per_kg_target"]

        for day_index in range(user_history_days):
            current_date = user_start_date + timedelta(days=day_index)
            activity_calories, day_activity_records = _generate_activity_day(
                rng, user_id, current_date, workout_probability
            )
            activity_records.extend(day_activity_records)

            base_tdee = _calculate_base_tdee_for_profile(
                user_profile["profile"],
                simulated_weight,
            )
            actual_calories_in = max(
                900.0,
                base_tdee
                + activity_calories
                + goal_balance
                + rng.gauss(0, 220),
            )

            if rng.random() <= food_logging_probability:
                logged_calories_in = _apply_food_log_noise(
                    rng,
                    actual_calories_in,
                    calorie_reporting_bias,
                    cfg.food_log_calorie_noise,
                )
                food_records.extend(
                    _generate_food_day(
                        rng,
                        user_id,
                        current_date,
                        logged_calories_in,
                        simulated_weight,
                        protein_per_kg_target,
                        cfg.custom_meal_probability,
                    )
                )

            daily_balance = actual_calories_in - (base_tdee + activity_calories)
            simulated_weight = _next_weight(rng, simulated_weight, daily_balance)

            should_log_weight = (
                day_index == 0
                or day_index == user_history_days - 1
                or current_date.weekday() == 0
                or rng.random() <= weight_logging_probability
            )
            if should_log_weight:
                weight_records.append(
                    {
                        "user_id": user_id,
                        "log_date": current_date,
                        "weight_kg": round(simulated_weight + rng.gauss(0, 0.18), 2),
                    }
                )

    return SyntheticHistories(
        profile_rows=pd.DataFrame(profile_records),
        food_rows=pd.DataFrame(food_records),
        activity_rows=pd.DataFrame(activity_records),
        weight_rows=pd.DataFrame(weight_records),
    )


def _generate_user_profile(rng: random.Random, user_id: int) -> dict[str, Any]:
    gender = rng.choice(["M", "F"])
    if gender == "M":
        height_cm = round(rng.uniform(168, 192), 1)
        bmi = rng.uniform(23, 32)
    else:
        height_cm = round(rng.uniform(155, 178), 1)
        bmi = rng.uniform(21, 31)

    start_weight_kg = round(bmi * ((height_cm / 100) ** 2), 2)
    goal = rng.choices(
        ["Slabire", "Mentinere", "Crestere"],
        weights=[0.5, 0.3, 0.2],
        k=1,
    )[0]
    goal_balance = {
        "Slabire": rng.uniform(-520, -220),
        "Mentinere": rng.uniform(-120, 120),
        "Crestere": rng.uniform(180, 420),
    }[goal]

    profile = {
        "user_id": user_id,
        "full_name": f"Synthetic User {user_id}",
        "height_cm": height_cm,
        "age": rng.randint(20, 55),
        "gender": gender,
        "goal": goal,
        "start_weight_kg": start_weight_kg,
    }

    return {
        "profile": profile,
        "start_weight_kg": start_weight_kg,
        "goal_balance": goal_balance,
        "food_logging_probability": rng.uniform(0.62, 0.94),
        "weight_logging_probability": rng.uniform(0.12, 0.45),
        "workout_probability": rng.uniform(0.18, 0.65),
        "protein_per_kg_target": rng.uniform(1.1, 2.0),
        "calorie_reporting_bias": max(-0.14, min(0.1, rng.gauss(-0.025, 0.045))),
    }


def _generate_activity_day(
    rng: random.Random,
    user_id: int,
    log_date: date,
    workout_probability: float,
) -> tuple[float, list[dict[str, Any]]]:
    if rng.random() > workout_probability:
        return 0.0, []

    activity_name, category, min_calories, max_calories = rng.choice(ACTIVITY_OPTIONS)
    duration_min = round(rng.uniform(20, 75), 1)
    calories_burned = round(rng.uniform(min_calories, max_calories), 2)
    return calories_burned, [
        {
            "user_id": user_id,
            "log_date": log_date,
            "activity_name": activity_name,
            "category": category,
            "duration_min": duration_min,
            "calories_burned": calories_burned,
        }
    ]


def _generate_food_day(
    rng: random.Random,
    user_id: int,
    log_date: date,
    total_calories: float,
    weight_kg: float,
    protein_per_kg_target: float,
    custom_meal_probability: float,
) -> list[dict[str, Any]]:
    meal_types = ["Mic dejun", "Pranz", "Cina", "Gustare"]
    meal_count = rng.choices([2, 3, 4], weights=[0.18, 0.62, 0.2], k=1)[0]
    selected_meals = meal_types[:meal_count]
    portions = _random_portions(rng, meal_count)

    protein_total = max(45.0, weight_kg * protein_per_kg_target + rng.gauss(0, 12))
    fat_calories_share = rng.uniform(0.22, 0.34)
    fats_total = max(25.0, (total_calories * fat_calories_share) / 9)
    carbs_total = max(35.0, (total_calories - protein_total * 4 - fats_total * 9) / 4)

    records: list[dict[str, Any]] = []
    for meal_type, portion in zip(selected_meals, portions):
        is_custom_meal = rng.random() <= custom_meal_probability
        records.append(
            {
                "user_id": user_id,
                "log_date": log_date,
                "meal_type": meal_type,
                "food_name": rng.choice(CUSTOM_MEAL_NAMES)
                if is_custom_meal
                else rng.choice(FOOD_NAMES),
                "source_type": "custom_meal" if is_custom_meal else "catalog_food",
                "calories": round(total_calories * portion, 2),
                "protein_g": round(protein_total * portion, 2),
                "carbs_g": round(carbs_total * portion, 2),
                "fats_g": round(fats_total * portion, 2),
            }
        )
    return records


def _random_portions(rng: random.Random, count: int) -> list[float]:
    raw_values = [rng.uniform(0.65, 1.35) for _ in range(count)]
    total = sum(raw_values)
    return [value / total for value in raw_values]


def _calculate_base_tdee_for_profile(
    profile: dict[str, Any], weight_kg: float
) -> float:
    bmr = calculate_bmr(
        weight_kg,
        profile["height_cm"],
        profile["age"],
        profile["gender"],
    )
    return calculate_base_tdee(bmr)


def _apply_food_log_noise(
    rng: random.Random,
    actual_calories_in: float,
    user_reporting_bias: float,
    daily_noise: float,
) -> float:
    reporting_multiplier = 1.0 + user_reporting_bias + rng.gauss(0, daily_noise)
    reporting_multiplier = max(0.72, min(1.18, reporting_multiplier))
    return max(900.0, actual_calories_in * reporting_multiplier)


def _next_weight(
    rng: random.Random, current_weight_kg: float, daily_balance: float
) -> float:
    adherence_and_water_response = rng.uniform(0.55, 0.85)
    expected_change = (daily_balance / 7700.0) * adherence_and_water_response
    water_noise = rng.gauss(0, 0.07)
    next_weight = current_weight_kg + expected_change + water_noise
    return max(40.0, min(180.0, next_weight))
