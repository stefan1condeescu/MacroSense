"""Pure energy formulas for dashboard analytics."""

SEDENTARY_ACTIVITY_FACTOR = 1.2


def _require_positive(value: float, field_name: str) -> float:
    numeric_value = float(value)
    if numeric_value <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return numeric_value


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    weight = _require_positive(weight_kg, "weight_kg")
    height = _require_positive(height_cm, "height_cm")
    height_m = height / 100
    return round(weight / (height_m**2), 2)


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    weight = _require_positive(weight_kg, "weight_kg")
    height = _require_positive(height_cm, "height_cm")
    age_value = _require_positive(age, "age")

    normalized_gender = str(gender).strip().upper()
    if normalized_gender == "M":
        return round(10 * weight + 6.25 * height - 5 * age_value + 5, 2)
    if normalized_gender == "F":
        return round(10 * weight + 6.25 * height - 5 * age_value - 161, 2)

    raise ValueError("gender must be 'M' or 'F'.")


def calculate_base_tdee(
    bmr: float, sedentary_factor: float = SEDENTARY_ACTIVITY_FACTOR
) -> float:
    bmr_value = _require_positive(bmr, "bmr")
    factor = _require_positive(sedentary_factor, "sedentary_factor")
    return round(bmr_value * factor, 2)


def calculate_estimated_tdee(
    base_tdee: float, activity_calories_burned: float = 0.0
) -> float:
    base_value = _require_positive(base_tdee, "base_tdee")
    activity_value = 0.0 if activity_calories_burned is None else float(activity_calories_burned)
    if activity_value < 0:
        raise ValueError("activity_calories_burned cannot be negative.")
    return round(base_value + activity_value, 2)


def calculate_estimated_balance(
    total_calories_in: float, estimated_tdee: float
) -> float:
    calories_in = float(total_calories_in)
    tdee = _require_positive(estimated_tdee, "estimated_tdee")
    return round(calories_in - tdee, 2)
