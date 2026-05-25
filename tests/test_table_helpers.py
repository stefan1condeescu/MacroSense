import unittest

import pandas as pd

from ui.activity_selection import (
    build_activity_selection_dataframe,
    build_activity_selection_state_key,
    get_activity_category_filter_options,
)
from ui.activity_validation import validate_duration_minutes, validate_reps, validate_sets
from ui.tables import (
    build_log_entry_card_html,
    build_weight_log_cards_html,
    escape_display_text,
    filter_activity_catalog_dataframe,
    filter_food_catalog_dataframe,
    get_food_log_card_style,
)


class TableHelperTests(unittest.TestCase):
    def setUp(self):
        self.foods = pd.DataFrame(
            [
                {
                    "Denumire": "Test (raw)",
                    "Categorie": "Altele",
                    "Sursă": "MacroSense",
                },
                {
                    "Denumire": "Broccoli, crud",
                    "Categorie": "Legume",
                    "Sursă": "USDA Foundation",
                },
                {
                    "Denumire": "Căpșuni, crude",
                    "Categorie": "Fructe",
                    "Sursă": "USDA SR",
                },
            ]
        )
        self.activities = pd.DataFrame(
            [
                {
                    "Denumire": "Flotări moderate",
                    "Categorie": "Forță",
                    "Sursă": "MacroSense",
                    "Metodă MET": "Mapare MacroSense",
                },
                {
                    "Denumire": "Alergare ușoară generală",
                    "Categorie": "Cardio",
                    "Sursă": "Compendium",
                    "Metodă MET": "Oficial Compendium",
                },
            ]
        )

    def test_food_catalog_search_treats_special_characters_as_plain_text(self):
        filtered = filter_food_catalog_dataframe(self.foods, "(", "Toate", "Toate")

        self.assertEqual(filtered["Denumire"].tolist(), ["Test (raw)"])

    def test_custom_card_text_is_html_escaped(self):
        self.assertEqual(escape_display_text("<b>Test</b>"), "&lt;b&gt;Test&lt;/b&gt;")

    def test_custom_meal_food_log_cards_use_meal_color_class(self):
        self.assertEqual(
            get_food_log_card_style("Masă personalizată"),
            ("custom-meal", "custom-meal"),
        )

        card_html = build_log_entry_card_html(
            title="Bol proteic",
            badge="Masă personalizată",
            card_type="custom-meal",
            badge_type="custom-meal",
            metrics=[("Calorii", "450 kcal")],
        )

        self.assertIn("log-entry-card custom-meal", card_html)
        self.assertIn("log-entry-badge custom-meal", card_html)

    def test_weight_log_cards_become_scrollable_for_long_history(self):
        weight_rows = pd.DataFrame(
            [
                {"Data": f"2026-05-{day:02d}", "Greutate (kg)": 70.0 + day}
                for day in range(1, 9)
            ]
        )

        cards_html, is_scrollable = build_weight_log_cards_html(weight_rows)

        self.assertTrue(is_scrollable)
        self.assertIn("weight-history-list is-scrollable", cards_html)

    def test_food_catalog_search_does_not_crash_on_invalid_regex_text(self):
        filtered = filter_food_catalog_dataframe(self.foods, "[", "Toate", "Toate")

        self.assertTrue(filtered.empty)

    def test_food_catalog_filter_combines_category_and_source(self):
        filtered = filter_food_catalog_dataframe(
            self.foods,
            "",
            "Legume",
            "USDA Foundation"
        )

        self.assertEqual(filtered["Denumire"].tolist(), ["Broccoli, crud"])

    def test_food_catalog_search_ignores_diacritics(self):
        filtered = filter_food_catalog_dataframe(self.foods, "capsuni", "Toate", "Toate")

        self.assertEqual(filtered["Denumire"].tolist(), ["Căpșuni, crude"])

    def test_activity_catalog_filter_combines_search_source_and_method(self):
        filtered = filter_activity_catalog_dataframe(
            self.activities,
            "flotari",
            "Forță",
            "MacroSense",
            "Mapare MacroSense",
        )

        self.assertEqual(filtered["Denumire"].tolist(), ["Flotări moderate"])

    def test_activity_selection_filters_without_diacritics(self):
        activity_options = {
            1: {
                "id": 1,
                "name": "Flotări moderate",
                "category": "Forță",
                "source_label": "MacroSense",
                "met_method_label": "Mapare MacroSense",
                "met": 3.8,
            }
        }

        filtered = build_activity_selection_dataframe(activity_options, "flotari", "Toate")

        self.assertEqual(filtered["Denumire"].tolist(), ["Flotări moderate"])
        self.assertEqual(get_activity_category_filter_options(activity_options), ["Toate", "Forță"])

    def test_activity_selection_does_not_truncate_visible_catalog_by_default(self):
        activity_options = {
            index: {
                "id": index,
                "name": f"Activitate test {index:02d}",
                "category": "Cardio",
                "source_label": "Compendium",
                "met_method_label": "Oficial Compendium",
                "met": 4.0,
            }
            for index in range(1, 46)
        }

        filtered = build_activity_selection_dataframe(activity_options, "", "Toate")

        self.assertEqual(len(filtered), 45)
        self.assertEqual(filtered.iloc[-1]["Denumire"], "Activitate test 45")

    def test_activity_selection_can_still_be_limited_when_requested(self):
        activity_options = {
            index: {
                "id": index,
                "name": f"Activitate test {index:02d}",
                "category": "Cardio",
                "source_label": "Compendium",
                "met_method_label": "Oficial Compendium",
                "met": 4.0,
            }
            for index in range(1, 46)
        }

        filtered = build_activity_selection_dataframe(
            activity_options,
            "",
            "Toate",
            max_rows=40,
        )

        self.assertEqual(len(filtered), 40)

    def test_activity_selection_key_changes_when_visible_context_changes(self):
        self.assertNotEqual(
            build_activity_selection_state_key("flotari", "Toate"),
            build_activity_selection_state_key("flotari", "Forță"),
        )

    def test_activity_ui_validation_blocks_native_number_input_edge_cases(self):
        self.assertEqual(validate_duration_minutes(0, "Durata nouă"), "Durata nouă trebuie să fie cel puțin 0.1 minute.")
        self.assertEqual(validate_duration_minutes(601, "Durata nouă"), "Durata nouă trebuie să fie cel mult 600 minute.")
        self.assertEqual(validate_sets(0), "Seturile trebuie să fie cel puțin 1.")
        self.assertEqual(validate_reps(201), "Repetările trebuie să fie cel mult 200.")

    def test_activity_duration_validation_accepts_subminute_values(self):
        self.assertIsNone(validate_duration_minutes(0.1, "Durata nouă"))
        self.assertIsNone(validate_duration_minutes(0.5, "Durata nouă"))


if __name__ == "__main__":
    unittest.main()
