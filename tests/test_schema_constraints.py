import unittest
from pathlib import Path


class SchemaConstraintTests(unittest.TestCase):
    def setUp(self):
        self.schema_sql = Path("schema.sql").read_text(encoding="utf-8")

    def test_activity_log_sets_reps_constraint_rejects_half_filled_pairs(self):
        self.assertIn("sets IS NULL AND reps IS NULL", self.schema_sql)
        self.assertIn("sets IS NOT NULL", self.schema_sql)
        self.assertIn("reps IS NOT NULL", self.schema_sql)
        self.assertIn("sets BETWEEN 1 AND 50", self.schema_sql)
        self.assertIn("reps BETWEEN 1 AND 200", self.schema_sql)
        self.assertIn("manual_calories_burned DECIMAL(8,2)", self.schema_sql)
        self.assertIn("chk_activity_log_manual_calories", self.schema_sql)
        self.assertIn("chk_activity_log_duration_range", self.schema_sql)
        self.assertIn("duration_min DECIMAL(6,2) NOT NULL", self.schema_sql)
        self.assertIn("duration_min BETWEEN 0.1 AND 600", self.schema_sql)

    def test_food_items_require_non_empty_category(self):
        self.assertIn("category VARCHAR(50) NOT NULL", self.schema_sql)
        self.assertIn("chk_food_category_not_empty", self.schema_sql)
        self.assertIn("chk_food_name_no_html", self.schema_sql)
        self.assertIn("chk_food_name_has_letter", self.schema_sql)
        self.assertIn("chk_food_calories_positive", self.schema_sql)
        self.assertIn("chk_food_has_macro", self.schema_sql)

    def test_users_reject_html_like_persisted_text_at_schema_level(self):
        self.assertIn("chk_user_email_no_html", self.schema_sql)
        self.assertIn("chk_user_full_name_no_html", self.schema_sql)
        self.assertIn("chk_user_full_name_chars", self.schema_sql)
        self.assertIn("chk_user_full_name_has_letter", self.schema_sql)
        self.assertIn("chk_user_goal", self.schema_sql)
        self.assertIn("goal IN ('Slabire', 'Mentinere', 'Crestere')", self.schema_sql)

    def test_activities_reject_html_like_names_at_schema_level(self):
        self.assertIn("chk_activity_name_no_html", self.schema_sql)
        self.assertIn("chk_activity_name_has_letter", self.schema_sql)
        self.assertIn("source_type VARCHAR(100)", self.schema_sql)
        self.assertIn("met_estimation_method VARCHAR(50)", self.schema_sql)
        self.assertIn("uq_activity_source_external", self.schema_sql)
        self.assertIn("chk_activity_met_estimation_method", self.schema_sql)

    def test_custom_meals_reject_html_like_names_at_schema_level(self):
        self.assertIn("chk_custom_meal_name_no_html", self.schema_sql)
        self.assertIn("chk_custom_meal_name_starts_letter", self.schema_sql)

    def test_food_logs_require_meal_type_and_time(self):
        self.assertIn("meal_type VARCHAR(50) NOT NULL", self.schema_sql)
        self.assertIn("meal_time TIME NOT NULL", self.schema_sql)
        self.assertNotIn("meal_type IS NULL OR", self.schema_sql)

    def test_food_logs_support_custom_meal_snapshots(self):
        self.assertIn("snapshot_name VARCHAR(100)", self.schema_sql)
        self.assertIn("snapshot_calories_100g DECIMAL(8,2)", self.schema_sql)
        self.assertIn("snapshot_protein_100g DECIMAL(8,2)", self.schema_sql)
        self.assertIn("snapshot_carbs_100g DECIMAL(8,2)", self.schema_sql)
        self.assertIn("snapshot_fats_100g DECIMAL(8,2)", self.schema_sql)
        self.assertIn("chk_food_log_snapshot_complete", self.schema_sql)
        self.assertIn("chk_food_log_catalog_snapshot_null", self.schema_sql)
        self.assertIn("chk_food_log_custom_meal_snapshot_required", self.schema_sql)
        self.assertIn("custom_meal_id IS NULL OR", self.schema_sql)
        self.assertIn("chk_food_log_snapshot_nutrition", self.schema_sql)

    def test_food_and_recipe_quantities_have_supported_range(self):
        self.assertIn("chk_food_log_quantity_range", self.schema_sql)
        self.assertIn("chk_recipe_ingredient_quantity_range", self.schema_sql)
        self.assertIn("quantity_g BETWEEN 1 AND 5000", self.schema_sql)

    def test_journal_tables_block_future_dates_with_triggers(self):
        self.assertIn("CREATE OR REPLACE FUNCTION prevent_future_log_date()", self.schema_sql)
        self.assertIn("NEW.log_date > CURRENT_DATE", self.schema_sql)
        self.assertIn("trg_weight_logs_no_future_date", self.schema_sql)
        self.assertIn("BEFORE INSERT OR UPDATE OF log_date ON weight_logs", self.schema_sql)
        self.assertIn("trg_daily_logs_no_future_date", self.schema_sql)
        self.assertIn("BEFORE INSERT OR UPDATE OF log_date ON daily_logs", self.schema_sql)


if __name__ == "__main__":
    unittest.main()
