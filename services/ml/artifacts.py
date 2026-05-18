"""Persistence helpers for MacroSense ML model artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pandas as pd

from services.ml.training import WeightModelTrainingResult


DEFAULT_MODEL_ARTIFACT_DIR = Path("artifacts/ml")
MODEL_ARTIFACT_VERSION = 1


@dataclass(frozen=True)
class WeightModelArtifact:
    """Loaded weight prediction model and its metadata."""

    horizon_days: int
    model: Any
    metadata: dict[str, Any]
    model_path: Path
    metadata_path: Path


def save_weight_model_artifact(
    result: WeightModelTrainingResult,
    output_dir: Path | str = DEFAULT_MODEL_ARTIFACT_DIR,
    training_context: dict[str, Any] | None = None,
) -> WeightModelArtifact:
    """Save the best trained model and metadata for one horizon."""

    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError("joblib is required for saving ML artifacts.") from exc

    artifact_dir = Path(output_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    horizon_days = int(result.horizon_days)
    model_path = artifact_dir / f"weight_prediction_{horizon_days}d.joblib"
    metadata_path = artifact_dir / f"weight_prediction_{horizon_days}d_metadata.json"

    joblib.dump(result.best_model, model_path)
    metadata = _build_metadata(result, training_context=training_context)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return WeightModelArtifact(
        horizon_days=horizon_days,
        model=result.best_model,
        metadata=metadata,
        model_path=model_path,
        metadata_path=metadata_path,
    )


def save_weight_model_artifacts(
    results: dict[int, WeightModelTrainingResult],
    output_dir: Path | str = DEFAULT_MODEL_ARTIFACT_DIR,
    training_context: dict[str, Any] | None = None,
) -> dict[int, WeightModelArtifact]:
    """Save trained models for multiple horizons."""

    return {
        int(horizon_days): save_weight_model_artifact(
            result,
            output_dir,
            training_context=training_context,
        )
        for horizon_days, result in results.items()
    }


def load_weight_model_artifact(
    horizon_days: int,
    artifact_dir: Path | str = DEFAULT_MODEL_ARTIFACT_DIR,
) -> WeightModelArtifact:
    """Load one saved weight prediction model and metadata."""

    try:
        import joblib
    except ImportError as exc:
        raise RuntimeError("joblib is required for loading ML artifacts.") from exc

    artifact_path = Path(artifact_dir)
    model_path = artifact_path / f"weight_prediction_{int(horizon_days)}d.joblib"
    metadata_path = artifact_path / f"weight_prediction_{int(horizon_days)}d_metadata.json"

    if not model_path.exists():
        raise FileNotFoundError(f"Missing model artifact: {model_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing metadata artifact: {metadata_path}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    _validate_metadata(metadata, int(horizon_days))
    model = joblib.load(model_path)

    return WeightModelArtifact(
        horizon_days=int(horizon_days),
        model=model,
        metadata=metadata,
        model_path=model_path,
        metadata_path=metadata_path,
    )


def predict_weight_change(
    artifact: WeightModelArtifact,
    feature_row: dict[str, Any] | pd.Series,
) -> float:
    """Predict future weight change for one prepared feature row."""

    feature_columns = list(artifact.metadata["feature_columns"])
    feature_frame = pd.DataFrame([{column: feature_row[column] for column in feature_columns}])
    prediction = artifact.model.predict(feature_frame)[0]
    return round(float(prediction), 3)


def _build_metadata(
    result: WeightModelTrainingResult,
    training_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_version": MODEL_ARTIFACT_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "problem_type": "weight_change_regression",
        "horizon_days": int(result.horizon_days),
        "target_column": "target_weight_change_kg",
        "best_model_name": result.best_model_name,
        "selection_policy": "best_conservative_energy_trend_model_by_mae",
        "feature_columns": list(result.feature_columns),
        "metrics_by_model": result.metrics_by_model,
        "row_count": int(result.row_count),
        "train_row_count": int(result.train_row_count),
        "test_row_count": int(result.test_row_count),
        "training_context": training_context or {},
    }


def _validate_metadata(metadata: dict[str, Any], expected_horizon_days: int) -> None:
    if metadata.get("artifact_version") != MODEL_ARTIFACT_VERSION:
        raise ValueError("Unsupported ML artifact version.")
    if metadata.get("problem_type") != "weight_change_regression":
        raise ValueError("Unsupported ML artifact problem type.")
    if int(metadata.get("horizon_days", -1)) != int(expected_horizon_days):
        raise ValueError("ML artifact horizon does not match the requested horizon.")
    if not metadata.get("feature_columns"):
        raise ValueError("ML artifact metadata has no feature columns.")
