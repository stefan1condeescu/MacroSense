from datetime import date
import unittest

import pandas as pd

from services.analytics.dashboard_data import (
    find_reference_weight,
    find_past_reference_weight_info,
    find_reference_weight_info,
    prepare_daily_analytics,
    summarize_dashboard,
)


class DashboardDataTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "id": 1,
            "full_name": "Test User",
            "height_cm": 180,
            "age": 25,
            "gender": "M",
            "goal": "Mentinere",
        }
        self.weight_rows = pd.DataFrame(
            [
                {"log_date": date(2026, 5, 3), "weight_kg": 81.0},
                {"log_date": date(2026, 5, 7), "weight_kg": 80.0},
            ]
        )

    def test_reference_weight_uses_latest_past_weight(self):
        result = find_reference_weight(self.weight_rows, date(2026, 5, 8))

        self.assertEqual(result, 80.0)

    def test_reference_weight_info_marks_past_imputation(self):
        result = find_reference_weight_info(self.weight_rows, date(2026, 5, 8))

        self.assertEqual(result["reference_weight_kg"], 80.0)
        self.assertEqual(result["reference_weight_source_date"], date(2026, 5, 7))
        self.assertTrue(result["reference_weight_is_imputed"])
        self.assertFalse(result["reference_weight_uses_future_reference"])
        self.assertEqual(result["reference_weight_days_distance"], 1)

    def test_reference_weight_uses_first_future_weight_when_no_past_exists(self):
        result = find_reference_weight(self.weight_rows, date(2026, 5, 1))

        self.assertEqual(result, 81.0)

    def test_reference_weight_info_marks_future_fallback(self):
        result = find_reference_weight_info(self.weight_rows, date(2026, 5, 1))

        self.assertEqual(result["reference_weight_kg"], 81.0)
        self.assertEqual(result["reference_weight_source_date"], date(2026, 5, 3))
        self.assertTrue(result["reference_weight_is_imputed"])
        self.assertTrue(result["reference_weight_uses_future_reference"])
        self.assertEqual(result["reference_weight_days_distance"], 2)

    def test_past_reference_weight_info_never_uses_future_weight(self):
        result = find_past_reference_weight_info(self.weight_rows, date(2026, 5, 1))

        self.assertIsNone(result["reference_weight_kg"])
        self.assertFalse(result["reference_weight_uses_future_reference"])

    def test_reference_weight_returns_none_without_weight_history(self):
        result = find_reference_weight(pd.DataFrame(), date(2026, 5, 1))

        self.assertIsNone(result)

    def test_activity_only_day_does_not_count_as_zero_food_day(self):
        daily_log_rows = pd.DataFrame(
            [
                {
                    "log_date": date(2026, 5, 4),
                    "total_calories_in": 0,
                    "activity_calories_burned": 300,
                    "has_food_logs": False,
                    "has_activity_logs": True,
                    "workouts_count": 1,
                }
            ]
        )

        daily_rows = prepare_daily_analytics(
            self.profile,
            daily_log_rows,
            self.weight_rows,
            date(2026, 5, 4),
            date(2026, 5, 4),
        )

        self.assertTrue(daily_rows.loc[0, "has_activity_logs"])
        self.assertFalse(daily_rows.loc[0, "has_food_logs"])
        self.assertTrue(pd.isna(daily_rows.loc[0, "food_calories_in"]))
        self.assertTrue(pd.isna(daily_rows.loc[0, "estimated_balance"]))
        self.assertFalse(pd.isna(daily_rows.loc[0, "estimated_tdee"]))

    def test_prepare_daily_analytics_returns_one_row_per_calendar_day(self):
        daily_log_rows = pd.DataFrame(
            [
                {
                    "log_date": date(2026, 5, 4),
                    "total_calories_in": 2000,
                    "activity_calories_burned": 0,
                    "has_food_logs": True,
                    "has_activity_logs": False,
                    "workouts_count": 0,
                },
                {
                    "log_date": date(2026, 5, 6),
                    "total_calories_in": 0,
                    "activity_calories_burned": 300,
                    "has_food_logs": False,
                    "has_activity_logs": True,
                    "workouts_count": 1,
                },
            ]
        )

        daily_rows = prepare_daily_analytics(
            self.profile,
            daily_log_rows,
            self.weight_rows,
            date(2026, 5, 3),
            date(2026, 5, 9),
        )

        self.assertEqual(daily_rows.shape[0], 7)
        self.assertEqual(daily_rows["log_date"].nunique(), 7)
        self.assertEqual(daily_rows["has_food_logs"].sum(), 1)
        self.assertEqual(daily_rows["has_activity_logs"].sum(), 1)

    def test_daily_bmr_uses_reference_weight_for_each_day(self):
        daily_rows = prepare_daily_analytics(
            self.profile,
            pd.DataFrame(),
            self.weight_rows,
            date(2026, 5, 6),
            date(2026, 5, 8),
        )

        first_day = daily_rows[daily_rows["log_date"] == date(2026, 5, 6)].iloc[0]
        second_day = daily_rows[daily_rows["log_date"] == date(2026, 5, 7)].iloc[0]
        third_day = daily_rows[daily_rows["log_date"] == date(2026, 5, 8)].iloc[0]

        self.assertEqual(first_day["reference_weight_kg"], 81.0)
        self.assertEqual(first_day["reference_weight_source_date"], date(2026, 5, 3))
        self.assertTrue(first_day["reference_weight_is_imputed"])
        self.assertFalse(first_day["reference_weight_uses_future_reference"])
        self.assertEqual(first_day["reference_weight_days_distance"], 3)
        self.assertEqual(first_day["bmr"], 1815.0)
        self.assertEqual(second_day["reference_weight_kg"], 80.0)
        self.assertEqual(second_day["reference_weight_source_date"], date(2026, 5, 7))
        self.assertFalse(second_day["reference_weight_is_imputed"])
        self.assertFalse(second_day["reference_weight_uses_future_reference"])
        self.assertEqual(second_day["reference_weight_days_distance"], 0)
        self.assertEqual(second_day["bmr"], 1805.0)
        self.assertEqual(third_day["reference_weight_kg"], 80.0)
        self.assertEqual(third_day["bmr"], 1805.0)

    def test_dashboard_summary_averages_calories_only_on_food_days(self):
        daily_log_rows = pd.DataFrame(
            [
                {
                    "log_date": date(2026, 5, 4),
                    "total_calories_in": 2000,
                    "activity_calories_burned": 0,
                    "has_food_logs": True,
                    "has_activity_logs": False,
                    "workouts_count": 0,
                },
                {
                    "log_date": date(2026, 5, 5),
                    "total_calories_in": 0,
                    "activity_calories_burned": 300,
                    "has_food_logs": False,
                    "has_activity_logs": True,
                    "workouts_count": 1,
                },
            ]
        )
        daily_rows = prepare_daily_analytics(
            self.profile,
            daily_log_rows,
            self.weight_rows,
            date(2026, 5, 4),
            date(2026, 5, 5),
        )

        summary = summarize_dashboard(
            self.profile,
            daily_rows,
            self.weight_rows,
            pd.DataFrame(),
            pd.DataFrame(),
            2,
        )

        self.assertEqual(summary["avg_calories_in"], 2000.0)
        self.assertEqual(summary["logged_days"], 2)
        self.assertEqual(summary["logging_consistency"], 100.0)
        self.assertEqual(summary["food_logging_consistency"], 50.0)
        self.assertEqual(summary["activity_logging_consistency"], 50.0)
        self.assertEqual(summary["weight_logging_consistency"], 0.0)
        self.assertEqual(summary["overall_logging_consistency"], 100.0)
        self.assertEqual(summary["workouts_count"], 1)

    def test_dashboard_summary_calculates_average_protein_per_kg(self):
        daily_log_rows = pd.DataFrame(
            [
                {
                    "log_date": date(2026, 5, 4),
                    "total_calories_in": 2000,
                    "activity_calories_burned": 0,
                    "has_food_logs": True,
                    "has_activity_logs": False,
                    "workouts_count": 0,
                },
                {
                    "log_date": date(2026, 5, 5),
                    "total_calories_in": 2100,
                    "activity_calories_burned": 0,
                    "has_food_logs": True,
                    "has_activity_logs": False,
                    "workouts_count": 0,
                },
            ]
        )
        weight_rows = pd.DataFrame(
            [
                {"log_date": date(2026, 5, 4), "weight_kg": 100.0},
                {"log_date": date(2026, 5, 5), "weight_kg": 100.0},
            ]
        )
        macro_rows = pd.DataFrame(
            [
                {"log_date": date(2026, 5, 4), "protein_g": 100, "carbs_g": 200, "fats_g": 50},
                {"log_date": date(2026, 5, 5), "protein_g": 140, "carbs_g": 210, "fats_g": 55},
            ]
        )
        daily_rows = prepare_daily_analytics(
            self.profile,
            daily_log_rows,
            weight_rows,
            date(2026, 5, 4),
            date(2026, 5, 5),
        )

        summary = summarize_dashboard(
            self.profile,
            daily_rows,
            weight_rows,
            macro_rows,
            pd.DataFrame(),
            2,
        )

        self.assertEqual(summary["avg_protein_per_kg"], 1.2)
        self.assertEqual(summary["weight_logging_consistency"], 100.0)


if __name__ == "__main__":
    unittest.main()
