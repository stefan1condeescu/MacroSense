from datetime import date
import unittest

import pandas as pd

from services.ml.synthetic_data import SyntheticDatasetConfig, generate_synthetic_histories
from services.ml.training import (
    ModelTrainingConfig,
    train_weight_prediction_models,
    train_weight_prediction_models_for_horizons,
)


class MLTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.training_config = ModelTrainingConfig(
            min_rows=10,
            random_forest_estimators=8,
            random_state=11,
            split_strategy="row",
        )
        cls.dataset_14d = _make_training_dataset(14)
        cls.dataset_30d = _make_training_dataset(30)

    def test_training_compares_regression_models_and_selects_best(self):
        result = train_weight_prediction_models(self.dataset_14d, self.training_config)

        self.assertEqual(result.horizon_days, 14)
        self.assertIn(
            result.best_model_name,
            {
                "ridge_regression",
                "random_forest",
                "gradient_boosting",
                "energy_balance_reference",
                "energy_trend_reference",
                "energy_trend_residual_ridge",
                "energy_trend_residual_gradient_boosting",
            },
        )
        self.assertTrue(
            {
                "ridge_regression",
                "random_forest",
                "gradient_boosting",
            }.issubset(set(result.metrics_by_model))
        )
        self.assertIn("energy_balance_reference", result.metrics_by_model)
        self.assertIn("energy_trend_reference", result.metrics_by_model)
        self.assertIn("energy_trend_residual_ridge", result.metrics_by_model)
        self.assertIn("energy_trend_residual_gradient_boosting", result.metrics_by_model)
        self.assertGreater(result.row_count, 0)
        self.assertGreater(result.train_row_count, 0)
        self.assertGreater(result.test_row_count, 0)
        for metrics in result.metrics_by_model.values():
            self.assertIn("mae", metrics)
            self.assertIn("rmse", metrics)
            self.assertIn("r2", metrics)
            self.assertGreaterEqual(metrics["mae"], 0)
            self.assertGreaterEqual(metrics["rmse"], 0)

    def test_training_supports_14_and_30_day_horizons(self):
        histories = generate_synthetic_histories(
            SyntheticDatasetConfig(
                user_count=8,
                history_days=80,
                start_date=date(2026, 1, 1),
                random_seed=404,
            )
        )

        results = train_weight_prediction_models_for_horizons(
            histories,
            horizon_days_values=(14, 30),
            feature_min_food_days=0,
            feature_min_weight_days=1,
            training_config=self.training_config,
        )

        self.assertEqual(set(results), {14, 30})
        self.assertEqual(results[14].horizon_days, 14)
        self.assertEqual(results[30].horizon_days, 30)
        self.assertTrue(results[14].feature_columns)
        self.assertEqual(results[14].feature_columns, results[30].feature_columns)

    def test_training_rejects_too_small_dataset(self):
        dataset = pd.DataFrame(
            [
                {
                    "user_id": 1,
                    "horizon_days": 14,
                    "current_weight_kg": 80.0,
                    "target_weight_change_kg": -0.2,
                }
            ]
        )

        with self.assertRaises(ValueError):
            train_weight_prediction_models(dataset, self.training_config)

    def test_training_rejects_mixed_horizons(self):
        mixed_dataset = pd.concat(
            [self.dataset_14d.head(15), self.dataset_30d.head(15)], ignore_index=True
        )

        with self.assertRaises(ValueError):
            train_weight_prediction_models(mixed_dataset, self.training_config)

    def test_training_config_rejects_unknown_split_strategy(self):
        with self.assertRaises(ValueError):
            ModelTrainingConfig(split_strategy="future")


def _make_training_dataset(horizon_days: int) -> pd.DataFrame:
    rows = []
    feature_window_days = horizon_days
    for index in range(60):
        user_id = (index % 6) + 1
        current_weight = 68.0 + (user_id * 2.1) + (index % 5) * 0.2
        calories_avg = 1650.0 + (index % 12) * 35.0
        activity_avg = 60.0 + (index % 8) * 18.0
        weight_trend = -0.8 + (index % 9) * 0.18
        estimated_balance = calories_avg - 2100.0 - activity_avg
        target_change = (
            estimated_balance / 7700.0 * horizon_days
            + weight_trend * 0.28
            + ((index % 3) - 1) * 0.04
        )
        rows.append(
            {
                "user_id": user_id,
                "analysis_date": date(2026, 2, 1),
                "horizon_days": horizon_days,
                "feature_window_days": feature_window_days,
                "current_weight_kg": round(current_weight, 3),
                "current_weight_source_date": date(2026, 2, 1),
                "target_date": date(2026, 2, 1),
                "target_weight_kg": round(current_weight + target_change, 3),
                "target_weight_source_date": date(2026, 2, 1),
                "target_weight_change_kg": round(target_change, 3),
                "calories_avg_logged_days": round(calories_avg, 3),
                "calories_total": round(calories_avg * 10, 3),
                "food_days": min(feature_window_days, 10 + (index % 5)),
                "food_consistency": round(
                    min(feature_window_days, 10 + (index % 5)) / feature_window_days,
                    3,
                ),
                "protein_avg_logged_days": 80.0 + (index % 7) * 5.0,
                "protein_per_kg_avg_logged_days": 1.1 + (index % 6) * 0.08,
                "carbs_avg_logged_days": 180.0 + (index % 9) * 8.0,
                "fats_avg_logged_days": 45.0 + (index % 5) * 4.0,
                "activity_calories_avg_all_days": round(activity_avg, 3),
                "activity_calories_total": round(activity_avg * feature_window_days, 3),
                "activity_days": 2 + (index % 5),
                "activity_consistency": round(
                    (2 + (index % 5)) / feature_window_days,
                    3,
                ),
                "workouts_count": 2 + (index % 6),
                "weight_days": 2 + (index % 4),
                "weight_consistency": round(
                    (2 + (index % 4)) / feature_window_days,
                    3,
                ),
                "weight_trend_kg": round(weight_trend, 3),
                "estimated_balance_avg_logged_days": round(estimated_balance, 3),
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
