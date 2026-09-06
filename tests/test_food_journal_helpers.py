import datetime
import inspect
import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from models.tracking import FoodLog
from ui import language
from ui.catalog_constants import FOOD_CATEGORIES
from ui.food_selection import (
    FOOD_CATEGORY_SOURCE_TEXT,
    build_food_selection_display_dataframe,
    format_food_category_for_display,
    format_food_entry_type,
    format_meal_type,
)
from ui.pages import food_journal_page
from ui.pages.food_journal_page import (
    FOOD_ENTRY_TYPES,
    MEAL_TYPES,
    build_food_selection_dataframe,
    build_food_selection_state_key,
    format_food_journal_date,
    format_food_log_option,
    get_food_category_filter_options,
)


class FoodJournalHelperTests(unittest.TestCase):
    def setUp(self):
        self.food_options = {
            1: {
                "id": 1,
                "name": "Banane, crude",
                "category": "Fructe",
                "calories_100g": 89.0,
                "protein_g": 1.1,
                "carbs_g": 22.8,
                "fats_g": 0.3,
            },
            2: {
                "id": 2,
                "name": "Broccoli, crud",
                "category": "Legume",
                "calories_100g": 31.0,
                "protein_g": 2.6,
                "carbs_g": 3.8,
                "fats_g": 0.3,
            },
            3: {
                "id": 3,
                "name": "Mere Fuji cu coaja, crude",
                "category": "Fructe",
                "calories_100g": 58.2,
                "protein_g": 0.2,
                "carbs_g": 15.4,
                "fats_g": 0.2,
                "source_label": "USDA Foundation",
            },
            4: {
                "id": 4,
                "name": "Căpșuni, crude",
                "category": "Fructe",
                "calories_100g": 32.0,
                "protein_g": 0.7,
                "carbs_g": 7.7,
                "fats_g": 0.3,
                "source_label": "USDA SR",
            },
        }

    def test_category_filter_options_include_all_categories(self):
        self.assertEqual(
            get_food_category_filter_options(self.food_options),
            ["Toate", "Fructe", "Legume"]
        )

    def test_food_selection_filters_by_name(self):
        dataframe = build_food_selection_dataframe(self.food_options, "broc", "Toate")

        self.assertEqual(dataframe["Denumire"].tolist(), ["Broccoli, crud"])

    def test_food_selection_filters_by_multiple_name_terms(self):
        dataframe = build_food_selection_dataframe(self.food_options, "mere fuji", "Toate")

        self.assertEqual(dataframe["Denumire"].tolist(), ["Mere Fuji cu coaja, crude"])

    def test_food_selection_filters_by_category(self):
        dataframe = build_food_selection_dataframe(self.food_options, "", "Fructe")

        self.assertEqual(dataframe["Denumire"].tolist(), ["Banane, crude", "Mere Fuji cu coaja, crude", "Căpșuni, crude"])

    def test_food_selection_filters_without_diacritics(self):
        dataframe = build_food_selection_dataframe(self.food_options, "capsuni", "Toate")

        self.assertEqual(dataframe["Denumire"].tolist(), ["Căpșuni, crude"])

    def test_food_selection_exposes_source_labels(self):
        dataframe = build_food_selection_dataframe(self.food_options, "mere", "Toate")

        self.assertEqual(dataframe["Sursă"].tolist(), ["USDA Foundation"])

    def test_food_selection_does_not_truncate_visible_catalog_by_default(self):
        food_options = {
            index: {
                "id": index,
                "name": f"Aliment test {index:02d}",
                "category": "Altele",
                "calories_100g": 100.0,
                "protein_g": 5.0,
                "carbs_g": 12.0,
                "fats_g": 2.0,
            }
            for index in range(1, 46)
        }

        dataframe = build_food_selection_dataframe(food_options, "", "Toate")

        self.assertEqual(len(dataframe), 45)
        self.assertEqual(dataframe.iloc[-1]["Denumire"], "Aliment test 45")

    def test_food_selection_can_still_be_limited_when_requested(self):
        food_options = {
            index: {
                "id": index,
                "name": f"Aliment test {index:02d}",
                "category": "Altele",
                "calories_100g": 100.0,
                "protein_g": 5.0,
                "carbs_g": 12.0,
                "fats_g": 2.0,
            }
            for index in range(1, 46)
        }

        dataframe = build_food_selection_dataframe(
            food_options,
            "",
            "Toate",
            max_rows=40,
        )

        self.assertEqual(len(dataframe), 40)

    def test_food_selection_key_changes_when_visible_catalog_context_changes(self):
        initial_key = build_food_selection_state_key("", "Toate")
        filtered_key = build_food_selection_state_key("broccoli", "Toate")

        self.assertNotEqual(initial_key, filtered_key)
        self.assertEqual(
            build_food_selection_state_key("  Broccoli  ", "Toate"),
            filtered_key
        )

    def test_food_entry_types_translate_without_changing_internal_values(self):
        self.assertEqual(
            FOOD_ENTRY_TYPES,
            ("Aliment din catalog", "Masă personalizată"),
        )

        with patch.object(language.st, "session_state", {"language": "en"}):
            english_labels = [format_food_entry_type(value) for value in FOOD_ENTRY_TYPES]
        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_labels = [format_food_entry_type(value) for value in FOOD_ENTRY_TYPES]

        self.assertEqual(english_labels, ["Catalog food", "Custom meal"])
        self.assertEqual(
            romanian_labels,
            ["Aliment din catalog", "Masă personalizată"],
        )

    def test_meal_type_labels_translate_without_changing_stored_values(self):
        self.assertEqual(MEAL_TYPES, list(FoodLog.VALID_MEAL_TYPES))

        with patch.object(language.st, "session_state", {"language": "en"}):
            english_labels = [format_meal_type(value) for value in MEAL_TYPES]
        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_labels = [format_meal_type(value) for value in MEAL_TYPES]

        self.assertEqual(english_labels, ["Breakfast", "Lunch", "Dinner", "Snack"])
        self.assertEqual(romanian_labels, list(FoodLog.VALID_MEAL_TYPES))

    def test_food_category_labels_cover_canonical_values_and_unknown_fallback(self):
        self.assertEqual(
            set(FOOD_CATEGORY_SOURCE_TEXT),
            {"Toate", *FOOD_CATEGORIES},
        )

        with patch.object(language.st, "session_state", {"language": "en"}):
            english_labels = {
                stored_value: format_food_category_for_display(stored_value)
                for stored_value in FOOD_CATEGORY_SOURCE_TEXT
            }
            unknown_label = format_food_category_for_display("Future category")

        self.assertEqual(english_labels["Toate"], "All")
        self.assertEqual(english_labels["Fructe"], "Fruits")
        self.assertEqual(english_labels["Pâine & Panificație"], "Bread & bakery products")
        self.assertEqual(english_labels["Altele"], "Other")
        self.assertEqual(unknown_label, "Future category")

    def test_food_selection_display_uses_a_copy_and_preserves_selection_ids(self):
        raw_dataframe = build_food_selection_dataframe(
            self.food_options,
            "",
            "Toate",
        )
        original_dataframe = raw_dataframe.copy(deep=True)

        with patch.object(language.st, "session_state", {"language": "en"}):
            english_dataframe = build_food_selection_display_dataframe(raw_dataframe)
        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_dataframe = build_food_selection_display_dataframe(raw_dataframe)

        assert_frame_equal(raw_dataframe, original_dataframe)
        self.assertEqual(
            english_dataframe["_food_id"].tolist(),
            raw_dataframe["_food_id"].tolist(),
        )
        self.assertEqual(
            english_dataframe["Kcal/100g"].tolist(),
            raw_dataframe["Kcal/100g"].tolist(),
        )
        self.assertEqual(english_dataframe["Categorie"].iloc[0], "Fruits")
        self.assertEqual(romanian_dataframe["Categorie"].iloc[0], "Fructe")

    def test_food_journal_date_uses_the_active_language(self):
        value = datetime.date(2026, 5, 25)

        with patch.object(language.st, "session_state", {"language": "en"}):
            english_date = format_food_journal_date(value)
        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_date = format_food_journal_date(value)

        self.assertEqual(english_date, "25 May 2026")
        self.assertEqual(romanian_date, "25 Mai 2026")

        expected_romanian_months = (
            "Ianuarie",
            "Februarie",
            "Martie",
            "Aprilie",
            "Mai",
            "Iunie",
            "Iulie",
            "August",
            "Septembrie",
            "Octombrie",
            "Noiembrie",
            "Decembrie",
        )
        with patch.object(language.st, "session_state", {"language": "ro"}):
            actual_months = tuple(
                format_food_journal_date(datetime.date(2026, month, 1)).split()[1]
                for month in range(1, 13)
            )
        self.assertEqual(actual_months, expected_romanian_months)

    def test_food_log_option_translates_display_values_but_keeps_numeric_id(self):
        entries = pd.DataFrame(
            [
                {
                    "id": 17,
                    "Tip": "Masă personalizată",
                    "Aliment / Masă": "Bol proteic",
                    "Cantitate (g)": 150,
                    "Masă": "Mic dejun",
                    "Ora": datetime.time(8, 30),
                }
            ]
        ).set_index("id")

        with patch.object(language.st, "session_state", {"language": "en"}):
            english_label = format_food_log_option(entries, 17)
        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_label = format_food_log_option(entries, 17)

        self.assertEqual(
            english_label,
            "Custom meal - Bol proteic (150g, Breakfast, 08:30)",
        )
        self.assertEqual(
            romanian_label,
            "Masă personalizată - Bol proteic (150g, Mic dejun, 08:30)",
        )
        self.assertEqual(entries.index.tolist(), [17])

    def test_food_journal_keeps_raw_meal_values_for_model_writes(self):
        source = inspect.getsource(food_journal_page.render_food_journal_page)

        self.assertIn("meal_type=meal_type", source)
        self.assertIn("meal_type=custom_meal_type", source)
        self.assertIn("edited_meal_type,", source)


if __name__ == "__main__":
    unittest.main()
