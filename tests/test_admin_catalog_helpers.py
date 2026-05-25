import unittest
from unittest.mock import patch

from ui.pages.admin_catalog_pages import (
    build_usda_preview_metric_html,
    show_first_validation_error,
    suggest_food_category,
    validate_activity_input,
    validate_food_item_input,
)


class AdminFoodCatalogHelperTests(unittest.TestCase):
    def test_manual_food_requires_name(self):
        errors = validate_food_item_input("", 100, 1, 2, 3)

        self.assertIn("Denumirea alimentului este obligatorie.", errors)

    def test_manual_food_rejects_html_like_name(self):
        errors = validate_food_item_input("A <span>Test</span>", 100, 1, 2, 3)

        self.assertIn("Denumirea alimentului nu poate conține caractere de tip HTML.", errors)

    def test_manual_food_rejects_special_only_name(self):
        errors = validate_food_item_input("///", 100, 1, 2, 3)

        self.assertIn("Denumirea alimentului trebuie să conțină cel puțin o literă.", errors)

    def test_manual_food_rejects_zero_calories_and_empty_macros(self):
        errors = validate_food_item_input("Test", 0, 0, 0, 0)

        self.assertIn("Caloriile trebuie să fie mai mari decât 0.", errors)
        self.assertIn("Completează cel puțin un macronutrient mai mare decât 0.", errors)

    def test_manual_food_rejects_zero_calories_even_with_macro_values(self):
        errors = validate_food_item_input("Test", 0, 1, 0, 0)

        self.assertIn("Caloriile trebuie să fie mai mari decât 0.", errors)

    def test_manual_food_rejects_empty_macros_even_with_calories(self):
        errors = validate_food_item_input("Test", 100, 0, 0, 0)

        self.assertIn("Completează cel puțin un macronutrient mai mare decât 0.", errors)

    def test_manual_food_rejects_negative_nutrition_values(self):
        errors = validate_food_item_input("Test", 100, -1, 2, 3)

        self.assertIn("Valorile nutriționale nu pot fi negative.", errors)

    def test_admin_forms_display_only_first_validation_error(self):
        errors = validate_food_item_input("", 0, 0, 0, 0)

        with patch("ui.pages.admin_catalog_pages.st.error") as mock_error:
            show_first_validation_error(errors)

        mock_error.assert_called_once_with(errors[0])

    def test_manual_food_allows_some_zero_nutrition_values(self):
        errors = validate_food_item_input("Test", 50, 0, 10, 0)

        self.assertEqual(errors, [])

    def test_suggest_food_category_handles_common_usda_descriptions(self):
        examples = {
            "Ice cream, vanilla": "Dulciuri",
            "Chicken breast, raw": "Carne",
            "Orange juice, raw": "Băuturi & Sucuri",
            "Pork sausage": "Mezeluri",
            "Atlantic salmon, raw": "Pește",
            "Eggplant, raw": "Legume",
            "Egg white, raw": "Ouă",
            "Unmapped sample": "Altele",
        }

        for description, expected_category in examples.items():
            with self.subTest(description=description):
                self.assertEqual(suggest_food_category(description), expected_category)

    def test_usda_preview_metric_uses_compact_escaped_html(self):
        html = build_usda_preview_metric_html("Calorii", '519.0 <kcal>')

        self.assertIn('class="usda-preview-metric"', html)
        self.assertIn("Calorii", html)
        self.assertIn("519.0 &lt;kcal&gt;", html)

    def test_manual_activity_requires_name(self):
        errors = validate_activity_input("", 5.0, "Cardio")

        self.assertIn("Denumirea activității este obligatorie.", errors)

    def test_manual_activity_rejects_html_like_name(self):
        errors = validate_activity_input("A <span>Test</span>", 5.0, "Cardio")

        self.assertIn("Denumirea activității nu poate conține caractere de tip HTML.", errors)

    def test_manual_activity_rejects_special_only_name(self):
        errors = validate_activity_input("///", 5.0, "Cardio")

        self.assertIn("Denumirea activității trebuie să conțină cel puțin o literă.", errors)

    def test_manual_activity_requires_positive_met(self):
        errors = validate_activity_input("Test", 0, "Cardio")

        self.assertIn("Coeficientul MET trebuie să fie cel puțin 0.9.", errors)

    def test_manual_activity_allows_valid_input(self):
        errors = validate_activity_input("Alergare", 8.0, "Cardio")

        self.assertEqual(errors, [])

    @patch("ui.pages.admin_catalog_pages.Activity.name_exists_normalized", return_value=True)
    def test_manual_activity_rejects_duplicate_name_when_requested(self, _mock_exists):
        errors = validate_activity_input("Alergare", 8.0, "Cardio", check_duplicate=True)

        self.assertIn("Există deja o activitate cu această denumire.", errors)


if __name__ == "__main__":
    unittest.main()
