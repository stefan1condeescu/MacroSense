import unittest

from ui.pages.food_journal_page import (
    build_food_selection_dataframe,
    build_food_selection_state_key,
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

    def test_food_selection_key_changes_when_visible_catalog_context_changes(self):
        initial_key = build_food_selection_state_key("", "Toate")
        filtered_key = build_food_selection_state_key("broccoli", "Toate")

        self.assertNotEqual(initial_key, filtered_key)
        self.assertEqual(
            build_food_selection_state_key("  Broccoli  ", "Toate"),
            filtered_key
        )


if __name__ == "__main__":
    unittest.main()
