from tempfile import TemporaryDirectory
import unittest

from services.ml.artifacts import (
    load_weight_model_artifact,
    predict_weight_change,
    save_weight_model_artifact,
)
from services.ml.training import ModelTrainingConfig, train_weight_prediction_models
from tests.test_ml_training import _make_training_dataset


class MLArtifactTests(unittest.TestCase):
    def setUp(self):
        self.dataset = _make_training_dataset(14)
        self.result = train_weight_prediction_models(
            self.dataset,
            ModelTrainingConfig(
                min_rows=10,
                random_forest_estimators=8,
                random_state=11,
                split_strategy="row",
            ),
        )

    def test_weight_model_artifact_round_trip(self):
        with TemporaryDirectory() as temp_dir:
            saved_artifact = save_weight_model_artifact(
                self.result,
                temp_dir,
                training_context={"synthetic_user_count": 120},
            )
            loaded_artifact = load_weight_model_artifact(14, temp_dir)

            self.assertTrue(saved_artifact.model_path.exists())
            self.assertTrue(saved_artifact.metadata_path.exists())
            self.assertEqual(loaded_artifact.horizon_days, 14)
            self.assertEqual(
                loaded_artifact.metadata["best_model_name"], self.result.best_model_name
            )
            self.assertEqual(
                loaded_artifact.metadata["feature_columns"], self.result.feature_columns
            )
            self.assertEqual(
                loaded_artifact.metadata["target_column"],
                "target_weight_change_kg",
            )
            self.assertEqual(
                loaded_artifact.metadata["training_context"]["synthetic_user_count"],
                120,
            )

    def test_loaded_artifact_predicts_one_feature_row(self):
        with TemporaryDirectory() as temp_dir:
            save_weight_model_artifact(self.result, temp_dir)
            loaded_artifact = load_weight_model_artifact(14, temp_dir)
            feature_row = self.dataset.iloc[0]

            prediction = predict_weight_change(loaded_artifact, feature_row)

            self.assertIsInstance(prediction, float)
            self.assertGreater(prediction, -10)
            self.assertLess(prediction, 10)

    def test_loading_missing_artifact_fails_clearly(self):
        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(FileNotFoundError):
                load_weight_model_artifact(14, temp_dir)

    def test_loading_wrong_horizon_metadata_fails_clearly(self):
        with TemporaryDirectory() as temp_dir:
            save_weight_model_artifact(self.result, temp_dir)

            with self.assertRaises(FileNotFoundError):
                load_weight_model_artifact(30, temp_dir)


if __name__ == "__main__":
    unittest.main()
