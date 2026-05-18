"""Small terminal smoke-check for the MacroSense ML pipeline."""

from __future__ import annotations

from datetime import date

from services.ml.synthetic_data import SyntheticDatasetConfig, generate_synthetic_histories
from services.ml.training import (
    ModelTrainingConfig,
    train_weight_prediction_models_for_horizons,
)


def main() -> None:
    histories = generate_synthetic_histories(
        SyntheticDatasetConfig(
            user_count=8,
            history_days=70,
            start_date=date(2026, 1, 1),
            random_seed=2026,
        )
    )
    print("Synthetic raw histories")
    print(f"- users: {histories.profile_rows.shape[0]}")
    print(f"- food logs: {histories.food_rows.shape[0]}")
    print(f"- custom meal logs: {(histories.food_rows['source_type'] == 'custom_meal').sum()}")
    print(f"- activity logs: {histories.activity_rows.shape[0]}")
    print(f"- weight logs: {histories.weight_rows.shape[0]}")

    results = train_weight_prediction_models_for_horizons(
        histories,
        horizon_days_values=(14, 30),
        training_config=ModelTrainingConfig(
            min_rows=20,
            random_forest_estimators=10,
            random_state=42,
            split_strategy="row",
        ),
    )

    print("\nWeight prediction models")
    for horizon_days, result in results.items():
        print(f"- {horizon_days} days: best={result.best_model_name}, rows={result.row_count}")
        for model_name, metrics in result.metrics_by_model.items():
            print(
                "  "
                f"{model_name}: "
                f"MAE={metrics['mae']}, "
                f"RMSE={metrics['rmse']}"
            )


if __name__ == "__main__":
    main()
