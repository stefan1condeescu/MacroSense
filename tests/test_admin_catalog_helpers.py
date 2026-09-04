import ast
import inspect
import unittest
from unittest.mock import patch

from ui import language
from ui.catalog_constants import (
    ACTIVITY_CATEGORIES,
    FOOD_CATEGORIES,
    USDA_DATA_TYPES,
)
from ui.pages import admin_catalog_pages
from ui.pages.admin_catalog_pages import (
    build_usda_preview_metric_html,
    show_first_validation_error,
    suggest_food_category,
    validate_activity_input,
    validate_food_item_input,
)
from ui.translations_ro import ROMANIAN_TRANSLATIONS


class AdminFoodCatalogHelperTests(unittest.TestCase):
    def setUp(self):
        language_patch = patch.object(language.st, "session_state", {"language": "ro"})
        language_patch.start()
        self.addCleanup(language_patch.stop)

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

    def test_manual_catalog_validation_uses_english_source_text(self):
        with patch.object(language.st, "session_state", {"language": "en"}):
            food_errors = validate_food_item_input("", 0, 0, 0, 0)
            activity_errors = validate_activity_input("", 0, "")

        self.assertIn("Food name is required.", food_errors)
        self.assertIn("Calories must be greater than 0.", food_errors)
        self.assertIn("Enter at least one macronutrient greater than 0.", food_errors)
        self.assertIn("Activity name is required.", activity_errors)
        self.assertIn("The MET coefficient must be at least 0.9.", activity_errors)
        self.assertIn("Activity category is required.", activity_errors)

    def test_admin_catalog_english_source_text_has_romanian_translations(self):
        source_tree = ast.parse(inspect.getsource(admin_catalog_pages))
        source_keys = {
            node.args[0].value
            for node in ast.walk(source_tree)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "translate"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            )
        }

        for source_key in source_keys:
            with self.subTest(source_key=source_key):
                self.assertIn(source_key, ROMANIAN_TRANSLATIONS)

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

    def test_admin_category_widgets_format_raw_values_only_for_display(self):
        food_page_source = inspect.getsource(
            admin_catalog_pages.render_admin_food_catalog_page
        )
        usda_panel_source = inspect.getsource(
            admin_catalog_pages.render_usda_food_import_panel
        )
        activity_page_source = inspect.getsource(
            admin_catalog_pages.render_admin_activity_catalog_page
        )

        self.assertIn("format_func=format_food_category_for_display", food_page_source)
        self.assertIn("format_func=format_food_category_for_display", usda_panel_source)
        self.assertIn(
            "format_func=format_activity_category_for_display",
            activity_page_source,
        )
        self.assertIn("Pește", FOOD_CATEGORIES)
        self.assertIn("Forță", ACTIVITY_CATEGORIES)
        self.assertEqual(
            USDA_DATA_TYPES,
            ["SR Legacy", "Foundation", "Survey (FNDDS)"],
        )

        raw_food_category = suggest_food_category("Atlantic salmon, raw")
        with patch.object(language.st, "session_state", {"language": "en"}):
            displayed_food_category = (
                admin_catalog_pages.format_food_category_for_display(
                    raw_food_category
                )
            )
            displayed_activity_category = (
                admin_catalog_pages.format_activity_category_for_display("Forță")
            )

        self.assertEqual(raw_food_category, "Pește")
        self.assertEqual(displayed_food_category, "Fish")
        self.assertEqual(displayed_activity_category, "Strength")

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
