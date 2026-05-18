from datetime import date
import unittest

import pandas as pd

from services.ml.feature_engineering import (
    WeightPredictionFeatureConfig,
    build_weight_prediction_dataset,
)
from services.ml.synthetic_data import (
    SyntheticDatasetConfig,
    generate_synthetic_histories,
)


class MLSyntheticDataTests(unittest.TestCase):
    def test_generator_is_reproducible_for_same_seed(self):
        config = SyntheticDatasetConfig(
            user_count=3,
            history_days=60,
            start_date=date(2026, 1, 1),
            random_seed=123,
        )

        first = generate_synthetic_histories(config)
        second = generate_synthetic_histories(config)

        pd.testing.assert_frame_equal(first.profile_rows, second.profile_rows)
        pd.testing.assert_frame_equal(first.food_rows, second.food_rows)
        pd.testing.assert_frame_equal(first.activity_rows, second.activity_rows)
        pd.testing.assert_frame_equal(first.weight_rows, second.weight_rows)

    def test_generator_returns_expected_raw_tables(self):
        histories = generate_synthetic_histories(
            SyntheticDatasetConfig(
                user_count=4,
                history_days=70,
                start_date=date(2026, 1, 1),
                random_seed=7,
            )
        )

        self.assertEqual(histories.profile_rows.shape[0], 4)
        self.assertFalse(histories.food_rows.empty)
        self.assertFalse(histories.activity_rows.empty)
        self.assertFalse(histories.weight_rows.empty)
        self.assertTrue(
            {
                "user_id",
                "height_cm",
                "age",
                "gender",
                "goal",
                "start_weight_kg",
            }.issubset(histories.profile_rows.columns)
        )
        self.assertTrue(
            {
                "user_id",
                "log_date",
                "meal_type",
                "food_name",
                "source_type",
                "calories",
                "protein_g",
                "carbs_g",
                "fats_g",
            }.issubset(histories.food_rows.columns)
        )
        self.assertTrue(
            {
                "user_id",
                "log_date",
                "activity_name",
                "category",
                "duration_min",
                "calories_burned",
            }.issubset(histories.activity_rows.columns)
        )
        self.assertTrue(
            {"user_id", "log_date", "weight_kg"}.issubset(
                histories.weight_rows.columns
            )
        )

    def test_generator_includes_simplified_custom_meal_snapshots(self):
        histories = generate_synthetic_histories(
            SyntheticDatasetConfig(
                user_count=5,
                history_days=75,
                start_date=date(2026, 1, 1),
                random_seed=99,
                custom_meal_probability=0.35,
            )
        )

        source_types = set(histories.food_rows["source_type"])

        self.assertIn("custom_meal", source_types)
        self.assertIn("catalog_food", source_types)
        custom_meal_rows = histories.food_rows[
            histories.food_rows["source_type"] == "custom_meal"
        ]
        self.assertGreater(custom_meal_rows.shape[0], 0)
        self.assertTrue((custom_meal_rows["calories"] > 0).all())
        self.assertTrue((custom_meal_rows["protein_g"] > 0).all())

    def test_generator_varies_history_shape_between_users(self):
        histories = generate_synthetic_histories(
            SyntheticDatasetConfig(
                user_count=6,
                history_days=100,
                start_date=date(2026, 1, 1),
                random_seed=555,
                history_days_jitter=20,
                start_date_jitter_days=20,
            )
        )

        self.assertIn("history_start_date", histories.profile_rows.columns)
        self.assertIn("history_days", histories.profile_rows.columns)
        self.assertGreater(histories.profile_rows["history_start_date"].nunique(), 1)
        self.assertGreater(histories.profile_rows["history_days"].nunique(), 1)

    def test_generated_histories_feed_14_and_30_day_feature_engineering(self):
        histories = generate_synthetic_histories(
            SyntheticDatasetConfig(
                user_count=4,
                history_days=60,
                start_date=date(2026, 1, 1),
                random_seed=202,
            )
        )

        dataset_14d = build_weight_prediction_dataset(
            histories.profile_rows,
            histories.food_rows,
            histories.activity_rows,
            histories.weight_rows,
            WeightPredictionFeatureConfig(
                horizon_days=14,
                feature_window_days=14,
                min_food_days=7,
                min_weight_days=2,
            ),
        )
        dataset_30d = build_weight_prediction_dataset(
            histories.profile_rows,
            histories.food_rows,
            histories.activity_rows,
            histories.weight_rows,
            WeightPredictionFeatureConfig(
                horizon_days=30,
                feature_window_days=14,
                min_food_days=7,
                min_weight_days=2,
            ),
        )

        self.assertFalse(dataset_14d.empty)
        self.assertFalse(dataset_30d.empty)
        self.assertEqual(set(dataset_14d["horizon_days"]), {14})
        self.assertEqual(set(dataset_30d["horizon_days"]), {30})
        self.assertTrue(dataset_14d["target_weight_change_kg"].notna().all())
        self.assertTrue(dataset_30d["target_weight_change_kg"].notna().all())
        self.assertTrue(
            (
                dataset_14d["current_weight_source_date"]
                <= dataset_14d["analysis_date"]
            ).all()
        )
        self.assertTrue(
            (
                dataset_30d["current_weight_source_date"]
                <= dataset_30d["analysis_date"]
            ).all()
        )


if __name__ == "__main__":
    unittest.main()
