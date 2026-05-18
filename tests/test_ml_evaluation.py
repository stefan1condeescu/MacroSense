from pathlib import Path
import unittest

import pandas as pd

from services.ml.artifacts import WeightModelArtifact
from services.ml.evaluation import (
    calculate_regression_metrics,
    evaluate_weight_model_on_dataset,
    run_weight_prediction_sanity_checks,
)
from services.ml.training import WEIGHT_MODEL_FEATURE_COLUMNS
from tests.test_ml_training import _make_training_dataset


class MLEvaluationTests(unittest.TestCase):
    def test_regression_metrics_report_expected_values(self):
        metrics = calculate_regression_metrics([1.0, 2.0, 3.0], [1.0, 2.5, 2.5])

        self.assertEqual(metrics.mae, 0.3333)
        self.assertEqual(metrics.rmse, 0.4082)
        self.assertLess(metrics.r2, 1.0)

    def test_model_evaluation_compares_model_with_baselines(self):
        dataset = _make_training_dataset(14)
        artifact = _make_fake_artifact(14)

        report = evaluate_weight_model_on_dataset(artifact, dataset)

        self.assertEqual(report.horizon_days, 14)
        self.assertEqual(report.model_name, "fake_linear")
        self.assertEqual(report.row_count, dataset.shape[0])
        self.assertGreaterEqual(report.model_metrics.mae, 0)
        self.assertEqual(
            [baseline.name for baseline in report.baseline_evaluations],
            ["no_change", "trend_projection", "energy_balance_projection"],
        )
        self.assertEqual(
            [check.name for check in report.sanity_checks],
            ["larger_deficit", "larger_surplus", "more_activity"],
        )

    def test_sanity_checks_pass_for_directional_fake_model(self):
        dataset = _make_training_dataset(14)
        artifact = _make_fake_artifact(14)

        checks = run_weight_prediction_sanity_checks(artifact, dataset.iloc[0])

        self.assertTrue(all(check.passed for check in checks))
        self.assertLess(
            checks[0].changed_prediction_kg,
            checks[0].base_prediction_kg,
        )
        self.assertGreater(
            checks[1].changed_prediction_kg,
            checks[1].base_prediction_kg,
        )


class _DirectionalFakeModel:
    def __init__(self, horizon_days: int):
        self.horizon_days = horizon_days

    def predict(self, feature_frame: pd.DataFrame) -> list[float]:
        predictions = []
        for row in feature_frame.to_dict("records"):
            energy_effect = (
                float(row["estimated_balance_avg_logged_days"])
                * self.horizon_days
                / 7700.0
            )
            trend_effect = float(row["weight_trend_kg"]) * 0.25
            activity_effect = -float(row["activity_calories_avg_all_days"]) / 20000.0
            predictions.append(energy_effect + trend_effect + activity_effect)
        return predictions


def _make_fake_artifact(horizon_days: int) -> WeightModelArtifact:
    return WeightModelArtifact(
        horizon_days=horizon_days,
        model=_DirectionalFakeModel(horizon_days),
        metadata={
            "best_model_name": "fake_linear",
            "feature_columns": list(WEIGHT_MODEL_FEATURE_COLUMNS),
        },
        model_path=Path("fake.joblib"),
        metadata_path=Path("fake_metadata.json"),
    )


if __name__ == "__main__":
    unittest.main()
