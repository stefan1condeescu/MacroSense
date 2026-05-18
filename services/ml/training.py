"""Training utilities for MacroSense weight prediction models."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import pandas as pd

from services.ml.feature_engineering import (
    build_default_weight_prediction_feature_config,
    build_weight_prediction_dataset,
)
from services.ml.synthetic_data import SyntheticHistories


WEIGHT_MODEL_FEATURE_COLUMNS = [
    "feature_window_days",
    "current_weight_kg",
    "calories_avg_logged_days",
    "calories_total",
    "food_days",
    "food_consistency",
    "protein_avg_logged_days",
    "protein_per_kg_avg_logged_days",
    "carbs_avg_logged_days",
    "fats_avg_logged_days",
    "activity_calories_avg_all_days",
    "activity_calories_total",
    "activity_days",
    "activity_consistency",
    "workouts_count",
    "weight_days",
    "weight_consistency",
    "weight_trend_kg",
    "estimated_balance_avg_logged_days",
]

TARGET_COLUMN = "target_weight_change_kg"
ENERGY_KCAL_PER_KG = 7700.0


class EnergyBalanceRegressor:
    """Deterministic reference regressor based on estimated caloric balance."""

    def __init__(self, horizon_days: int):
        self.horizon_days = int(horizon_days)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "EnergyBalanceRegressor":
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        return _energy_balance_projection(X, self.horizon_days)


class EnergyTrendBlendRegressor:
    """Conservative reference regressor based on energy balance and real trend."""

    def __init__(self, horizon_days: int):
        self.horizon_days = int(horizon_days)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "EnergyTrendBlendRegressor":
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        return _energy_trend_blend_projection(X, self.horizon_days)


class EnergyTrendResidualRegressor:
    """Conservative hybrid: trend/energy baseline plus bounded ML correction."""

    def __init__(
        self,
        horizon_days: int,
        residual_model: Any,
        residual_shrinkage: float = 0.25,
    ):
        self.horizon_days = int(horizon_days)
        self.residual_model = residual_model
        self.residual_shrinkage = float(residual_shrinkage)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "EnergyTrendResidualRegressor":
        baseline_predictions = _energy_trend_blend_projection(X, self.horizon_days)
        residual_target = pd.Series(y).reset_index(drop=True) - pd.Series(
            baseline_predictions
        ).reset_index(drop=True)
        self.residual_model.fit(X, residual_target)
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        baseline_predictions = pd.Series(
            _energy_trend_blend_projection(X, self.horizon_days)
        ).reset_index(drop=True)
        raw_residuals = pd.Series(self.residual_model.predict(X)).reset_index(drop=True)
        correction_limits = baseline_predictions.abs().mul(0.35).clip(lower=0.2)
        bounded_residuals = raw_residuals.clip(
            lower=-correction_limits,
            upper=correction_limits,
        )
        return baseline_predictions + (bounded_residuals * self.residual_shrinkage)


@dataclass(frozen=True)
class ModelTrainingConfig:
    """Configuration for comparing weight prediction regressors."""

    test_size: float = 0.25
    random_state: int = 42
    min_rows: int = 30
    random_forest_estimators: int = 80
    split_strategy: str = "user"

    def __post_init__(self) -> None:
        if not 0 < self.test_size < 1:
            raise ValueError("test_size must be between 0 and 1.")
        if self.min_rows < 10:
            raise ValueError("min_rows must be at least 10.")
        if self.random_forest_estimators <= 0:
            raise ValueError("random_forest_estimators must be positive.")
        if self.split_strategy not in {"user", "row"}:
            raise ValueError("split_strategy must be 'user' or 'row'.")


@dataclass
class WeightModelTrainingResult:
    """Result of training and evaluating candidate weight prediction models."""

    horizon_days: int
    best_model_name: str
    best_model: Any
    metrics_by_model: dict[str, dict[str, float]]
    feature_columns: list[str]
    row_count: int
    train_row_count: int
    test_row_count: int


def train_weight_prediction_models(
    dataset: pd.DataFrame,
    config: ModelTrainingConfig | None = None,
) -> WeightModelTrainingResult:
    """Train candidate regressors and return the selected deployable model."""

    cfg = config or ModelTrainingConfig()
    prepared_dataset = _prepare_training_dataset(dataset)
    if prepared_dataset.shape[0] < cfg.min_rows:
        raise ValueError(
            f"Not enough rows for training: {prepared_dataset.shape[0]} rows available, "
            f"{cfg.min_rows} required."
        )

    train_rows, test_rows = _split_dataset_by_user(prepared_dataset, cfg)
    X_train = train_rows[WEIGHT_MODEL_FEATURE_COLUMNS]
    y_train = train_rows[TARGET_COLUMN]
    X_test = test_rows[WEIGHT_MODEL_FEATURE_COLUMNS]
    y_test = test_rows[TARGET_COLUMN]

    horizon_days = int(prepared_dataset["horizon_days"].iloc[0])
    candidate_models = _build_candidate_models(cfg, horizon_days)
    trained_models: dict[str, Any] = {}
    metrics_by_model: dict[str, dict[str, float]] = {}

    for model_name, model in candidate_models.items():
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        metrics_by_model[model_name] = _calculate_metrics(y_test, predictions)
        trained_models[model_name] = model

    deployable_model_names = [
        name for name in metrics_by_model if name.startswith("energy_trend")
    ]
    selection_pool = deployable_model_names or list(metrics_by_model)
    best_model_name = min(
        selection_pool,
        key=lambda name: (
            metrics_by_model[name]["mae"],
            metrics_by_model[name]["rmse"],
        ),
    )
    return WeightModelTrainingResult(
        horizon_days=horizon_days,
        best_model_name=best_model_name,
        best_model=trained_models[best_model_name],
        metrics_by_model=metrics_by_model,
        feature_columns=list(WEIGHT_MODEL_FEATURE_COLUMNS),
        row_count=int(prepared_dataset.shape[0]),
        train_row_count=int(train_rows.shape[0]),
        test_row_count=int(test_rows.shape[0]),
    )


def train_weight_prediction_models_for_horizons(
    histories: SyntheticHistories,
    horizon_days_values: tuple[int, ...] = (14, 30),
    feature_window_days: int | None = None,
    feature_min_food_days: int | None = None,
    feature_min_weight_days: int | None = None,
    training_config: ModelTrainingConfig | None = None,
) -> dict[int, WeightModelTrainingResult]:
    """Build datasets from raw histories and train one model set per horizon."""

    results: dict[int, WeightModelTrainingResult] = {}
    for horizon_days in horizon_days_values:
        dataset = build_weight_prediction_dataset(
            histories.profile_rows,
            histories.food_rows,
            histories.activity_rows,
            histories.weight_rows,
            build_default_weight_prediction_feature_config(
                horizon_days=horizon_days,
                feature_window_days=feature_window_days,
                min_food_days=feature_min_food_days,
                min_weight_days=feature_min_weight_days,
            ),
        )
        results[horizon_days] = train_weight_prediction_models(
            dataset, training_config
        )
    return results


def _prepare_training_dataset(dataset: pd.DataFrame) -> pd.DataFrame:
    if dataset is None or dataset.empty:
        raise ValueError("dataset is empty.")

    required_columns = set(WEIGHT_MODEL_FEATURE_COLUMNS + [TARGET_COLUMN, "horizon_days"])
    missing_columns = required_columns.difference(dataset.columns)
    if missing_columns:
        raise ValueError(
            "dataset is missing columns: " + ", ".join(sorted(missing_columns)) + "."
        )

    prepared = dataset.copy()
    for column in WEIGHT_MODEL_FEATURE_COLUMNS + [TARGET_COLUMN]:
        prepared[column] = pd.to_numeric(prepared[column], errors="coerce")

    prepared = prepared.dropna(subset=WEIGHT_MODEL_FEATURE_COLUMNS + [TARGET_COLUMN])
    if prepared.empty:
        raise ValueError("dataset has no complete rows for training.")

    horizons = set(prepared["horizon_days"].dropna().astype(int))
    if len(horizons) != 1:
        raise ValueError("dataset must contain exactly one horizon_days value.")

    return prepared.reset_index(drop=True)


def _split_dataset_by_user(
    dataset: pd.DataFrame, config: ModelTrainingConfig
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if config.split_strategy == "row":
        return _split_dataset_by_row(dataset, config)

    if "user_id" not in dataset.columns or dataset["user_id"].nunique() < 2:
        return _split_dataset_by_row(dataset, config)

    try:
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for ML training.") from exc

    user_ids = pd.Series(dataset["user_id"].unique())
    train_users, test_users = train_test_split(
        user_ids,
        test_size=config.test_size,
        random_state=config.random_state,
        shuffle=True,
    )
    train_rows = dataset[dataset["user_id"].isin(set(train_users))]
    test_rows = dataset[dataset["user_id"].isin(set(test_users))]

    if train_rows.empty or test_rows.empty:
        return _split_dataset_by_row(dataset, config)
    return train_rows.reset_index(drop=True), test_rows.reset_index(drop=True)


def _split_dataset_by_row(
    dataset: pd.DataFrame, config: ModelTrainingConfig
) -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for ML training.") from exc

    train_rows, test_rows = train_test_split(
        dataset,
        test_size=config.test_size,
        random_state=config.random_state,
        shuffle=True,
    )
    return train_rows.reset_index(drop=True), test_rows.reset_index(drop=True)


def _build_candidate_models(
    config: ModelTrainingConfig,
    horizon_days: int,
) -> dict[str, Any]:
    try:
        from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for ML training.") from exc

    return {
        "ridge_regression": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "random_forest": RandomForestRegressor(
            n_estimators=config.random_forest_estimators,
            min_samples_leaf=3,
            random_state=config.random_state,
        ),
        "gradient_boosting": GradientBoostingRegressor(
            random_state=config.random_state,
        ),
        "energy_balance_reference": EnergyBalanceRegressor(horizon_days),
        "energy_trend_reference": EnergyTrendBlendRegressor(horizon_days),
        "energy_trend_residual_ridge": EnergyTrendResidualRegressor(
            horizon_days,
            make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        ),
        "energy_trend_residual_gradient_boosting": EnergyTrendResidualRegressor(
            horizon_days,
            GradientBoostingRegressor(random_state=config.random_state),
        ),
    }


def _calculate_metrics(y_true: pd.Series, predictions: Any) -> dict[str, float]:
    try:
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    except ImportError as exc:
        raise RuntimeError("scikit-learn is required for ML training.") from exc

    mae = mean_absolute_error(y_true, predictions)
    mse = mean_squared_error(y_true, predictions)
    rmse = math.sqrt(mse)
    r2 = r2_score(y_true, predictions)
    return {
        "mae": round(float(mae), 4),
        "rmse": round(float(rmse), 4),
        "r2": round(float(r2), 4),
    }


def _energy_balance_projection(X: pd.DataFrame, horizon_days: int) -> pd.Series:
    balance = pd.to_numeric(
        X["estimated_balance_avg_logged_days"], errors="coerce"
    ).fillna(0.0)
    return balance * int(horizon_days) / ENERGY_KCAL_PER_KG


def _trend_projection(X: pd.DataFrame, horizon_days: int) -> pd.Series:
    trend = pd.to_numeric(X["weight_trend_kg"], errors="coerce").fillna(0.0)
    if "feature_window_days" in X.columns:
        window_days = pd.to_numeric(
            X["feature_window_days"], errors="coerce"
        ).fillna(float(horizon_days))
    else:
        window_days = pd.Series(float(horizon_days), index=X.index)
    window_days = window_days.replace(0, float(horizon_days))
    return trend * int(horizon_days) / window_days


def _energy_trend_blend_projection(
    X: pd.DataFrame, horizon_days: int
) -> pd.Series:
    energy_projection = _energy_balance_projection(X, horizon_days)
    trend_projection = _trend_projection(X, horizon_days)
    weight_days = pd.to_numeric(X["weight_days"], errors="coerce").fillna(0.0)
    trend_confidence = (weight_days / 3.0).clip(lower=0.0, upper=1.0)
    trend_weight = 0.45 + (0.25 * trend_confidence)
    energy_weight = 1.0 - trend_weight
    return (trend_projection * trend_weight) + (energy_projection * energy_weight)
