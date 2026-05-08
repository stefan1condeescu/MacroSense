import re
import unittest
from pathlib import Path


class FoodCatalogSeedTests(unittest.TestCase):
    def setUp(self):
        self.food_seed = Path("database/seeds/seed_food_items_usda_starter.sql").read_text(encoding="utf-8")

    def count_food_rows(self) -> int:
        return len(re.findall(r"^\s*\(", self.food_seed, flags=re.MULTILINE))

    def test_food_seed_has_dashboard_scale_catalog(self):
        self.assertGreaterEqual(self.count_food_rows(), 170)
        self.assertIn("USDA FoodData Central", self.food_seed)
        self.assertIn("ON CONFLICT ON CONSTRAINT uq_food_source_external DO NOTHING", self.food_seed)

    def test_food_seed_covers_macro_categories(self):
        expected_categories = [
            "Fructe",
            "Legume",
            "Carne",
            "Pește",
            "Ouă",
            "Lactate",
            "Cereale",
            "Pâine & Panificație",
            "Paste & Orez",
            "Leguminoase",
            "Nuci & Semințe",
            "Uleiuri & Grăsimi",
            "Mezeluri",
            "Dulciuri",
            "Gustări",
            "Băuturi & Sucuri",
            "Alcoolice",
            "Condimente & Sosuri",
        ]
        for category in expected_categories:
            self.assertIn(f"'{category}'", self.food_seed)

    def test_food_seed_does_not_contain_negative_nutrition_values(self):
        self.assertNotRegex(self.food_seed, r"^\s*-[0-9]+\.[0-9]+,", msg="Food seed contains negative nutrition values.")


class DemoUserSeedTests(unittest.TestCase):
    def setUp(self):
        self.demo_seed = Path("database/seeds/seed_demo_users.sql").read_text(encoding="utf-8")

    def count_inserts(self, table_name: str) -> int:
        return len(re.findall(rf"INSERT INTO {table_name}\b", self.demo_seed))

    def test_demo_seed_is_repeatable_and_documents_password(self):
        self.assertIn("DELETE FROM users WHERE email IN", self.demo_seed)
        self.assertIn("All demo accounts use password: test123", self.demo_seed)
        self.assertIn("BEGIN;", self.demo_seed)
        self.assertIn("COMMIT;", self.demo_seed)

    def test_demo_seed_creates_multiple_user_profiles(self):
        for email in [
            "demo.slabire@test.com",
            "demo.masa@test.com",
            "demo.mentinere@test.com",
            "demo.activ@test.com",
            "demo.rar@test.com",
        ]:
            self.assertIn(email, self.demo_seed)
        self.assertEqual(self.count_inserts("users"), 5)

    def test_demo_seed_has_enough_history_for_dashboard_and_ml(self):
        self.assertGreaterEqual(self.count_inserts("daily_logs"), 200)
        self.assertGreaterEqual(self.count_inserts("weight_logs"), 40)
        self.assertGreaterEqual(self.count_inserts("food_logs"), 500)
        self.assertGreaterEqual(self.count_inserts("activity_logs"), 100)

    def test_demo_seed_exercises_custom_meal_snapshots(self):
        self.assertIn("INSERT INTO custom_meals", self.demo_seed)
        self.assertIn("INSERT INTO recipe_ingredients", self.demo_seed)
        self.assertIn("snapshot_calories_100g", self.demo_seed)
        self.assertIn("Bol proteic demo", self.demo_seed)
        self.assertIn("Pui cu orez demo", self.demo_seed)


if __name__ == "__main__":
    unittest.main()
