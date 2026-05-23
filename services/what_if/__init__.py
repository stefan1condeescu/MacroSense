"""Read-only What-if simulation helpers for MacroSense."""

from services.what_if.simulator import (
    WhatIfActivityEntry,
    WhatIfComparison,
    WhatIfFoodEntry,
    WhatIfTotals,
    build_activity_entry,
    build_custom_meal_entry,
    build_food_entry,
    calculate_repeated_daily_weight_impact,
    calculate_totals,
    compare_totals,
    describe_balance_delta,
    scenario_matches_real_day,
)

__all__ = [
    "WhatIfActivityEntry",
    "WhatIfComparison",
    "WhatIfFoodEntry",
    "WhatIfTotals",
    "build_activity_entry",
    "build_custom_meal_entry",
    "build_food_entry",
    "calculate_repeated_daily_weight_impact",
    "calculate_totals",
    "compare_totals",
    "describe_balance_delta",
    "scenario_matches_real_day",
]
