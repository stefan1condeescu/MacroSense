import inspect
import unittest
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import patch

from services.what_if.simulator import describe_balance_delta
from ui import language
from ui.pages import what_if_page
from ui.pages.what_if_page import (
    REFERENCE_CONTEXT_COLUMN_WEIGHTS,
    WHAT_IF_CONTEXT_KEY,
    WHAT_IF_FOOD_ROWS_KEY,
    WHAT_IF_FORCE_RESET_KEY,
    WHAT_IF_LAST_VALID_COMPARISON_KEY,
    WHAT_IF_LAST_VALID_CONTEXT_KEY,
    WHAT_IF_WIDGET_VERSION_KEY,
    _calculate_activity_row_calories,
    _calculate_food_row_calories,
    _clear_scenario_widget_state,
    _get_last_valid_comparison,
    _comparison_row,
    _format_activity_row_error,
    _format_activity_row_label,
    _format_food_row_error,
    _format_food_row_label,
    _format_remaining_error_count,
    _format_source_context,
    _format_signed_value,
    _format_value,
    _is_strength_category,
    _remember_valid_comparison,
    _reset_scenario_widget_state,
    _sync_scenario_state,
    _validate_manual_calories_ui,
    _versioned_widget_key,
)


class WhatIfPageHelperTests(unittest.TestCase):
    def test_remaining_error_count_follows_selected_language(self):
        expectations = {
            "en": (
                "One more invalid value remains in the scenario.",
                "2 more invalid values remain in the scenario.",
            ),
            "ro": (
                "Încă o valoare invalidă în scenariu.",
                "Încă 2 valori invalide în scenariu.",
            ),
        }

        for language_code, (singular, plural) in expectations.items():
            with self.subTest(language_code=language_code):
                with patch.object(
                    language.st,
                    "session_state",
                    {"language": language_code},
                ):
                    self.assertEqual(_format_remaining_error_count(1), singular)
                    self.assertEqual(_format_remaining_error_count(2), plural)

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

    def test_food_scenario_rows_use_compact_card_controls(self):
        source = inspect.getsource(what_if_page._render_food_scenario_editor)

        self.assertIn("st.container(border=True)", source)
        self.assertIn('label_visibility="collapsed"', source)
        self.assertIn('type="tertiary"', source)

    def test_add_activity_section_matches_activity_journal_inputs(self):
        source = inspect.getsource(what_if_page._render_add_activity_section)

        self.assertIn("what_if_add_activity_sets", source)
        self.assertIn("what_if_add_activity_reps", source)
        self.assertIn("what_if_add_activity_manual_toggle", source)
        self.assertIn("what_if_add_activity_manual", source)
        self.assertIn(
            "Sets and repetitions apply only to strength exercises.",
            source,
        )
        self.assertIn("Estimated calories burned", source)
        self.assertIn("_validate_manual_calories_ui(manual_calories)", source)
        self.assertIn(
            "manual_calories_burned=manual_calories if use_manual_calories else None",
            source,
        )

    def test_food_and_activity_selectors_translate_display_only(self):
        food_source = inspect.getsource(what_if_page._render_add_catalog_food)
        activity_source = inspect.getsource(what_if_page._render_add_activity_section)

        self.assertIn("format_func=format_food_category_for_display", food_source)
        self.assertIn(
            "selection_display_df = build_food_selection_display_dataframe(selection_df)",
            food_source,
        )
        self.assertIn(
            'int(selection_df.iloc[selected_rows[0]]["_food_id"])',
            food_source,
        )

        self.assertIn("format_func=format_activity_category_for_display", activity_source)
        self.assertIn(
            "selection_display_df = build_activity_selection_display_dataframe(selection_df)",
            activity_source,
        )
        self.assertIn(
            'int(selection_df.iloc[selected_rows[0]]["_activity_id"])',
            activity_source,
        )
        self.assertIn('_is_strength_category(selected_activity.get("category"))', activity_source)

    def test_strength_detection_keeps_raw_domain_category(self):
        for language_code in ("en", "ro"):
            with self.subTest(language_code=language_code):
                with patch.object(
                    language.st,
                    "session_state",
                    {"language": language_code},
                ):
                    self.assertTrue(_is_strength_category("Forță"))
                    self.assertFalse(_is_strength_category("Strength"))

    def test_source_context_translates_display_without_changing_row(self):
        row = {
            "entry_type": "Aliment",
            "source_label": "MacroSense",
            "meal_type": "Mic dejun",
            "meal_time": time(9, 0),
        }
        original_row = row.copy()

        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(
                _format_source_context(row),
                "Food | MacroSense | Breakfast, 09:00",
            )
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(
                _format_source_context(row),
                "Aliment | MacroSense | Mic dejun, 09:00",
            )

        self.assertEqual(row, original_row)

    def test_custom_meal_snapshot_source_follows_selected_language(self):
        row = {
            "entry_type": "Masă personalizată",
            "source_label": "Meal snapshot",
            "meal_type": "Prânz",
            "meal_time": time(13, 30),
        }

        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(
                _format_source_context(row),
                "Custom meal | Meal snapshot | Lunch, 13:30",
            )
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(
                _format_source_context(row),
                "Masă personalizată | Snapshot masă | Prânz, 13:30",
            )

    def test_row_validation_uses_natural_labels_in_both_languages(self):
        expectations = {
            "en": (
                "Food: The quantity must be at least 1 g.",
                "Activity: The duration must be at least 0.1 minutes.",
            ),
            "ro": (
                "Aliment: Cantitatea trebuie să fie cel puțin 1 g.",
                "Activitate: Durata trebuie să fie cel puțin 0.1 minute.",
            ),
        }

        for language_code, expected in expectations.items():
            with self.subTest(language_code=language_code):
                with patch.object(
                    language.st,
                    "session_state",
                    {"language": language_code},
                ):
                    self.assertEqual(
                        _format_food_row_error({"label": "", "quantity_g": 0}),
                        expected[0],
                    )
                    self.assertEqual(
                        _format_activity_row_error(
                            {
                                "label": "",
                                "duration_min": 0,
                                "manual_calories_burned": None,
                            }
                        ),
                        expected[1],
                    )

    def test_missing_row_names_follow_language_without_changing_named_entries(self):
        for language_code, expected in (
            ("en", ("Food", "Custom meal", "Activity")),
            ("ro", ("Aliment", "Masă personalizată", "Activitate")),
        ):
            with self.subTest(language_code=language_code):
                with patch.object(language.st, "session_state", {"language": language_code}):
                    self.assertEqual(_format_food_row_label({"label": ""}), expected[0])
                    self.assertEqual(
                        _format_food_row_label(
                            {"label": "", "entry_type": "Masă personalizată"}
                        ),
                        expected[1],
                    )
                    self.assertEqual(_format_activity_row_label({"label": None}), expected[2])
                    for name in ("Food", "Custom meal", "Activity", "Prânzul meu"):
                        row = {"label": name, "entry_type": "Masă personalizată"}
                        self.assertEqual(_format_food_row_label(row), name)
                        self.assertEqual(_format_activity_row_label(row), name)
                        self.assertEqual(row["label"], name)

    def test_manual_calorie_validation_follows_selected_language(self):
        expectations = {
            "en": (
                "Manual calories must be a valid number.",
                "Manual calories must be at least 1 kcal.",
                "Manual calories must be at most 5000 kcal.",
            ),
            "ro": (
                "Caloriile manuale trebuie să fie un număr valid.",
                "Caloriile manuale trebuie să fie cel puțin 1 kcal.",
                "Caloriile manuale trebuie să fie cel mult 5000 kcal.",
            ),
        }

        for language_code, expected in expectations.items():
            with self.subTest(language_code=language_code):
                with patch.object(
                    language.st,
                    "session_state",
                    {"language": language_code},
                ):
                    self.assertEqual(_validate_manual_calories_ui("bad"), expected[0])
                    self.assertEqual(_validate_manual_calories_ui(0), expected[1])
                    self.assertEqual(_validate_manual_calories_ui(5001), expected[2])
                    self.assertIsNone(_validate_manual_calories_ui(250))

    def test_balance_description_is_translated_at_render_boundary(self):
        source = inspect.getsource(what_if_page._render_comparison)

        self.assertIn(
            "translate(describe_balance_delta(comparison.difference.estimated_balance))",
            source,
        )

        expectations = {
            "en": {
                None: (
                    "The estimated balance cannot be compared because food data is "
                    "missing from the real day or the scenario."
                ),
                0: "The estimated balance remains unchanged compared with the real values.",
                -100: (
                    "The scenario lowers the estimated balance and moves further "
                    "toward a deficit."
                ),
                100: (
                    "The scenario raises the estimated balance and moves further "
                    "toward a surplus."
                ),
                50: (
                    "The scenario changes the estimated balance only slightly "
                    "compared with the real values."
                ),
            },
            "ro": {
                None: (
                    "Balanța estimată nu poate fi comparată deoarece lipsește "
                    "alimentația din ziua reală sau din scenariu."
                ),
                0: "Balanța estimată rămâne neschimbată față de valorile reale.",
                -100: "Scenariul scade balanța estimată și merge mai mult spre deficit.",
                100: "Scenariul crește balanța estimată și merge mai mult spre surplus.",
                50: "Scenariul schimbă puțin balanța estimată față de valorile reale.",
            },
        }
        for language_code, language_expectations in expectations.items():
            with patch.object(
                language.st,
                "session_state",
                {"language": language_code},
            ):
                for balance_delta, expected in language_expectations.items():
                    with self.subTest(
                        language_code=language_code,
                        balance_delta=balance_delta,
                    ):
                        self.assertEqual(
                            language.translate(describe_balance_delta(balance_delta)),
                            expected,
                        )

    def test_add_food_buttons_use_primary_what_if_style(self):
        catalog_source = inspect.getsource(what_if_page._render_add_catalog_food)
        custom_meal_source = inspect.getsource(what_if_page._render_add_custom_meal)

        self.assertIn('type="primary"', catalog_source)
        self.assertIn('type="primary"', custom_meal_source)

    def test_food_row_calories_update_from_current_quantity(self):
        calories = _calculate_food_row_calories(
            {
                "scenario_id": "food_1",
                "entry_type": "Aliment",
                "label": "Orez",
                "quantity_g": 250.0,
                "calories_100g": 130.0,
                "protein_100g": 2.7,
                "carbs_100g": 28.0,
                "fats_100g": 0.3,
            }
        )

        self.assertEqual(calories, 325.0)

    def test_food_row_calories_are_unavailable_for_invalid_quantity(self):
        calories = _calculate_food_row_calories(
            {
                "scenario_id": "food_1",
                "entry_type": "Aliment",
                "label": "Orez",
                "quantity_g": -1.0,
                "calories_100g": 130.0,
                "protein_100g": 2.7,
                "carbs_100g": 28.0,
                "fats_100g": 0.3,
            }
        )

        self.assertIsNone(calories)

    def test_activity_row_calories_update_from_manual_override(self):
        calories = _calculate_activity_row_calories(
            {
                "scenario_id": "activity_1",
                "label": "Alergare",
                "category": "Cardio",
                "duration_min": 35.0,
                "met": 7.0,
                "manual_calories_burned": 420.0,
            },
            reference_weight=75.0,
        )

        self.assertEqual(calories, 420.0)

    def test_activity_row_calories_are_unavailable_for_invalid_duration(self):
        calories = _calculate_activity_row_calories(
            {
                "scenario_id": "activity_1",
                "label": "Alergare",
                "category": "Cardio",
                "duration_min": -1.0,
                "met": 7.0,
            },
            reference_weight=75.0,
        )

        self.assertIsNone(calories)

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
            "what_if_add_activity_sets": 3,
            "what_if_add_activity_sets_3": 4,
            "what_if_add_activity_reps": 12,
            "what_if_add_activity_reps_3": 15,
            "what_if_add_activity_manual_toggle": True,
            "what_if_add_activity_manual_toggle_3": True,
            "what_if_add_activity_manual": 240.0,
            "what_if_add_activity_manual_3": 300.0,
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
            "what_if_add_activity_sets_3": 5,
            "what_if_add_activity_manual_toggle_3": True,
            "what_if_add_activity_manual_3": 400.0,
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
            self.assertNotIn("what_if_add_activity_sets_3", fake_state)
            self.assertNotIn("what_if_add_activity_manual_3", fake_state)

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
