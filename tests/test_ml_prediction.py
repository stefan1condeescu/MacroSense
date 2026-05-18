from datetime import date
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from services.ml.artifacts import save_weight_model_artifact
from services.ml.prediction import (
    UserWeightPredictions,
    WeightPrediction,
    _resolve_analysis_date,
    get_latest_available_user_weight_predictions,
    predict_weight_changes_from_frames,
    prepare_activity_rows_for_ml,
)
from services.ml.training import ModelTrainingConfig, train_weight_prediction_models
from tests.test_ml_training import _make_training_dataset


class MLPredictionTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "user_id": 1,
            "full_name": "Prediction User",
            "height_cm": 180,
            "age": 30,
            "gender": "M",
            "goal": "Slabire",
        }
        self.food_rows = pd.DataFrame(
            [
                {
                    "user_id": 1,
                    "log_date": pd.Timestamp(date(2026, 4, 15))
                    + pd.Timedelta(days=day_index),
                    "meal_type": "Pranz",
                    "food_name": "Meal",
                    "source_type": "catalog_food",
                    "calories": 1900,
                    "protein_g": 105,
                    "carbs_g": 210,
                    "fats_g": 55,
                }
                for day_index in range(30)
            ]
        )
        self.weight_rows = pd.DataFrame(
            [
                {"user_id": 1, "log_date": date(2026, 4, 15), "weight_kg": 80.8},
                {"user_id": 1, "log_date": date(2026, 5, 1), "weight_kg": 80.0},
                {"user_id": 1, "log_date": date(2026, 5, 8), "weight_kg": 79.4},
            ]
        )
        self.activity_rows = pd.DataFrame(
            [
                {
                    "user_id": 1,
                    "log_date": date(2026, 5, 3),
                    "activity_name": "Alergare",
                    "category": "Cardio",
                    "duration_min": 30,
                    "calories_burned": 320,
                }
            ]
        )

    def test_prepare_activity_rows_uses_only_past_weight_for_estimates(self):
        raw_activity_rows = pd.DataFrame(
            [
                {
                    "user_id": 1,
                    "log_date": date(2026, 5, 1),
                    "activity_name": "Before weight",
                    "category": "Cardio",
                    "duration_min": 30,
                    "sets": None,
                    "reps": None,
                    "manual_calories_burned": None,
                    "met_multiplier": 8.0,
                },
                {
                    "user_id": 1,
                    "log_date": date(2026, 5, 1),
                    "activity_name": "Manual before weight",
                    "category": "Cardio",
                    "duration_min": 30,
                    "sets": None,
                    "reps": None,
                    "manual_calories_burned": 250,
                    "met_multiplier": 8.0,
                },
                {
                    "user_id": 1,
                    "log_date": date(2026, 5, 5),
                    "activity_name": "Alergare",
                    "category": "Cardio",
                    "duration_min": 30,
                    "sets": None,
                    "reps": None,
                    "manual_calories_burned": None,
                    "met_multiplier": 8.0,
                },
                {
                    "user_id": 1,
                    "log_date": date(2026, 5, 5),
                    "activity_name": "Forta",
                    "category": "Forta",
                    "duration_min": 30,
                    "sets": 3,
                    "reps": 10,
                    "manual_calories_burned": None,
                    "met_multiplier": 5.0,
                },
            ]
        )
        weight_rows = pd.DataFrame(
            [{"user_id": 1, "log_date": date(2026, 5, 3), "weight_kg": 80.0}]
        )

        prepared_rows = prepare_activity_rows_for_ml(raw_activity_rows, weight_rows)

        self.assertEqual(prepared_rows.shape[0], 3)
        self.assertNotIn("Before weight", set(prepared_rows["activity_name"]))
        self.assertIn("Manual before weight", set(prepared_rows["activity_name"]))
        cardio_row = prepared_rows[prepared_rows["activity_name"] == "Alergare"].iloc[0]
        strength_row = prepared_rows[prepared_rows["activity_name"] == "Forta"].iloc[0]
        self.assertEqual(cardio_row["calories_burned"], 320.0)
        self.assertEqual(strength_row["calories_burned"], 67.0)

    def test_prediction_returns_14_and_30_day_outputs_from_saved_artifacts(self):
        with TemporaryDirectory() as temp_dir:
            for horizon_days in (14, 30):
                training_result = train_weight_prediction_models(
                    _make_training_dataset(horizon_days),
                    ModelTrainingConfig(
                        min_rows=10,
                        random_forest_estimators=8,
                        random_state=11,
                        split_strategy="row",
                    ),
                )
                save_weight_model_artifact(training_result, temp_dir)

            result = predict_weight_changes_from_frames(
                self.profile,
                self.food_rows,
                self.activity_rows,
                self.weight_rows,
                date(2026, 5, 14),
                temp_dir,
                horizons=(14, 30),
            )

        self.assertEqual(result.user_id, 1)
        self.assertEqual(result.analysis_date, date(2026, 5, 14))
        self.assertEqual(result.unavailable_horizons, {})
        self.assertEqual([item.horizon_days for item in result.predictions], [14, 30])
        for prediction in result.predictions:
            self.assertGreater(prediction.predicted_weight_kg, 30)
            self.assertLess(prediction.predicted_weight_kg, 300)
            self.assertIn("mae", prediction.metrics)
            self.assertIn("rmse", prediction.metrics)

    def test_prediction_reports_unavailable_horizon_when_recent_data_is_sparse(self):
        with TemporaryDirectory() as temp_dir:
            training_result = train_weight_prediction_models(
                _make_training_dataset(14),
                ModelTrainingConfig(
                    min_rows=10,
                    random_forest_estimators=8,
                    random_state=11,
                    split_strategy="row",
                ),
            )
            save_weight_model_artifact(training_result, temp_dir)

            result = predict_weight_changes_from_frames(
                self.profile,
                self.food_rows.head(2),
                self.activity_rows,
                self.weight_rows,
                date(2026, 5, 14),
                temp_dir,
                horizons=(14,),
            )

        self.assertEqual(result.predictions, [])
        self.assertIn(14, result.unavailable_horizons)

    def test_latest_available_prediction_looks_back_from_sparse_current_day(self):
        with TemporaryDirectory() as temp_dir:
            training_result = train_weight_prediction_models(
                _make_training_dataset(14),
                ModelTrainingConfig(
                    min_rows=10,
                    random_forest_estimators=8,
                    random_state=11,
                    split_strategy="row",
                ),
            )
            save_weight_model_artifact(training_result, temp_dir)

            import services.ml.prediction as prediction_module

            original_fetch = prediction_module.fetch_user_prediction_frames
            sparse_food_rows = self.food_rows[
                (self.food_rows["log_date"].dt.date >= date(2026, 5, 1))
                & (self.food_rows["log_date"].dt.date <= date(2026, 5, 7))
            ].reset_index(drop=True)
            try:
                prediction_module.fetch_user_prediction_frames = (
                    lambda user_id, analysis_date: (
                        self.profile,
                        sparse_food_rows,
                        self.activity_rows,
                        self.weight_rows,
                    )
                )
                result = get_latest_available_user_weight_predictions(
                    user_id=1,
                    analysis_date=date(2026, 5, 18),
                    artifact_dir=temp_dir,
                    horizons=(14,),
                    max_lookback_days=8,
                )
            finally:
                prediction_module.fetch_user_prediction_frames = original_fetch

        self.assertEqual(result.analysis_date, date(2026, 5, 14))
        self.assertEqual(len(result.predictions), 1)

    def test_prefer_complete_days_uses_yesterday_for_current_day(self):
        self.assertEqual(
            _resolve_analysis_date(
                date(2026, 5, 18),
                prefer_complete_days=True,
                today=date(2026, 5, 18),
            ),
            date(2026, 5, 17),
        )
        self.assertEqual(
            _resolve_analysis_date(
                date(2026, 5, 17),
                prefer_complete_days=True,
                today=date(2026, 5, 18),
            ),
            date(2026, 5, 17),
        )

    def test_latest_available_prediction_falls_back_to_current_day(self):
        import services.ml.prediction as prediction_module

        original_fetch = prediction_module.fetch_user_prediction_frames
        original_predict = prediction_module.predict_weight_changes_from_frames

        def fake_fetch(user_id, analysis_date):
            return self.profile, self.food_rows, self.activity_rows, self.weight_rows

        def fake_predict(
            profile,
            food_rows,
            activity_rows,
            weight_rows,
            analysis_date,
            artifact_dir,
            horizons,
        ):
            if analysis_date != date(2026, 5, 18):
                return UserWeightPredictions(
                    user_id=profile["user_id"],
                    analysis_date=analysis_date,
                    predictions=[],
                    unavailable_horizons={
                        horizon: "Nu există suficiente date recente pentru predicție."
                        for horizon in horizons
                    },
                )
            return UserWeightPredictions(
                user_id=profile["user_id"],
                analysis_date=analysis_date,
                predictions=[
                    WeightPrediction(
                        horizon_days=14,
                        analysis_date=analysis_date,
                        target_date=date(2026, 6, 1),
                        current_weight_kg=79.0,
                        predicted_change_kg=-0.2,
                        predicted_weight_kg=78.8,
                        model_name="energy_trend_reference",
                        metrics={"mae": 0.4},
                    )
                ],
                unavailable_horizons={},
            )

        try:
            prediction_module.fetch_user_prediction_frames = fake_fetch
            prediction_module.predict_weight_changes_from_frames = fake_predict

            result = get_latest_available_user_weight_predictions(
                user_id=1,
                analysis_date=date(2026, 5, 18),
                horizons=(14,),
                max_lookback_days=2,
                prefer_complete_days=True,
                today=date(2026, 5, 18),
            )
        finally:
            prediction_module.fetch_user_prediction_frames = original_fetch
            prediction_module.predict_weight_changes_from_frames = original_predict

        self.assertEqual(result.analysis_date, date(2026, 5, 18))
        self.assertEqual(len(result.predictions), 1)


if __name__ == "__main__":
    unittest.main()
