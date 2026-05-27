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

    def values_block(self, table_name: str) -> str:
        match = re.search(
            rf"INSERT INTO {table_name} .*? VALUES\s*(.*?);",
            self.demo_seed,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, f"{table_name} VALUES block was not found.")
        return match.group(1)

    def profile_rows(self):
        rows = re.findall(
            r"\('([^']+)', '([^']+)', DATE '([0-9]{4}-[0-9]{2}-[0-9]{2})', "
            r"([0-9.]+), ([0-9]+), '([MF])', '([^']+)', "
            r"DATE '([0-9]{4}-[0-9]{2}-[0-9]{2})', DATE '([0-9]{4}-[0-9]{2}-[0-9]{2})', "
            r"([0-9.]+), ([0-9.]+), ([0-9.]+), ([0-9]+)\)",
            self.values_block("demo_profiles"),
        )
        return {
            row[0]: {
                "full_name": row[1],
                "registration_date": row[2],
                "height_cm": float(row[3]),
                "age": int(row[4]),
                "gender": row[5],
                "goal": row[6],
                "start_date": row[7],
                "end_date": row[8],
                "start_weight": float(row[9]),
                "end_weight": float(row[10]),
                "food_scale": float(row[11]),
                "food_pattern_count": int(row[12]),
            }
            for row in rows
        }

    def test_demo_seed_is_repeatable_and_documents_password(self):
        self.assertIn("DELETE FROM users WHERE email IN", self.demo_seed)
        self.assertIn("All demo accounts use password: test123", self.demo_seed)
        self.assertIn("deterministic", self.demo_seed)
        self.assertIn("BEGIN;", self.demo_seed)
        self.assertIn("COMMIT;", self.demo_seed)
        self.assertNotIn("random()", self.demo_seed.lower())

    def test_demo_seed_creates_multiple_user_profiles(self):
        profiles = self.profile_rows()
        for email in [
            "demo.slabire@test.com",
            "demo.masa@test.com",
            "demo.mentinere@test.com",
            "demo.activ@test.com",
            "demo.rar@test.com",
        ]:
            self.assertIn(email, profiles)
        self.assertEqual(len(profiles), 5)
        self.assertEqual(self.count_inserts("users"), 1)

    def test_demo_seed_uses_supported_user_goals(self):
        seed_goals = {profile["goal"] for profile in self.profile_rows().values()}
        self.assertTrue(seed_goals)
        self.assertTrue(seed_goals.issubset(set(USER_GOALS)))

    def test_demo_seed_generates_history_for_dashboard_and_ml(self):
        self.assertIn("CREATE TEMP TABLE demo_days", self.demo_seed)
        self.assertIn("generate_series(p.start_date, p.end_date", self.demo_seed)
        self.assertIn("INSERT INTO daily_logs", self.demo_seed)
        self.assertIn("INSERT INTO weight_logs", self.demo_seed)
        self.assertIn("INSERT INTO food_logs", self.demo_seed)
        self.assertIn("INSERT INTO activity_logs", self.demo_seed)
        self.assertIn("CREATE TEMP TABLE demo_food_patterns", self.demo_seed)
        self.assertIn("CREATE TEMP TABLE demo_activity_schedule", self.demo_seed)

        food_pattern_rows = re.findall(r"\('demo\.[^']+@test\.com', [0-9], [0-9]+,", self.values_block("demo_food_patterns"))
        activity_schedule_rows = re.findall(r"\('demo\.[^']+@test\.com', [1-7], [0-9]+,", self.values_block("demo_activity_schedule"))
        self.assertGreaterEqual(len(food_pattern_rows), 120)
        self.assertGreaterEqual(len(activity_schedule_rows), 18)

    def test_demo_seed_extends_tracking_to_current_demo_date(self):
        date_literals = re.findall(r"DATE '([0-9]{4}-[0-9]{2}-[0-9]{2})'", self.demo_seed)

        self.assertIn("DATE '2026-05-27'", self.demo_seed)
        self.assertLessEqual(max(date_literals), "2026-05-27")
        for profile in self.profile_rows().values():
            self.assertEqual(profile["end_date"], "2026-05-27")

    def test_demo_seed_profiles_cover_minimum_90_day_window(self):
        profiles = self.profile_rows()

        for email in [
            "demo.slabire@test.com",
            "demo.masa@test.com",
            "demo.mentinere@test.com",
            "demo.activ@test.com",
            "demo.rar@test.com",
        ]:
            with self.subTest(email=email):
                self.assertLessEqual(profiles[email]["registration_date"], "2026-02-23")
                self.assertLessEqual(profiles[email]["start_date"], "2026-02-23")

    def test_demo_seed_uses_one_uniform_generation_flow(self):
        self.assertIn("CREATE TEMP TABLE demo_profiles", self.demo_seed)
        self.assertIn("CREATE TEMP TABLE demo_days", self.demo_seed)
        self.assertIn("CREATE TEMP TABLE demo_food_patterns", self.demo_seed)
        self.assertIn("CREATE TEMP TABLE demo_activity_schedule", self.demo_seed)
        self.assertIn("ON CONFLICT ON CONSTRAINT uq_daily_log DO NOTHING", self.demo_seed)
        self.assertNotIn("Demo minimum 90-day backfill", self.demo_seed)
        self.assertNotIn("Demo calibration for recent dashboard and ML predictions", self.demo_seed)
        self.assertNotIn("template_days AS", self.demo_seed)
        self.assertNotIn("source_food.quantity_g", self.demo_seed)

    def test_demo_seed_recalculates_daily_totals_after_generated_rows(self):
        self.assertIn("Final total recalculation", self.demo_seed)
        self.assertIn("SET total_calories_in = food_totals.total_calories_in", self.demo_seed)
        self.assertIn("LEFT JOIN food_logs fl ON fl.log_id = ddl.log_id", self.demo_seed)
        self.assertIn("SET total_calories_burned = activity_totals.total_calories_burned", self.demo_seed)
        self.assertIn("LEFT JOIN activity_logs al ON al.log_id = ddl.log_id", self.demo_seed)
        self.assertIn("LEFT JOIN LATERAL", self.demo_seed)
        self.assertIn("WHEN al.manual_calories_burned IS NOT NULL", self.demo_seed)
        self.assertIn("WHEN a.category = 'Forță'", self.demo_seed)

    def test_demo_seed_recalculates_activity_totals_after_weight_generation(self):
        self.assertLess(
            self.demo_seed.index("INSERT INTO weight_logs"),
            self.demo_seed.index("Final total recalculation"),
        )
        self.assertIn("COALESCE(past_weight.weight_kg, future_weight.weight_kg, 70.0)", self.demo_seed)

    def test_demo_seed_weight_trends_follow_profile_goals(self):
        profiles = self.profile_rows()
        self.assertGreater(
            profiles["demo.slabire@test.com"]["start_weight"],
            profiles["demo.slabire@test.com"]["end_weight"],
        )
        self.assertLess(
            profiles["demo.masa@test.com"]["start_weight"],
            profiles["demo.masa@test.com"]["end_weight"],
        )
        self.assertLess(
            abs(profiles["demo.mentinere@test.com"]["end_weight"] - profiles["demo.mentinere@test.com"]["start_weight"]),
            1.00,
        )
        self.assertLess(
            abs(profiles["demo.activ@test.com"]["end_weight"] - profiles["demo.activ@test.com"]["start_weight"]),
            1.00,
        )
        self.assertGreater(
            profiles["demo.rar@test.com"]["start_weight"],
            profiles["demo.rar@test.com"]["end_weight"],
        )

    def test_demo_seed_varies_food_quantities_without_randomness(self):
        self.assertIn("food_scale", self.demo_seed)
        self.assertIn("fp.base_quantity_g", self.demo_seed)
        self.assertIn("MOD(d.day_index + fp.meal_sequence, 5)", self.demo_seed)
        self.assertNotIn("quantity_multiplier", self.demo_seed)

    def test_demo_seed_generates_food_logs_from_realistic_patterns(self):
        self.assertIn("demo_food_patterns", self.demo_seed)
        self.assertIn("'Mic dejun'", self.demo_seed)
        self.assertIn("'Prânz'", self.demo_seed)
        self.assertIn("'Cină'", self.demo_seed)
        self.assertIn("'Gustare'", self.demo_seed)
        self.assertIn("snapshot_calories_100g", self.demo_seed)

    def test_demo_seed_generates_activity_logs_from_schedules(self):
        self.assertIn("demo_activity_schedule", self.demo_seed)
        self.assertIn("base_manual_calories", self.demo_seed)
        self.assertIn("s.sets", self.demo_seed)
        self.assertIn("s.reps", self.demo_seed)
        self.assertIn("EXTRACT(ISODOW FROM d.log_date)", self.demo_seed)

    def test_demo_seed_food_references_exist_in_catalog_seed(self):
        food_seed = Path("database/seeds/seed_food_items_usda_starter.sql").read_text(encoding="utf-8")
        catalog_food_ids = set(re.findall(r"'([0-9]{5,})'", food_seed))
        used_food_ids = set(re.findall(r"'([0-9]{5,})'", self.values_block("demo_recipe_ingredients")))
        used_food_ids.update(re.findall(r"'([0-9]{5,})'", self.values_block("demo_food_patterns")))

        self.assertTrue(used_food_ids)
        self.assertTrue(used_food_ids.issubset(catalog_food_ids))

    def test_demo_seed_activity_references_exist_in_activity_seeds(self):
        activity_seeds = "\n".join([
            Path("database/seeds/seed_activities_compendium_official.sql").read_text(encoding="utf-8"),
            Path("database/seeds/seed_activities_macrosense_mappings.sql").read_text(encoding="utf-8"),
        ])
        catalog_activity_pairs = set()
        for row in re.findall(r"\(([^\n]+)\)", activity_seeds):
            columns = re.findall(r"'([^']*)'", row)
            if len(columns) >= 5:
                catalog_activity_pairs.add((columns[2], columns[4]))

        used_activity_pairs = set(
            re.findall(
                r"'((?:Compendium|MacroSense))', '([^']+)'",
                self.values_block("demo_activity_schedule"),
            )
        )

        self.assertTrue(used_activity_pairs)
        self.assertTrue(used_activity_pairs.issubset(catalog_activity_pairs))

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
