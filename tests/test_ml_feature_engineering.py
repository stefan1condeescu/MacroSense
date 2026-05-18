from datetime import date
import unittest

import pandas as pd

from services.ml.feature_engineering import (
    WeightPredictionFeatureConfig,
    build_default_weight_prediction_feature_config,
    build_weight_prediction_dataset,
    build_weight_prediction_feature_row,
)


class MLFeatureEngineeringTests(unittest.TestCase):
    def setUp(self):
        self.profiles = pd.DataFrame(
            [
                {
                    "id": 1,
                    "height_cm": 180,
                    "age": 30,
                    "gender": "M",
                    "goal": "Slabire",
                }
            ]
        )
        self.profile = {
            "user_id": 1,
            "height_cm": 180,
            "age": 30,
            "gender": "M",
            "goal": "Slabire",
        }
        self.weight_rows = pd.DataFrame(
            [
                {"user_id": 1, "log_date": date(2026, 5, 1), "weight_kg": 80.0},
                {"user_id": 1, "log_date": date(2026, 5, 8), "weight_kg": 79.6},
                {"user_id": 1, "log_date": date(2026, 5, 14), "weight_kg": 79.2},
                {"user_id": 1, "log_date": date(2026, 5, 28), "weight_kg": 78.5},
                {"user_id": 1, "log_date": date(2026, 6, 13), "weight_kg": 78.0},
            ]
        )
        food_days = [1, 2, 3, 4, 6, 7, 8, 10, 11, 12]
        self.food_rows = pd.DataFrame(
            [
                {
                    "user_id": 1,
                    "log_date": date(2026, 5, day),
                    "calories": 2000,
                    "protein_g": 100,
                    "carbs_g": 220,
                    "fats_g": 60,
                }
                for day in food_days
            ]
        )
        self.activity_rows = pd.DataFrame(
            [
                {
                    "user_id": 1,
                    "log_date": date(2026, 5, 2),
                    "calories_burned": 300,
                },
                {
                    "user_id": 1,
                    "log_date": date(2026, 5, 4),
                    "calories_burned": 200,
                },
                {
                    "user_id": 1,
                    "log_date": date(2026, 5, 6),
                    "calories_burned": 100,
                },
            ]
        )

    def test_default_feature_config_uses_horizon_sized_windows(self):
        config_14d = build_default_weight_prediction_feature_config(14)
        config_30d = build_default_weight_prediction_feature_config(30)

        self.assertEqual(config_14d.feature_window_days, 14)
        self.assertEqual(config_14d.min_food_days, 7)
        self.assertEqual(config_14d.min_weight_days, 2)
        self.assertEqual(config_30d.feature_window_days, 30)
        self.assertEqual(config_30d.min_food_days, 14)
        self.assertEqual(config_30d.min_weight_days, 3)

    def test_feature_row_uses_logged_food_days_and_rest_activity_days(self):
        config = WeightPredictionFeatureConfig(
            horizon_days=14,
            feature_window_days=14,
            min_food_days=7,
            min_weight_days=2,
        )

        row = build_weight_prediction_feature_row(
            self.profile,
            self.food_rows,
            self.activity_rows,
            self.weight_rows,
            date(2026, 5, 14),
            config,
        )

        self.assertIsNotNone(row)
        self.assertEqual(row["current_weight_kg"], 79.2)
        self.assertEqual(row["current_weight_source_date"], date(2026, 5, 14))
        self.assertEqual(row["food_days"], 10)
        self.assertEqual(row["food_consistency"], 0.714)
        self.assertEqual(row["calories_avg_logged_days"], 2000.0)
        self.assertEqual(row["activity_days"], 3)
        self.assertEqual(row["activity_consistency"], 0.214)
        self.assertEqual(row["activity_calories_total"], 600.0)
        self.assertEqual(row["activity_calories_avg_all_days"], 42.857)
        self.assertEqual(row["workouts_count"], 3)
        self.assertEqual(row["weight_days"], 3)
        self.assertEqual(row["weight_trend_kg"], -0.8)

    def test_dataset_calculates_14_day_target_weight_change(self):
        config = WeightPredictionFeatureConfig(
            horizon_days=14,
            feature_window_days=14,
            min_food_days=7,
            min_weight_days=2,
            target_tolerance_days=0,
        )

        dataset = build_weight_prediction_dataset(
            self.profiles,
            self.food_rows,
            self.activity_rows,
            self.weight_rows,
            config,
        )
        row = dataset[dataset["analysis_date"] == date(2026, 5, 14)].iloc[0]

        self.assertEqual(row["target_date"], date(2026, 5, 28))
        self.assertEqual(row["target_weight_kg"], 78.5)
        self.assertEqual(row["target_weight_source_date"], date(2026, 5, 28))
        self.assertEqual(row["target_weight_change_kg"], -0.7)

    def test_dataset_supports_30_day_target_with_same_feature_pipeline(self):
        config = WeightPredictionFeatureConfig(
            horizon_days=30,
            feature_window_days=14,
            min_food_days=7,
            min_weight_days=2,
            target_tolerance_days=0,
        )

        dataset = build_weight_prediction_dataset(
            self.profiles,
            self.food_rows,
            self.activity_rows,
            self.weight_rows,
            config,
        )
        row = dataset[dataset["analysis_date"] == date(2026, 5, 14)].iloc[0]

        self.assertEqual(row["horizon_days"], 30)
        self.assertEqual(row["target_date"], date(2026, 6, 13))
        self.assertEqual(row["target_weight_kg"], 78.0)
        self.assertEqual(row["target_weight_change_kg"], -1.2)

    def test_feature_row_never_uses_future_weight_as_input(self):
        weight_rows = pd.DataFrame(
            [
                {"user_id": 1, "log_date": date(2026, 5, 10), "weight_kg": 80.0},
                {"user_id": 1, "log_date": date(2026, 5, 20), "weight_kg": 75.0},
            ]
        )
        config = WeightPredictionFeatureConfig(
            horizon_days=14,
            feature_window_days=7,
            min_food_days=0,
            min_weight_days=1,
        )

        missing_past_row = build_weight_prediction_feature_row(
            self.profile,
            pd.DataFrame(),
            pd.DataFrame(),
            weight_rows,
            date(2026, 5, 5),
            config,
        )
        available_past_row = build_weight_prediction_feature_row(
            self.profile,
            pd.DataFrame(),
            pd.DataFrame(),
            weight_rows,
            date(2026, 5, 15),
            config,
        )

        self.assertIsNone(missing_past_row)
        self.assertIsNotNone(available_past_row)
        self.assertEqual(available_past_row["current_weight_kg"], 80.0)
        self.assertEqual(
            available_past_row["current_weight_source_date"], date(2026, 5, 10)
        )

    def test_row_is_skipped_when_food_history_is_too_sparse(self):
        config = WeightPredictionFeatureConfig(
            horizon_days=14,
            feature_window_days=14,
            min_food_days=11,
            min_weight_days=2,
        )

        row = build_weight_prediction_feature_row(
            self.profile,
            self.food_rows,
            self.activity_rows,
            self.weight_rows,
            date(2026, 5, 14),
            config,
        )

        self.assertIsNone(row)


if __name__ == "__main__":
    unittest.main()
