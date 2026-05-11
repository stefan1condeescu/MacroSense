"""Analytics helpers used by dashboard and future ML modules."""

from services.analytics.energy import (
    SEDENTARY_ACTIVITY_FACTOR,
    calculate_base_tdee,
    calculate_bmi,
    calculate_bmr,
    calculate_estimated_balance,
    calculate_estimated_tdee,
)

__all__ = [
    "SEDENTARY_ACTIVITY_FACTOR",
    "calculate_base_tdee",
    "calculate_bmi",
    "calculate_bmr",
    "calculate_estimated_balance",
    "calculate_estimated_tdee",
]
