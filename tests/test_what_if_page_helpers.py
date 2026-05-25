import inspect
import unittest
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import patch

from ui.pages import what_if_page
from ui.pages.what_if_page import (
    REFERENCE_CONTEXT_COLUMN_WEIGHTS,
    WHAT_IF_CONTEXT_KEY,
    WHAT_IF_FOOD_ROWS_KEY,
    WHAT_IF_FORCE_RESET_KEY,
    WHAT_IF_LAST_VALID_COMPARISON_KEY,
    WHAT_IF_LAST_VALID_CONTEXT_KEY,
    WHAT_IF_WIDGET_VERSION_KEY,
    _clear_scenario_widget_state,
    _get_last_valid_comparison,
    _comparison_row,
    _format_remaining_error_count,
    _format_signed_value,
    _format_value,
    _remember_valid_comparison,
    _reset_scenario_widget_state,
    _sync_scenario_state,
    _versioned_widget_key,
)


class WhatIfPageHelperTests(unittest.TestCase):
    def test_remaining_error_count_uses_singular_for_one_error(self):
        self.assertEqual(
            _format_remaining_error_count(1),
            "Încă o valoare invalidă în scenariu.",
        )

    def test_remaining_error_count_uses_plural_for_multiple_errors(self):
        self.assertEqual(
            _format_remaining_error_count(2),
            "Încă 2 valori invalide în scenariu.",
        )

    def test_reference_context_keeps_four_columns_to_replace_dashboard_card_row(self):
        source = inspect.getsource(what_if_page._render_reference_context)

        self.assertEqual(len(REFERENCE_CONTEXT_COLUMN_WEIGHTS), 4)
        self.assertIn("spacer_col", source)

    def test_what_if_loads_day_context_from_selected_date(self):
        source = inspect.getsource(what_if_page.render_what_if_page)

        self.assertIn("max_value=date.today()", source)
        self.assertIn("DailyLog.get_for_date(int(user_id), selected_date)", source)
        self.assertIn("WeightLog.get_reference_for_user(int(user_id), selected_date)", source)
        self.assertIn("get_daily_energy_estimate(int(user_id), selected_date)", source)

    def test_result_table_formats_kcal_like_dashboard_metrics(self):
        self.assertEqual(_format_value(1671.5, "kcal"), "1672 kcal")
        self.assertEqual(_format_value(2327.6, "kcal"), "2328 kcal")
        self.assertEqual(_format_signed_value(-656.1, "kcal"), "-656 kcal")

    def test_result_table_keeps_macro_grams_at_one_decimal(self):
        self.assertEqual(_format_value(193.04, "g"), "193.0 g")
        self.assertEqual(_format_signed_value(-0.04, "g"), "-0.0 g")

    def test_result_table_marks_missing_balance_as_unavailable(self):
        row = _comparison_row(
            "Balanță estimată",
            None,
            None,
            None,
            "kcal",
        )

        self.assertEqual(row["Valori reale"], "\u2014")
        self.assertEqual(row["Scenariu simulat"], "\u2014")
        self.assertEqual(row["Diferență"], "\u2014")

    def test_result_table_marks_foodless_calories_as_unavailable(self):
        row = _comparison_row(
            "Calorii consumate",
            0.0,
            0.0,
            0.0,
            "kcal",
            real_unavailable=True,
            simulated_unavailable=True,
            difference_unavailable=True,
        )

        self.assertEqual(row["Valori reale"], "\u2014")
        self.assertEqual(row["Scenariu simulat"], "\u2014")
        self.assertEqual(row["Diferență"], "\u2014")

    def test_full_reset_clears_visible_scenario_widget_state(self):
        fake_state = {
            "what_if_food_quantity_real_food_1": 150.0,
            "what_if_food_search": "orez",
            "what_if_food_search_3": "paine",
            "what_if_food_category_filter": "Cereale",
            "what_if_food_category_filter_3": "Cereale",
            "what_if_food_selection_table_abcd": {"selection": [0]},
            "what_if_add_food_quantity": 75.0,
            "what_if_add_food_quantity_3": 250.0,
            "what_if_custom_meal_select": 1,
            "what_if_custom_meal_select_3": 1,
            "what_if_add_custom_meal_quantity": 125.0,
            "what_if_add_custom_meal_quantity_3": 300.0,
            "what_if_activity_duration_real_activity_1": 45.0,
            "what_if_activity_sets_real_activity_1": 4,
            "what_if_activity_reps_real_activity_1": 12,
            "what_if_activity_manual_toggle_real_activity_1": True,
            "what_if_activity_manual_real_activity_1": 300.0,
            "what_if_activity_search": "alergare",
            "what_if_activity_search_3": "alergare",
            "what_if_activity_category_filter": "Cardio",
            "what_if_activity_category_filter_3": "Cardio",
            "what_if_activity_selection_table_abcd": {"selection": [0]},
            "what_if_add_activity_duration": 20.0,
            "what_if_add_activity_duration_3": 45.0,
            "what_if_selected_date": "kept",
            WHAT_IF_WIDGET_VERSION_KEY: 3,
        }

        with patch.object(what_if_page, "st", SimpleNamespace(session_state=fake_state)):
            _clear_scenario_widget_state()

        self.assertEqual(
            fake_state,
            {"what_if_selected_date": "kept", WHAT_IF_WIDGET_VERSION_KEY: 3},
        )

    def test_force_reset_bumps_widget_version_for_fresh_add_inputs(self):
        fake_state = {
            WHAT_IF_FORCE_RESET_KEY: True,
            WHAT_IF_WIDGET_VERSION_KEY: 3,
            "what_if_food_search_3": "paine",
            "what_if_add_food_quantity_3": 250.0,
            "what_if_activity_search_3": "alergare",
            "what_if_add_activity_duration_3": 45.0,
        }

        with patch.object(what_if_page, "st", SimpleNamespace(session_state=fake_state)):
            _sync_scenario_state(
                user_id=1,
                selected_date=date(2026, 5, 24),
                real_food_rows=[],
                real_activity_rows=[],
            )
            self.assertEqual(fake_state[WHAT_IF_WIDGET_VERSION_KEY], 4)
            self.assertEqual(_versioned_widget_key("what_if_food_search"), "what_if_food_search_4")
            self.assertNotIn("what_if_food_search_3", fake_state)
            self.assertNotIn("what_if_add_activity_duration_3", fake_state)

    def test_real_food_metadata_refresh_preserves_simulated_quantity(self):
        real_rows_before = [
            {
                "scenario_id": "real_food_1",
                "entry_type": "Aliment",
                "label": "Orez",
                "quantity_g": 500.0,
                "calories_100g": 130.0,
                "protein_100g": 2.7,
                "carbs_100g": 28.0,
                "fats_100g": 0.3,
                "meal_type": "Mic dejun",
                "meal_time": time(9, 0),
                "source_label": "MacroSense",
                "is_existing": True,
            }
        ]
        real_rows_after = [{**real_rows_before[0], "meal_time": time(10, 0)}]
        fake_state = {}

        with patch.object(what_if_page, "st", SimpleNamespace(session_state=fake_state)):
            _sync_scenario_state(
                user_id=1,
                selected_date=date(2026, 5, 24),
                real_food_rows=real_rows_before,
                real_activity_rows=[],
            )
            fake_state[WHAT_IF_FOOD_ROWS_KEY][0]["quantity_g"] = 100.0
            fake_state["what_if_food_quantity_real_food_1"] = 100.0

            _sync_scenario_state(
                user_id=1,
                selected_date=date(2026, 5, 24),
                real_food_rows=real_rows_after,
                real_activity_rows=[],
            )

        self.assertEqual(fake_state[WHAT_IF_FOOD_ROWS_KEY][0]["quantity_g"], 100.0)
        self.assertEqual(fake_state["what_if_food_quantity_real_food_1"], 100.0)
        self.assertEqual(fake_state[WHAT_IF_FOOD_ROWS_KEY][0]["meal_time"], time(10, 0))

    def test_reset_scenario_widget_state_increments_widget_version(self):
        fake_state = {WHAT_IF_WIDGET_VERSION_KEY: 7, "what_if_food_search_7": "paine"}

        with patch.object(what_if_page, "st", SimpleNamespace(session_state=fake_state)):
            _reset_scenario_widget_state()

        self.assertEqual(fake_state, {WHAT_IF_WIDGET_VERSION_KEY: 8})

    def test_last_valid_comparison_is_scoped_to_current_context(self):
        fake_state = {WHAT_IF_CONTEXT_KEY: "user:date:a"}
        comparison = object()

        with patch.object(what_if_page, "st", SimpleNamespace(session_state=fake_state)):
            _remember_valid_comparison(comparison)
            self.assertIs(_get_last_valid_comparison(), comparison)
            fake_state[WHAT_IF_CONTEXT_KEY] = "user:date:b"
            self.assertIsNone(_get_last_valid_comparison())

        self.assertEqual(fake_state[WHAT_IF_LAST_VALID_CONTEXT_KEY], "user:date:a")
        self.assertIs(fake_state[WHAT_IF_LAST_VALID_COMPARISON_KEY], comparison)


if __name__ == "__main__":
    unittest.main()
