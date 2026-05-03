import unittest

import pandas as pd

from ui.tables import filter_food_catalog_dataframe


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

    def test_food_catalog_search_treats_special_characters_as_plain_text(self):
        filtered = filter_food_catalog_dataframe(self.foods, "(", "Toate", "Toate")

        self.assertEqual(filtered["Denumire"].tolist(), ["Test (raw)"])

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


if __name__ == "__main__":
    unittest.main()
