import re
import unittest
from pathlib import Path

from models.profile_constants import USER_GOALS
from ui.catalog_constants import ACTIVITY_CATEGORIES, FOOD_CATEGORIES


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
        expected_categories = [category for category in FOOD_CATEGORIES if category != "Altele"]
        for category in expected_categories:
            self.assertIn(f"'{category}'", self.food_seed)

    def test_food_seed_categories_match_ui_categories(self):
        seed_categories = set(re.findall(r",\s*'([^']+)'\s*,\s*'USDA'", self.food_seed))
        self.assertTrue(seed_categories)
        self.assertTrue(seed_categories.issubset(set(FOOD_CATEGORIES)))

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

    def test_demo_seed_uses_supported_user_goals(self):
        user_rows = re.findall(r"INSERT INTO users .*? VALUES \((.*?)\);", self.demo_seed)
        seed_goals = {
            row.rsplit(",", 1)[-1].strip().strip("'")
            for row in user_rows
        }
        self.assertTrue(seed_goals)
        self.assertTrue(seed_goals.issubset(set(USER_GOALS)))

    def test_demo_seed_has_enough_history_for_dashboard_and_ml(self):
        self.assertGreaterEqual(self.count_inserts("daily_logs"), 200)
        self.assertGreaterEqual(self.count_inserts("weight_logs"), 40)
        self.assertGreaterEqual(self.count_inserts("food_logs"), 500)
        self.assertGreaterEqual(self.count_inserts("activity_logs"), 100)

    def test_demo_seed_extends_tracking_to_current_demo_date(self):
        date_literals = re.findall(r"DATE '([0-9]{4}-[0-9]{2}-[0-9]{2})'", self.demo_seed)

        self.assertIn("generate_series(DATE '2026-05-08', DATE '2026-05-23'", self.demo_seed)
        self.assertIn("DATE '2026-05-23'", self.demo_seed)
        self.assertLessEqual(max(date_literals), "2026-05-23")

    def test_demo_seed_profiles_cover_minimum_90_day_window(self):
        user_rows = re.findall(
            r"INSERT INTO users .*? VALUES \('([^']+)', .*?, DATE '([0-9]{4}-[0-9]{2}-[0-9]{2})'",
            self.demo_seed,
        )
        registration_dates = {email: registration_date for email, registration_date in user_rows}

        for email in [
            "demo.slabire@test.com",
            "demo.masa@test.com",
            "demo.mentinere@test.com",
            "demo.activ@test.com",
            "demo.rar@test.com",
        ]:
            with self.subTest(email=email):
                self.assertLessEqual(registration_dates[email], "2026-02-23")

    def test_demo_seed_backfills_missing_90_day_history_from_templates(self):
        self.assertIn("Demo minimum 90-day backfill", self.demo_seed)
        self.assertIn("generate_series(cfg.history_start, cfg.history_end", self.demo_seed)
        self.assertIn("ON CONFLICT ON CONSTRAINT uq_daily_log DO NOTHING", self.demo_seed)
        self.assertIn("inserted_days AS", self.demo_seed)
        self.assertIn("JOIN food_logs source_food ON source_food.log_id = template.source_log_id", self.demo_seed)
        self.assertIn("source_food.quantity_g * (1.0 +", self.demo_seed)
        self.assertIn("backfill_weights", self.demo_seed)

    def test_demo_seed_recalculates_daily_totals_after_backfill(self):
        self.assertIn("Final demo total recalculation", self.demo_seed)
        self.assertIn("SET total_calories_in = food_totals.total_calories_in", self.demo_seed)
        self.assertIn("LEFT JOIN food_logs fl ON fl.log_id = ddl.log_id", self.demo_seed)
        self.assertIn("SET total_calories_burned = activity_totals.total_calories_burned", self.demo_seed)
        self.assertIn("LEFT JOIN activity_logs al ON al.log_id = ddl.log_id", self.demo_seed)
        self.assertIn("LEFT JOIN LATERAL", self.demo_seed)
        self.assertIn("WHEN al.manual_calories_burned IS NOT NULL", self.demo_seed)
        self.assertIn("WHEN a.category = 'Forță'", self.demo_seed)

    def test_demo_seed_recalculates_activity_totals_after_weight_backfill(self):
        self.assertLess(
            self.demo_seed.index("backfill_weights"),
            self.demo_seed.index("Final demo total recalculation"),
        )
        self.assertIn("COALESCE(past_weight.weight_kg, future_weight.weight_kg, 70.0)", self.demo_seed)

    def test_demo_seed_recent_weights_follow_profile_goals(self):
        recent_weight_rows = re.findall(
            r"\('([^']+)', DATE '(2026-05-(?:12|18|23))', ([0-9]+\.[0-9]+)\)",
            self.demo_seed,
        )
        weights = {
            (email, log_date): float(weight)
            for email, log_date, weight in recent_weight_rows
        }

        self.assertGreater(
            weights[("demo.slabire@test.com", "2026-05-12")],
            weights[("demo.slabire@test.com", "2026-05-18")],
        )
        self.assertGreater(
            weights[("demo.slabire@test.com", "2026-05-18")],
            weights[("demo.slabire@test.com", "2026-05-23")],
        )
        self.assertLess(
            weights[("demo.masa@test.com", "2026-05-12")],
            weights[("demo.masa@test.com", "2026-05-18")],
        )
        self.assertLess(
            weights[("demo.masa@test.com", "2026-05-18")],
            weights[("demo.masa@test.com", "2026-05-23")],
        )
        self.assertLess(
            abs(weights[("demo.mentinere@test.com", "2026-05-23")] - weights[("demo.mentinere@test.com", "2026-05-12")]),
            0.10,
        )
        self.assertLess(
            abs(weights[("demo.activ@test.com", "2026-05-23")] - weights[("demo.activ@test.com", "2026-05-12")]),
            0.15,
        )
        self.assertGreater(
            weights[("demo.rar@test.com", "2026-05-12")],
            weights[("demo.rar@test.com", "2026-05-18")],
        )
        self.assertGreater(
            weights[("demo.rar@test.com", "2026-05-18")],
            weights[("demo.rar@test.com", "2026-05-23")],
        )

    def test_demo_seed_calibrates_recent_food_totals_for_ml_predictions(self):
        self.assertIn("Demo calibration for recent dashboard and ML predictions", self.demo_seed)
        self.assertIn("quantity_multiplier", self.demo_seed)
        self.assertIn("DATE '2026-04-19', DATE '2026-05-23'", self.demo_seed)
        self.assertIn(
            "('demo.masa@test.com', DATE '2026-04-19', DATE '2026-05-23', 1.24)",
            self.demo_seed,
        )

    def test_demo_seed_extends_recent_foods_from_historical_templates(self):
        self.assertIn("template_days AS", self.demo_seed)
        self.assertIn("JOIN food_logs source_food ON source_food.log_id = template.source_log_id", self.demo_seed)
        self.assertIn("source_food.snapshot_calories_100g", self.demo_seed)
        self.assertNotIn("daily_step_g", self.demo_seed)

    def test_demo_seed_extends_recent_activities_from_historical_templates(self):
        self.assertIn(
            "JOIN activity_logs source_activity ON source_activity.log_id = template.source_log_id",
            self.demo_seed,
        )
        self.assertIn("JOIN daily_logs source_day ON source_day.id = template.source_log_id", self.demo_seed)
        self.assertIn("source_day.total_calories_burned", self.demo_seed)
        self.assertIn("source_activity.sets", self.demo_seed)
        self.assertNotIn("extension_activities(email, external_id", self.demo_seed)

    def test_demo_seed_exercises_custom_meal_snapshots(self):
        self.assertIn("INSERT INTO custom_meals", self.demo_seed)
        self.assertIn("INSERT INTO recipe_ingredients", self.demo_seed)
        self.assertIn("snapshot_calories_100g", self.demo_seed)
        self.assertIn("Bol proteic demo", self.demo_seed)
        self.assertIn("Pui cu orez demo", self.demo_seed)


class ActivityCatalogSeedTests(unittest.TestCase):
    def setUp(self):
        self.activity_seeds = "\n".join([
            Path("database/seeds/seed_activities_compendium_official.sql").read_text(encoding="utf-8"),
            Path("database/seeds/seed_activities_macrosense_mappings.sql").read_text(encoding="utf-8"),
        ])

    def test_activity_seed_categories_match_ui_categories(self):
        seed_categories = set(
            re.findall(r",\s*'([^']+)'\s*,\s*'(?:Compendium|MacroSense)'", self.activity_seeds)
        )
        self.assertTrue(seed_categories)
        self.assertTrue(seed_categories.issubset(set(ACTIVITY_CATEGORIES)))


if __name__ == "__main__":
    unittest.main()
