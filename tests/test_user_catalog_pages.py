import unittest
from unittest.mock import patch

import pandas as pd

from ui import language
from ui.pages import user_catalog_pages


class UserCatalogPageTests(unittest.TestCase):
    def test_empty_user_catalog_pages_render_in_english_and_romanian(self):
        expected_copy = {
            "en": {
                "headers": ["🍎 Food catalog", "🏃‍♂️ Physical activity catalog"],
                "subheaders": ["Nutrition database", "Available activities"],
                "info": [
                    "The catalog is currently empty. The administrator will add data soon.",
                    "The activity catalog is currently empty.",
                ],
            },
            "ro": {
                "headers": ["🍎 Catalog Alimente", "🏃‍♂️ Catalog Activități Fizice"],
                "subheaders": ["Baza de date nutrițională", "Lista activităților disponibile"],
                "info": [
                    "Catalogul este gol în acest moment. Administratorul va adăuga date în curând.",
                    "Catalogul de activități este gol în acest moment.",
                ],
            },
        }

        for language_code, expected in expected_copy.items():
            with self.subTest(language_code=language_code):
                with (
                    patch.object(
                        language.st,
                        "session_state",
                        {"language": language_code},
                    ),
                    patch.object(
                        user_catalog_pages.FoodItem,
                        "get_all_as_dataframe",
                        return_value=pd.DataFrame(),
                    ),
                    patch.object(
                        user_catalog_pages.Activity,
                        "get_all_as_dataframe",
                        return_value=pd.DataFrame(),
                    ),
                    patch.object(user_catalog_pages.st, "header") as header_mock,
                    patch.object(user_catalog_pages.st, "subheader") as subheader_mock,
                    patch.object(user_catalog_pages.st, "info") as info_mock,
                ):
                    user_catalog_pages.render_user_food_catalog_page()
                    user_catalog_pages.render_user_activity_catalog_page()

                self.assertEqual(
                    [call.args[0] for call in header_mock.call_args_list],
                    expected["headers"],
                )
                self.assertEqual(
                    [call.args[0] for call in subheader_mock.call_args_list],
                    expected["subheaders"],
                )
                self.assertEqual(
                    [call.args[0] for call in info_mock.call_args_list],
                    expected["info"],
                )


if __name__ == "__main__":
    unittest.main()
