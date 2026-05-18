"""CLI utility for evaluating saved MacroSense ML model artifacts."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

from services.ml.artifacts import DEFAULT_MODEL_ARTIFACT_DIR, load_weight_model_artifact
from services.ml.evaluation import WeightModelEvaluation, evaluate_weight_model_on_dataset
from services.ml.feature_engineering import (
    build_default_weight_prediction_feature_config,
    build_weight_prediction_dataset,
)
from services.ml.synthetic_data import SyntheticDatasetConfig, generate_synthetic_histories


def main() -> None:
    _configure_stdout_encoding()
    args = _parse_args()
    histories = generate_synthetic_histories(
        SyntheticDatasetConfig(
            user_count=args.user_count,
            history_days=args.history_days,
            start_date=date.fromisoformat(args.start_date),
            random_seed=args.evaluation_seed,
        )
    )

    print("MacroSense ML evaluation")
    print(f"- synthetic evaluation users: {args.user_count}")
    print(f"- synthetic evaluation history days: {args.history_days}")
    print(f"- evaluation seed: {args.evaluation_seed}")

    for horizon_days in args.horizons:
        dataset = build_weight_prediction_dataset(
            histories.profile_rows,
            histories.food_rows,
            histories.activity_rows,
            histories.weight_rows,
            build_default_weight_prediction_feature_config(
                horizon_days=horizon_days,
                feature_window_days=args.feature_window_days,
                min_food_days=args.min_food_days,
                min_weight_days=args.min_weight_days,
            ),
        )
        if dataset.shape[0] < args.min_rows:
            print(
                f"\n{horizon_days} days: skipped, only {dataset.shape[0]} "
                f"evaluation rows available."
            )
            continue

        try:
            artifact = load_weight_model_artifact(horizon_days, args.artifact_dir)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            print(f"\n{horizon_days} days: skipped, {exc}")
            continue

        report = evaluate_weight_model_on_dataset(artifact, dataset)
        _print_report(report)


def _print_report(report: WeightModelEvaluation) -> None:
    print(f"\n{report.horizon_days} days")
    print(f"- rows: {report.row_count}")
    print(f"- model: {report.model_name}")
    print(f"- model metrics: {_format_metrics(report.model_metrics)}")
    for baseline in report.baseline_evaluations:
        improvement = baseline.metrics.mae - report.model_metrics.mae
        print(
            f"- baseline {baseline.name}: {_format_metrics(baseline.metrics)} "
            f"(MAE improvement: {improvement:+.4f} kg)"
        )
    print(f"- verdict: {_build_verdict(report)}")

    print("- sanity checks:")
    for check in report.sanity_checks:
        status = "PASS" if check.passed else "WARN"
        print(
            f"  {status} {check.name}: "
            f"{check.base_prediction_kg:+.3f} kg -> "
            f"{check.changed_prediction_kg:+.3f} kg "
            f"(expected {check.expected_direction})"
        )


def _format_metrics(metrics: object) -> str:
    return (
        f"MAE={metrics.mae:.4f}, "
        f"RMSE={metrics.rmse:.4f}, "
        f"R2={metrics.r2:.4f}"
    )


def _build_verdict(report: WeightModelEvaluation) -> str:
    baselines = {
        baseline.name: baseline.metrics.mae
        for baseline in report.baseline_evaluations
    }
    model_mae = report.model_metrics.mae
    beats_no_change = model_mae < baselines.get("no_change", float("inf"))
    beats_trend = model_mae < baselines.get("trend_projection", float("inf"))
    beats_energy = model_mae < baselines.get(
        "energy_balance_projection", float("inf")
    )
    sanity_passed = all(check.passed for check in report.sanity_checks)

    if beats_no_change and beats_trend and beats_energy and sanity_passed:
        return "strong - beats all baselines and passes sanity checks"
    if beats_no_change and beats_trend and sanity_passed:
        return "acceptable - beats simple baselines, energy reference remains stronger"
    if beats_no_change and sanity_passed:
        return "weak - beats no-change only, review model before relying on it"
    return "not ready - does not beat basic baselines or fails sanity checks"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate saved MacroSense weight prediction models."
    )
    parser.add_argument("--user-count", type=int, default=30)
    parser.add_argument("--history-days", type=int, default=100)
    parser.add_argument("--start-date", default="2026-01-01")
    parser.add_argument("--evaluation-seed", type=int, default=9090)
    parser.add_argument("--horizons", type=int, nargs="+", default=[14, 30])
    parser.add_argument("--feature-window-days", type=int, default=None)
    parser.add_argument("--min-food-days", type=int, default=None)
    parser.add_argument("--min-weight-days", type=int, default=None)
    parser.add_argument("--min-rows", type=int, default=30)
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
