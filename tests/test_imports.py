import importlib
import unittest


class ArchitectureImportTests(unittest.TestCase):
    def test_tracking_facade_exports_documented_classes(self):
        tracking = importlib.import_module("models.tracking")

        for class_name in [
            "Activity",
            "ActivityLog",
            "CustomMeal",
            "DailyLog",
            "FoodItem",
            "FoodLog",
            "RecipeIngredient",
            "WeightLog",
        ]:
            with self.subTest(class_name=class_name):
                self.assertTrue(hasattr(tracking, class_name))

    def test_tracking_modules_are_importable(self):
        module_names = [
            "models.text_validation",
            "models.tracking_models.activity",
            "models.tracking_models.activity_log",
            "models.tracking_models.custom_meal",
            "models.tracking_models.daily_log",
            "models.tracking_models.food_item",
            "models.tracking_models.food_log",
            "models.tracking_models.recipe_ingredient",
            "models.tracking_models.weight_log",
        ]

        for module_name in module_names:
            with self.subTest(module_name=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_ui_modules_are_importable(self):
        module_names = [
            "ui.config",
            "ui.activity_selection",
            "ui.activity_validation",
            "ui.food_selection",
            "ui.formatters",
            "ui.quantity_validation",
            "ui.tables",
            "ui.pages.activity_journal_page",
            "ui.pages.admin_catalog_pages",
            "ui.pages.admin_routes",
            "ui.pages.auth_page",
            "ui.pages.custom_meals_page",
            "ui.pages.dashboard_page",
            "ui.pages.food_journal_page",
            "ui.pages.user_catalog_pages",
            "ui.pages.user_routes",
            "ui.pages.weight_journal_page",
            "services.ml",
            "services.ml.artifacts",
            "services.ml.evaluate_models",
            "services.ml.evaluation",
            "services.ml.feature_engineering",
            "services.ml.prediction",
            "services.ml.predict_user",
            "services.ml.smoke_check",
            "services.ml.synthetic_data",
            "services.ml.train_models",
            "services.ml.training",
            "services.usda_food_data",
        ]

        for module_name in module_names:
            with self.subTest(module_name=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))


if __name__ == "__main__":
    unittest.main()
