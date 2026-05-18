"""Train and persist MacroSense ML model artifacts."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from services.ml.artifacts import DEFAULT_MODEL_ARTIFACT_DIR, save_weight_model_artifacts
from services.ml.synthetic_data import SyntheticDatasetConfig, generate_synthetic_histories
from services.ml.training import (
    ModelTrainingConfig,
    train_weight_prediction_models_for_horizons,
)


def main() -> None:
    args = _parse_args()
    histories = generate_synthetic_histories(
        SyntheticDatasetConfig(
            user_count=args.user_count,
            history_days=args.history_days,
            start_date=date.fromisoformat(args.start_date),
            random_seed=args.random_seed,
            min_user_history_days=args.min_user_history_days,
            history_days_jitter=args.history_days_jitter,
            start_date_jitter_days=args.start_date_jitter_days,
            food_log_calorie_noise=args.food_log_calorie_noise,
            custom_meal_probability=args.custom_meal_probability,
        )
    )
    results = train_weight_prediction_models_for_horizons(
        histories,
        horizon_days_values=tuple(args.horizons),
        feature_window_days=args.feature_window_days,
        feature_min_food_days=args.min_food_days,
        feature_min_weight_days=args.min_weight_days,
        training_config=ModelTrainingConfig(
            min_rows=args.min_rows,
            random_forest_estimators=args.random_forest_estimators,
            random_state=args.random_seed,
            split_strategy=args.split_strategy,
        ),
    )
    training_context = {
        "synthetic_user_count": args.user_count,
        "synthetic_history_days": args.history_days,
        "synthetic_start_date": args.start_date,
        "synthetic_min_user_history_days": args.min_user_history_days,
        "synthetic_history_days_jitter": args.history_days_jitter,
        "synthetic_start_date_jitter_days": args.start_date_jitter_days,
        "synthetic_food_log_calorie_noise": args.food_log_calorie_noise,
        "synthetic_custom_meal_probability": args.custom_meal_probability,
        "random_seed": args.random_seed,
        "split_strategy": args.split_strategy,
        "min_rows": args.min_rows,
        "random_forest_estimators": args.random_forest_estimators,
    }
    artifacts = save_weight_model_artifacts(
        results,
        args.output_dir,
        training_context=training_context,
    )

    print("Saved MacroSense ML model artifacts")
    for horizon_days, artifact in artifacts.items():
        metadata = artifact.metadata
        print(
            f"- {horizon_days} days: "
            f"best={metadata['best_model_name']}, "
            f"rows={metadata['row_count']}, "
            f"model={artifact.model_path.as_posix()}, "
            f"metadata={artifact.metadata_path.as_posix()}"
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train MacroSense synthetic weight prediction models."
    )
    parser.add_argument("--user-count", type=int, default=20)
    parser.add_argument("--history-days", type=int, default=120)
    parser.add_argument("--start-date", default="2025-09-01")
    parser.add_argument("--random-seed", type=int, default=2026)
    parser.add_argument("--min-user-history-days", type=int, default=45)
    parser.add_argument("--history-days-jitter", type=int, default=45)
    parser.add_argument("--start-date-jitter-days", type=int, default=45)
    parser.add_argument("--food-log-calorie-noise", type=float, default=0.06)
    parser.add_argument("--custom-meal-probability", type=float, default=0.22)
    parser.add_argument("--horizons", type=int, nargs="+", default=[14, 30])
    parser.add_argument("--feature-window-days", type=int, default=None)
    parser.add_argument("--min-food-days", type=int, default=None)
    parser.add_argument("--min-weight-days", type=int, default=None)
    parser.add_argument("--min-rows", type=int, default=60)
    parser.add_argument("--random-forest-estimators", type=int, default=10)
    parser.add_argument("--split-strategy", choices=["user", "row"], default="user")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_MODEL_ARTIFACT_DIR,
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
