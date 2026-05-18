"""Terminal utility for predicting one real MacroSense user's weight change."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from services.ml.artifacts import DEFAULT_MODEL_ARTIFACT_DIR
from services.ml.prediction import get_user_weight_predictions


def main() -> None:
    _configure_stdout_encoding()
    args = _parse_args()
    analysis_date = date.fromisoformat(args.analysis_date) if args.analysis_date else None
    result = get_user_weight_predictions(
        args.user_id,
        analysis_date=analysis_date,
        artifact_dir=args.artifact_dir,
        horizons=tuple(args.horizons),
    )

    print(f"Weight predictions for user_id={result.user_id}")
    print(f"- analysis date: {result.analysis_date.isoformat()}")
    if result.predictions:
        for prediction in result.predictions:
            print(
                f"- {prediction.horizon_days} days "
                f"({prediction.target_date.isoformat()}): "
                f"{prediction.predicted_weight_kg:.2f} kg "
                f"({prediction.predicted_change_kg:+.2f} kg), "
                f"model={prediction.model_name}, "
                f"MAE={prediction.metrics.get('mae')}"
            )
    if result.unavailable_horizons:
        print("- unavailable:")
        for horizon_days, reason in result.unavailable_horizons.items():
            print(f"  {horizon_days} days: {reason}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Predict weight change for one MacroSense user."
    )
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--analysis-date", default=None)
    parser.add_argument("--horizons", type=int, nargs="+", default=[14, 30])
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=DEFAULT_MODEL_ARTIFACT_DIR,
    )
    return parser.parse_args()


def _configure_stdout_encoding() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    main()
