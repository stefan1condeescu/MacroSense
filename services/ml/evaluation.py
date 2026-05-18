"""Evaluation utilities for MacroSense weight prediction models."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import pandas as pd

from services.ml.artifacts import WeightModelArtifact
from services.ml.training import TARGET_COLUMN


@dataclass(frozen=True)
class RegressionMetrics:
    """Regression metrics for model or baseline predictions."""

    mae: float
    rmse: float
    r2: float


@dataclass(frozen=True)
class BaselineEvaluation:
    """Evaluation result for a simple baseline predictor."""

    name: str
    metrics: RegressionMetrics


@dataclass(frozen=True)
class SanityCheckResult:
    """Directional sanity check for one controlled feature perturbation."""

    name: str
    passed: bool
    base_prediction_kg: float
    changed_prediction_kg: float
    expected_direction: str
    description: str


@dataclass(frozen=True)
class WeightModelEvaluation:
    """Complete evaluation report for one weight prediction horizon."""

    horizon_days: int
    model_name: str
    row_count: int
    model_metrics: RegressionMetrics
    baseline_evaluations: list[BaselineEvaluation]
    sanity_checks: list[SanityCheckResult]


def evaluate_weight_model_on_dataset(
    artifact: WeightModelArtifact,
    dataset: pd.DataFrame,
) -> WeightModelEvaluation:
    """Compare a saved model against simple baselines and sanity checks."""

    prepared_dataset = _prepare_evaluation_dataset(dataset, artifact)
    feature_columns = list(artifact.metadata["feature_columns"])
    target_values = prepared_dataset[TARGET_COLUMN]
    model_predictions = artifact.model.predict(prepared_dataset[feature_columns])

    baseline_evaluations = [
        BaselineEvaluation(
            name="no_change",
            metrics=calculate_regression_metrics(
                target_values,
                _no_change_baseline(prepared_dataset),
            ),
        ),
        BaselineEvaluation(
            name="trend_projection",
            metrics=calculate_regression_metrics(
                target_values,
                _trend_projection_baseline(prepared_dataset),
            ),
        ),
        BaselineEvaluation(
            name="energy_balance_projection",
            metrics=calculate_regression_metrics(
                target_values,
                _energy_balance_projection_baseline(prepared_dataset),
            ),
        ),
    ]

    return WeightModelEvaluation(
        horizon_days=int(artifact.horizon_days),
        model_name=str(artifact.metadata["best_model_name"]),
        row_count=int(prepared_dataset.shape[0]),
        model_metrics=calculate_regression_metrics(target_values, model_predictions),
        baseline_evaluations=baseline_evaluations,
        sanity_checks=run_weight_prediction_sanity_checks(
            artifact,
            _representative_feature_row(prepared_dataset),
        ),
    )


def calculate_regression_metrics(
    y_true: Any,
    predictions: Any,
) -> RegressionMetrics:
    """Calculate MAE, RMSE and R2 without depending on sklearn at runtime."""

    true_values = pd.to_numeric(pd.Series(y_true), errors="coerce")
    predicted_values = pd.to_numeric(pd.Series(predictions), errors="coerce")
    values = pd.DataFrame({"actual": true_values, "predicted": predicted_values}).dropna()
    if values.empty:
        raise ValueError("No numeric values available for regression metrics.")

    errors = values["actual"] - values["predicted"]
    mae = float(errors.abs().mean())
    rmse = math.sqrt(float((errors**2).mean()))
    total_variance = float(((values["actual"] - values["actual"].mean()) ** 2).sum())
    residual_variance = float((errors**2).sum())
    if total_variance == 0:
        r2 = 1.0 if residual_variance == 0 else 0.0
    else:
        r2 = 1.0 - (residual_variance / total_variance)

    return RegressionMetrics(
        mae=round(mae, 4),
        rmse=round(rmse, 4),
        r2=round(r2, 4),
    )


def run_weight_prediction_sanity_checks(
    artifact: WeightModelArtifact,
    feature_row: dict[str, Any] | pd.Series,
    tolerance_kg: float = 0.02,
) -> list[SanityCheckResult]:
    """Run directional checks on controlled feature changes."""

    base_row = dict(feature_row)
    base_prediction = _predict_raw(artifact, base_row)
    checks = [
        (
            "larger_deficit",
            "lower",
            "Deficit caloric mai mare ar trebui să scadă predicția de greutate.",
            _with_larger_deficit(base_row),
        ),
        (
            "larger_surplus",
            "higher",
            "Surplus caloric mai mare ar trebui să crească predicția de greutate.",
            _with_larger_surplus(base_row),
        ),
        (
            "more_activity",
            "lower",
            "Mai multă activitate ar trebui să scadă predicția de greutate.",
            _with_more_activity(base_row),
        ),
    ]

    results: list[SanityCheckResult] = []
    for name, expected_direction, description, changed_row in checks:
        changed_prediction = _predict_raw(artifact, changed_row)
        if expected_direction == "lower":
            passed = changed_prediction <= base_prediction + tolerance_kg
        else:
            passed = changed_prediction >= base_prediction - tolerance_kg

        results.append(
            SanityCheckResult(
                name=name,
                passed=bool(passed),
                base_prediction_kg=round(base_prediction, 3),
                changed_prediction_kg=round(changed_prediction, 3),
                expected_direction=expected_direction,
                description=description,
            )
        )
    return results


def _prepare_evaluation_dataset(
    dataset: pd.DataFrame,
    artifact: WeightModelArtifact,
) -> pd.DataFrame:
    if dataset is None or dataset.empty:
        raise ValueError("dataset is empty.")

    feature_columns = list(artifact.metadata["feature_columns"])
    required_columns = feature_columns + [TARGET_COLUMN]
    missing_columns = [column for column in required_columns if column not in dataset.columns]
    if missing_columns:
        raise ValueError(
            "dataset is missing columns: " + ", ".join(sorted(missing_columns)) + "."
        )

    prepared_dataset = dataset.copy()
    for column in required_columns:
        prepared_dataset[column] = pd.to_numeric(prepared_dataset[column], errors="coerce")

    prepared_dataset = prepared_dataset.dropna(subset=required_columns)
    if prepared_dataset.empty:
        raise ValueError("dataset has no complete rows for evaluation.")
    return prepared_dataset.reset_index(drop=True)


def _no_change_baseline(dataset: pd.DataFrame) -> pd.Series:
    return pd.Series([0.0] * dataset.shape[0], index=dataset.index)


def _trend_projection_baseline(dataset: pd.DataFrame) -> pd.Series:
    horizon_days = pd.to_numeric(dataset["horizon_days"], errors="coerce")
    feature_window_days = pd.to_numeric(dataset["feature_window_days"], errors="coerce")
    weight_trend = pd.to_numeric(dataset["weight_trend_kg"], errors="coerce").fillna(0.0)
    scale = horizon_days / feature_window_days.replace(0, pd.NA)
    return (weight_trend * scale.fillna(0.0)).fillna(0.0)


def _energy_balance_projection_baseline(dataset: pd.DataFrame) -> pd.Series:
    horizon_days = pd.to_numeric(dataset["horizon_days"], errors="coerce")
    balance = pd.to_numeric(
        dataset["estimated_balance_avg_logged_days"], errors="coerce"
    ).fillna(0.0)
    return (balance * horizon_days / 7700.0).fillna(0.0)


def _representative_feature_row(dataset: pd.DataFrame) -> dict[str, Any]:
    numeric_dataset = dataset.copy()
    numeric_dataset["abs_target"] = pd.to_numeric(
        numeric_dataset[TARGET_COLUMN], errors="coerce"
    ).abs()
    sorted_rows = numeric_dataset.sort_values("abs_target").reset_index(drop=True)
    return dict(sorted_rows.iloc[len(sorted_rows) // 2])


def _with_larger_deficit(feature_row: dict[str, Any]) -> dict[str, Any]:
    changed_row = dict(feature_row)
    food_days = max(1.0, float(changed_row.get("food_days", 1.0)))
    current_calories = float(changed_row.get("calories_avg_logged_days", 0.0))
    changed_row["calories_avg_logged_days"] = max(800.0, current_calories - 400.0)
    changed_row["calories_total"] = changed_row["calories_avg_logged_days"] * food_days
    changed_row["estimated_balance_avg_logged_days"] = (
        float(changed_row.get("estimated_balance_avg_logged_days", 0.0)) - 400.0
    )
    return changed_row


def _with_larger_surplus(feature_row: dict[str, Any]) -> dict[str, Any]:
    changed_row = dict(feature_row)
    food_days = max(1.0, float(changed_row.get("food_days", 1.0)))
    current_calories = float(changed_row.get("calories_avg_logged_days", 0.0))
    changed_row["calories_avg_logged_days"] = current_calories + 400.0
    changed_row["calories_total"] = changed_row["calories_avg_logged_days"] * food_days
    changed_row["estimated_balance_avg_logged_days"] = (
        float(changed_row.get("estimated_balance_avg_logged_days", 0.0)) + 400.0
    )
    return changed_row


def _with_more_activity(feature_row: dict[str, Any]) -> dict[str, Any]:
    changed_row = dict(feature_row)
    window_days = max(1.0, float(changed_row.get("feature_window_days", 1.0)))
    changed_row["activity_calories_avg_all_days"] = (
        float(changed_row.get("activity_calories_avg_all_days", 0.0)) + 150.0
    )
    changed_row["activity_calories_total"] = (
        float(changed_row.get("activity_calories_total", 0.0)) + (150.0 * window_days)
    )
    changed_row["estimated_balance_avg_logged_days"] = (
        float(changed_row.get("estimated_balance_avg_logged_days", 0.0)) - 150.0
    )
    return changed_row


def _predict_raw(artifact: WeightModelArtifact, feature_row: dict[str, Any]) -> float:
    feature_columns = list(artifact.metadata["feature_columns"])
    feature_frame = pd.DataFrame([{column: feature_row[column] for column in feature_columns}])
    return float(artifact.model.predict(feature_frame)[0])
