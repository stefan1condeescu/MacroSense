"""Machine learning support utilities for MacroSense."""

from services.ml.feature_engineering import (
    WeightPredictionFeatureConfig,
    build_default_weight_prediction_feature_config,
    build_weight_prediction_dataset,
    build_weight_prediction_feature_row,
)
from services.ml.artifacts import (
    DEFAULT_MODEL_ARTIFACT_DIR,
    WeightModelArtifact,
    load_weight_model_artifact,
    predict_weight_change,
    save_weight_model_artifact,
    save_weight_model_artifacts,
)
from services.ml.evaluation import (
    BaselineEvaluation,
    RegressionMetrics,
    SanityCheckResult,
    WeightModelEvaluation,
    calculate_regression_metrics,
    evaluate_weight_model_on_dataset,
    run_weight_prediction_sanity_checks,
)
from services.ml.prediction import (
    DEFAULT_PREDICTION_HORIZONS,
    UserWeightPredictions,
    WeightPrediction,
    get_latest_available_user_weight_predictions,
    get_user_weight_predictions,
    predict_weight_changes_from_frames,
    prepare_activity_rows_for_ml,
)
from services.ml.synthetic_data import (
    SyntheticDatasetConfig,
    SyntheticHistories,
    generate_synthetic_histories,
)
from services.ml.training import (
    ModelTrainingConfig,
    WeightModelTrainingResult,
    train_weight_prediction_models,
    train_weight_prediction_models_for_horizons,
)

__all__ = [
    "DEFAULT_MODEL_ARTIFACT_DIR",
    "DEFAULT_PREDICTION_HORIZONS",
    "BaselineEvaluation",
    "ModelTrainingConfig",
    "RegressionMetrics",
    "SanityCheckResult",
    "SyntheticDatasetConfig",
    "SyntheticHistories",
    "UserWeightPredictions",
    "WeightModelArtifact",
    "WeightModelEvaluation",
    "WeightPrediction",
    "WeightPredictionFeatureConfig",
    "WeightModelTrainingResult",
    "build_default_weight_prediction_feature_config",
    "build_weight_prediction_dataset",
    "build_weight_prediction_feature_row",
    "calculate_regression_metrics",
    "evaluate_weight_model_on_dataset",
    "generate_synthetic_histories",
    "get_latest_available_user_weight_predictions",
    "get_user_weight_predictions",
    "load_weight_model_artifact",
    "predict_weight_change",
    "predict_weight_changes_from_frames",
    "prepare_activity_rows_for_ml",
    "run_weight_prediction_sanity_checks",
    "save_weight_model_artifact",
    "save_weight_model_artifacts",
    "train_weight_prediction_models",
    "train_weight_prediction_models_for_horizons",
]
