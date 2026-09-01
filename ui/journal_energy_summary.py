from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd
import streamlit as st

from ui.formatters import format_kcal_for_display
from ui.language import translate


MISSING_FOOD_SOURCE_TEXT = "Not logged"


def build_daily_energy_summary_cards(energy_estimate: dict[str, Any]) -> list[dict[str, str]]:
    """Builds dashboard-compatible daily energy cards for journal pages."""
    has_food_logs = bool(energy_estimate.get("has_food_logs"))
    activity_calories = _zero_if_missing(energy_estimate.get("activity_calories_burned"))

    return [
        {
            "label": translate("Calories consumed"),
            "value": _format_food_calories(energy_estimate),
            "accent": "food",
        },
        {
            "label": translate("Activity calories"),
            "value": format_kcal_for_display(activity_calories),
            "accent": "activity",
        },
        {
            "label": translate("Estimated TDEE"),
            "value": format_kcal_for_display(energy_estimate.get("estimated_tdee")),
            "accent": "energy",
        },
        {
            "label": translate("Estimated balance"),
            "value": (
                format_kcal_for_display(energy_estimate.get("estimated_balance"), signed=True)
                if has_food_logs
                else translate(MISSING_FOOD_SOURCE_TEXT)
            ),
            "accent": "balance",
        },
    ]


def render_daily_energy_summary(energy_estimate: dict[str, Any]) -> None:
    cards = build_daily_energy_summary_cards(energy_estimate)
    st.markdown(
        "".join(
            [
                '<div class="journal-energy-summary">',
                *[_build_card_html(card) for card in cards],
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def _format_food_calories(energy_estimate: dict[str, Any]) -> str:
    if not energy_estimate.get("has_food_logs"):
        return translate(MISSING_FOOD_SOURCE_TEXT)
    return format_kcal_for_display(energy_estimate.get("food_calories_in"))


def _zero_if_missing(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _build_card_html(card: dict[str, str]) -> str:
    return (
        f'<div class="journal-energy-card {escape(card["accent"])}">'
        f'<span>{escape(card["label"])}</span>'
        f'<strong>{escape(card["value"])}</strong>'
        "</div>"
    )
