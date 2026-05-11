import datetime
import inspect
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from models.authentication import User
from models.tracking import Activity, ActivityLog, CustomMeal, DailyLog, FoodItem, FoodLog, RecipeIngredient, WeightLog
from models.tracking_models.daily_log import format_optional_activity_count


class FoodLogValidationTests(unittest.TestCase):
    def test_food_log_requires_positive_quantity(self):
        with self.assertRaises(ValueError):
            FoodLog(
                log_id=1,
                quantity_g=0,
                meal_type="Prânz",
                meal_time=datetime.time(12, 0),
                food_id=1,
            )

    def test_food_log_rejects_quantity_above_supported_range(self):
        with self.assertRaises(ValueError):
            FoodLog(
                log_id=1,
                quantity_g=5000.1,
                meal_type="PrÃ¢nz",
                meal_time=datetime.time(12, 0),
                food_id=1,
            )

        with self.assertRaises(ValueError):
            FoodLog.update(
                log_entry_id=1,
                user_id=1,
                quantity_g=5000.1,
                meal_type="PrÃ¢nz",
                meal_time=datetime.time(12, 0),
            )

    def test_food_log_requires_exactly_one_food_source(self):
        with self.assertRaises(ValueError):
            FoodLog(
                log_id=1,
                quantity_g=100,
                meal_type="Prânz",
                meal_time=datetime.time(12, 0),
            )

        with self.assertRaises(ValueError):
            FoodLog(
                log_id=1,
                quantity_g=100,
                meal_type="Prânz",
                meal_time=datetime.time(12, 0),
                food_id=1,
                custom_meal_id=1,
            )

    def test_food_log_requires_supported_meal_type(self):
        with self.assertRaises(ValueError):
            FoodLog(
                log_id=1,
                quantity_g=100,
                meal_type="Pranz",
                meal_time=datetime.time(12, 0),
                food_id=1,
            )

    def test_food_log_requires_valid_meal_time(self):
        with self.assertRaises(ValueError):
            FoodLog(
                log_id=1,
                quantity_g=100,
                meal_type="Prânz",
                meal_time=None,
                food_id=1,
            )

    def test_food_log_accepts_catalog_food_or_custom_meal(self):
        catalog_entry = FoodLog(
            log_id=1,
            quantity_g=100,
            meal_type="Prânz",
            meal_time=datetime.time(12, 0),
            food_id=1,
        )
        custom_entry = FoodLog(
            log_id=1,
            quantity_g=100,
            meal_type="Prânz",
            meal_time=datetime.time(12, 0),
            custom_meal_id=1,
        )

        self.assertEqual(catalog_entry.food_id, 1)
        self.assertIsNone(catalog_entry.custom_meal_id)
        self.assertEqual(custom_entry.custom_meal_id, 1)
        self.assertIsNone(custom_entry.food_id)

    def test_food_log_save_stores_snapshot_for_custom_meal(self):
        class FakeCursor:
            def __init__(self):
                self.calls = []

            def execute(self, query, params):
                self.calls.append((query, params))

            def fetchone(self):
                last_query = self.calls[-1][0]
                if "FROM custom_meals cm" in last_query:
                    return ("Masa test", 250, 500, 25, 50, 12.5)
                return (42,)

        class FakeConnection:
            def __init__(self):
                self.cursor_instance = FakeCursor()
                self.committed = False
                self.closed = False

            def cursor(self):
                return self.cursor_instance

            def commit(self):
                self.committed = True

            def rollback(self):
                pass

            def close(self):
                self.closed = True

        fake_conn = FakeConnection()
        food_log = FoodLog(
            log_id=7,
            quantity_g=125,
            meal_type=FoodLog.VALID_MEAL_TYPES[0],
            meal_time=datetime.time(12, 0),
            custom_meal_id=3,
        )

        with patch("models.tracking_models.food_log.get_connection", return_value=fake_conn):
            self.assertTrue(food_log.save())

        insert_query, insert_params = fake_conn.cursor_instance.calls[-1]
        self.assertIn("snapshot_calories_100g", insert_query)
        self.assertEqual(food_log.id, 42)
        self.assertEqual(insert_params[0:6], (7, None, 3, 125, FoodLog.VALID_MEAL_TYPES[0], datetime.time(12, 0)))
        self.assertEqual(insert_params[6:], ("Masa test", 200.0, 10.0, 20.0, 5.0))
        self.assertTrue(fake_conn.committed)
        self.assertTrue(fake_conn.closed)

    def test_food_log_save_keeps_snapshot_empty_for_catalog_food(self):
        class FakeCursor:
            def __init__(self):
                self.calls = []

            def execute(self, query, params):
                self.calls.append((query, params))

            def fetchone(self):
                return (43,)

        class FakeConnection:
            def __init__(self):
                self.cursor_instance = FakeCursor()

            def cursor(self):
                return self.cursor_instance

            def commit(self):
                pass

            def rollback(self):
                pass

            def close(self):
                pass

        fake_conn = FakeConnection()
        food_log = FoodLog(
            log_id=8,
            quantity_g=100,
            meal_type=FoodLog.VALID_MEAL_TYPES[0],
            meal_time=datetime.time(13, 0),
            food_id=5,
        )

        with patch("models.tracking_models.food_log.get_connection", return_value=fake_conn):
            self.assertTrue(food_log.save())

        self.assertEqual(len(fake_conn.cursor_instance.calls), 1)
        _, insert_params = fake_conn.cursor_instance.calls[0]
        self.assertEqual(insert_params[6:], (None, None, None, None, None))


class ActivityLogValidationTests(unittest.TestCase):
    def test_activity_log_requires_positive_duration(self):
        with self.assertRaises(ValueError):
            ActivityLog(log_id=1, activity_id=1, duration_min=0)

    def test_activity_log_accepts_subminute_duration(self):
        activity_log = ActivityLog(log_id=1, activity_id=1, duration_min=0.1)

        self.assertEqual(activity_log.duration_min, 0.1)

    def test_activity_log_rejects_duration_above_supported_range(self):
        with self.assertRaises(ValueError):
            ActivityLog(log_id=1, activity_id=1, duration_min=601)

    def test_activity_log_update_validates_sets_and_reps_together_before_db(self):
        with self.assertRaises(ValueError):
            ActivityLog.update(
                log_entry_id=1,
                user_id=1,
                activity_id=1,
                duration_min=30,
                sets=3,
                reps=None,
            )

        with self.assertRaises(ValueError):
            ActivityLog.update(
                log_entry_id=1,
                user_id=1,
                activity_id=1,
                duration_min=30,
                sets=0,
                reps=10,
            )

    def test_activity_log_constructor_validates_sets_and_reps_together(self):
        with self.assertRaises(ValueError):
            ActivityLog(log_id=1, activity_id=1, duration_min=30, sets=3, reps=None)

        with self.assertRaises(ValueError):
            ActivityLog(log_id=1, activity_id=1, duration_min=30, sets=0, reps=10)

        with self.assertRaises(ValueError):
            ActivityLog(log_id=1, activity_id=1, duration_min=30, sets=51, reps=10)

        with self.assertRaises(ValueError):
            ActivityLog(log_id=1, activity_id=1, duration_min=30, sets=3, reps=201)

    def test_activity_log_validates_optional_manual_calories(self):
        valid_log = ActivityLog(
            log_id=1,
            activity_id=1,
            duration_min=30,
            manual_calories_burned=250,
        )

        self.assertEqual(valid_log.manual_calories_burned, 250.0)

        with self.assertRaises(ValueError):
            ActivityLog(log_id=1, activity_id=1, duration_min=30, manual_calories_burned=0)

        with self.assertRaises(ValueError):
            ActivityLog.update(
                log_entry_id=1,
                user_id=1,
                activity_id=1,
                duration_min=30,
                manual_calories_burned=5000.1,
            )

    def test_activity_requires_name_category_and_positive_met(self):
        with self.assertRaises(ValueError):
            Activity(name="", met_multiplier=5.0, category="Cardio")

        with self.assertRaises(ValueError):
            Activity(name="Test", met_multiplier=0.8, category="Cardio")

        with self.assertRaises(ValueError):
            Activity(name="Test", met_multiplier=5.0, category="")

        with self.assertRaises(ValueError):
            Activity(name="A <span>Test</span>", met_multiplier=5.0, category="Cardio")

        with self.assertRaises(ValueError):
            Activity(name="///", met_multiplier=5.0, category="Cardio")

        with self.assertRaises(ValueError):
            Activity(
                name="Test",
                met_multiplier=5.0,
                category="Cardio",
                met_estimation_method="invented_method",
            )

    def test_activity_normalizes_name_and_met(self):
        activity = Activity(
            name="  Alergare  ",
            met_multiplier=8,
            category="Cardio",
            source=" Compendium ",
            external_id=" 12020 ",
            met_estimation_method="official_compendium",
        )

        self.assertEqual(activity.name, "Alergare")
        self.assertEqual(activity.met_multiplier, 8.0)
        self.assertEqual(activity.source, "Compendium")
        self.assertEqual(activity.external_id, "12020")
        self.assertEqual(activity.met_estimation_method, "official_compendium")

    def test_activity_name_normalization_is_diacritic_insensitive(self):
        self.assertEqual(
            Activity.normalize_name("  Înot   liber  "),
            Activity.normalize_name("inot liber"),
        )


class FoodItemValidationTests(unittest.TestCase):
    def test_food_item_requires_name_category_and_nutrition(self):
        invalid_examples = [
            {"name": "", "calories": 100, "protein": 1, "carbs": 2, "fats": 3, "category": "Altele"},
            {"name": "A <span>Test</span>", "calories": 100, "protein": 1, "carbs": 2, "fats": 3, "category": "Altele"},
            {"name": "///", "calories": 100, "protein": 1, "carbs": 2, "fats": 3, "category": "Altele"},
            {"name": "Test", "calories": 100, "protein": 1, "carbs": 2, "fats": 3, "category": ""},
            {"name": "Test", "calories": 0, "protein": 0, "carbs": 0, "fats": 0, "category": "Altele"},
            {"name": "Test", "calories": 0, "protein": 1, "carbs": 0, "fats": 0, "category": "Altele"},
            {"name": "Test", "calories": 100, "protein": 0, "carbs": 0, "fats": 0, "category": "Altele"},
            {"name": "Test", "calories": 100, "protein": -1, "carbs": 2, "fats": 3, "category": "Altele"},
        ]

        for example in invalid_examples:
            with self.subTest(example=example):
                with self.assertRaises(ValueError):
                    FoodItem(
                        example["name"],
                        example["calories"],
                        example["protein"],
                        example["carbs"],
                        example["fats"],
                        example["category"],
                    )

    def test_food_item_normalizes_valid_input(self):
        food = FoodItem("  Banane  ", 89, 1.1, 22.8, 0.3, "  Fructe  ")

        self.assertEqual(food.name, "Banane")
        self.assertEqual(food.category, "Fructe")
        self.assertEqual(food.calories_100g, 89.0)


class CustomMealValidationTests(unittest.TestCase):
    def test_custom_meal_name_must_start_with_letter(self):
        invalid_names = ["", "  ", "123 Salata", "-Salata", "A <span>Test</span>"]

        for recipe_name in invalid_names:
            with self.subTest(recipe_name=recipe_name):
                self.assertFalse(CustomMeal.is_valid_recipe_name(recipe_name))
                with self.assertRaises(ValueError):
                    CustomMeal(user_id=1, recipe_name=recipe_name)

    def test_custom_meal_accepts_letter_starting_name(self):
        meal = CustomMeal(user_id=1, recipe_name="Salata de fructe")

        self.assertEqual(meal.recipe_name, "Salata de fructe")
        self.assertEqual(meal.status, CustomMeal.ACTIVE_STATUS)

    def test_custom_meal_exposes_archive_statuses(self):
        self.assertNotEqual(CustomMeal.ACTIVE_STATUS, CustomMeal.ARCHIVED_STATUS)

    def test_custom_meal_update_does_not_touch_historical_food_logs(self):
        update_source = inspect.getsource(CustomMeal.update_with_ingredients)

        self.assertIn("UPDATE custom_meals", update_source)
        self.assertIn("DELETE FROM recipe_ingredients", update_source)
        self.assertNotIn("_backfill_missing_food_log_snapshots", update_source)
        self.assertFalse(hasattr(CustomMeal, "_backfill_missing_food_log_snapshots"))


class RecipeIngredientValidationTests(unittest.TestCase):
    def test_recipe_ingredient_requires_positive_quantity(self):
        with self.assertRaises(ValueError):
            RecipeIngredient(meal_id=1, food_id=1, quantity_g=0)

    def test_recipe_ingredient_rejects_quantity_above_supported_range(self):
        with self.assertRaises(ValueError):
            RecipeIngredient(meal_id=1, food_id=1, quantity_g=5000.1)

        with self.assertRaises(ValueError):
            RecipeIngredient.validate_quantity(5000.1)


class ActivityDisplayFormattingTests(unittest.TestCase):
    def test_optional_activity_count_avoids_float_suffix_for_integers(self):
        self.assertEqual(format_optional_activity_count(6.0), "6")
        self.assertEqual(format_optional_activity_count(15), "15")
        self.assertEqual(format_optional_activity_count(None), "-")


class WeightLogValidationTests(unittest.TestCase):
    def test_weight_log_requires_positive_weight(self):
        with self.assertRaises(ValueError):
            WeightLog(
                user_id=1,
                log_date=datetime.date(2026, 4, 29),
                weight_kg=0,
            )

    def test_weight_log_requires_weight_inside_supported_range(self):
        invalid_weights = [29.9, 300.1]

        for weight_kg in invalid_weights:
            with self.subTest(weight_kg=weight_kg):
                with self.assertRaises(ValueError):
                    WeightLog(
                        user_id=1,
                        log_date=datetime.date(2026, 4, 29),
                        weight_kg=weight_kg,
                    )

    def test_weight_log_requires_valid_date(self):
        with self.assertRaises(ValueError):
            WeightLog(
                user_id=1,
                log_date="2026-04-29",
                weight_kg=75.5,
            )

    def test_weight_log_requires_positive_user_id(self):
        with self.assertRaises(ValueError):
            WeightLog(
                user_id=0,
                log_date=datetime.date(2026, 4, 29),
                weight_kg=75.5,
            )

    def test_weight_log_accepts_valid_entry(self):
        weight_log = WeightLog(
            user_id=1,
            log_date=datetime.date(2026, 4, 29),
            weight_kg=75.5,
        )

        self.assertEqual(weight_log.user_id, 1)
        self.assertEqual(weight_log.weight_kg, 75.5)

    def test_weight_log_update_validates_before_db(self):
        with self.assertRaises(ValueError):
            WeightLog.update(
                log_entry_id=1,
                user_id=1,
                log_date=datetime.date(2026, 4, 29),
                weight_kg=0,
            )

        with self.assertRaises(ValueError):
            WeightLog.update(
                log_entry_id=1,
                user_id=1,
                log_date=datetime.date(2026, 4, 29),
                weight_kg=300.1,
            )

    def test_weight_log_detects_changed_activity_day_references(self):
        before_references = {
            10: (1, 80.0),
            11: (1, 80.0),
            12: (2, 82.0),
        }
        after_references = {
            10: (1, 80.0),
            11: (3, 81.0),
            12: (2, 82.0),
        }

        self.assertEqual(
            WeightLog.get_changed_reference_ids(before_references, after_references),
            {11}
        )


class UserRegistrationValidationTests(unittest.TestCase):
    def test_user_strips_email_and_full_name_without_changing_case(self):
        user = User(
            email="  TEST.USER@EXAMPLE.COM  ",
            full_name="  Test User  ",
            height_cm=180,
            age=30,
            gender="M",
            goal="Mentinere",
        )

        self.assertEqual(user.email, "TEST.USER@EXAMPLE.COM")
        self.assertEqual(user.full_name, "Test User")

    def test_user_register_rejects_initial_weight_outside_supported_range_before_db(self):
        user = User(
            email="invalid.weight@example.com",
            full_name="Invalid Weight",
            height_cm=180,
            age=24,
            gender="M",
            goal="Mentinere",
        )

        with redirect_stdout(io.StringIO()):
            self.assertFalse(user.register("test123", 29.9))
            self.assertEqual(user.last_error_code, "initial_weight_out_of_range")
            self.assertFalse(user.register("test123", 300.1))
            self.assertEqual(user.last_error_code, "initial_weight_out_of_range")

    def test_user_register_rejects_html_like_full_name_before_db(self):
        user = User(
            email="invalid.fullname@example.com",
            full_name="A <span>Test</span>",
            height_cm=180,
            age=24,
            gender="M",
            goal="Mentinere",
        )

        with redirect_stdout(io.StringIO()):
            self.assertFalse(user.register("test123", 75))
            self.assertEqual(user.last_error_code, "invalid_full_name")

    def test_user_register_rejects_special_only_full_name_before_db(self):
        user = User(
            email="invalid.special.fullname@example.com",
            full_name="///",
            height_cm=180,
            age=24,
            gender="M",
            goal="Mentinere",
        )

        with redirect_stdout(io.StringIO()):
            self.assertFalse(user.register("test123", 75))
            self.assertEqual(user.last_error_code, "invalid_full_name")

    def test_user_register_rejects_html_like_email_before_db(self):
        user = User(
            email="<user>@example.com",
            full_name="Invalid Email",
            height_cm=180,
            age=24,
            gender="M",
            goal="Mentinere",
        )

        with redirect_stdout(io.StringIO()):
            self.assertFalse(user.register("test123", 75))
            self.assertEqual(user.last_error_code, "invalid_email")

    def test_user_register_rejects_height_outside_supported_range_before_db(self):
        user = User(
            email="invalid.height@example.com",
            full_name="Invalid Height",
            height_cm=90,
            age=24,
            gender="M",
            goal="Mentinere",
        )

        with redirect_stdout(io.StringIO()):
            self.assertFalse(user.register("test123", 75))
            self.assertEqual(user.last_error_code, "invalid_height")

    def test_user_register_rejects_age_outside_supported_range_before_db(self):
        user = User(
            email="invalid.age@example.com",
            full_name="Invalid Age",
            height_cm=180,
            age=9,
            gender="M",
            goal="Mentinere",
        )

        with redirect_stdout(io.StringIO()):
            self.assertFalse(user.register("test123", 75))
            self.assertEqual(user.last_error_code, "invalid_age")

    def test_user_register_rejects_invalid_gender_before_db(self):
        user = User(
            email="invalid.gender@example.com",
            full_name="Invalid Gender",
            height_cm=180,
            age=24,
            gender="X",
            goal="Mentinere",
        )

        with redirect_stdout(io.StringIO()):
            self.assertFalse(user.register("test123", 75))
            self.assertEqual(user.last_error_code, "invalid_gender")

    def test_user_register_rejects_invalid_goal_before_db(self):
        user = User(
            email="invalid.goal@example.com",
            full_name="Invalid Goal",
            height_cm=180,
            age=24,
            gender="M",
            goal="Performanta",
        )

        with redirect_stdout(io.StringIO()):
            self.assertFalse(user.register("test123", 75))
            self.assertEqual(user.last_error_code, "invalid_goal")

    def test_user_registration_maps_database_errors_to_stable_codes(self):
        class FakeDiag:
            def __init__(self, constraint_name):
                self.constraint_name = constraint_name

        class FakeDatabaseError:
            def __init__(self, pgcode, constraint_name=None):
                self.pgcode = pgcode
                self.diag = FakeDiag(constraint_name)

        self.assertEqual(
            User._map_registration_error(FakeDatabaseError("23505")),
            "duplicate_email",
        )
        self.assertEqual(
            User._map_registration_error(FakeDatabaseError("23514", "chk_user_height")),
            "invalid_height",
        )
        self.assertEqual(
            User._map_registration_error(FakeDatabaseError("23514", "chk_user_full_name_chars")),
            "invalid_full_name",
        )
        self.assertEqual(
            User._map_registration_error(FakeDatabaseError("23514", "chk_user_full_name_has_letter")),
            "invalid_full_name",
        )
        self.assertEqual(
            User._map_registration_error(FakeDatabaseError("23514", "chk_user_goal")),
            "invalid_goal",
        )
        self.assertEqual(
            User._map_registration_error(FakeDatabaseError("23514", "chk_weight_range")),
            "initial_weight_out_of_range",
        )


class DailyLogCalculationTests(unittest.TestCase):
    def test_entry_fetchers_accept_user_scope(self):
        self.assertIn("user_id", inspect.signature(DailyLog.get_food_entries).parameters)
        self.assertIn("user_id", inspect.signature(DailyLog.get_activity_entries).parameters)

    def test_daily_log_uses_custom_meal_snapshot_when_available(self):
        recalculate_source = inspect.getsource(DailyLog.recalculate_totals)
        entries_source = inspect.getsource(DailyLog.get_food_entries)

        self.assertIn("fl.snapshot_calories_100g * fl.quantity_g / 100.0", recalculate_source)
        self.assertNotIn("meal_totals", recalculate_source)
        self.assertIn('fl.snapshot_name AS "Aliment / Masă"', entries_source)
        self.assertIn("fl.snapshot_calories_100g * fl.quantity_g / 100.0", entries_source)
        self.assertNotIn("COALESCE(fl.snapshot_name, cm.recipe_name)", entries_source)

    def test_energy_balance_is_calories_in_minus_burned(self):
        daily_log = DailyLog(
            user_id=1,
            log_date=datetime.date(2026, 4, 28),
            total_calories_in=2000,
            total_calories_burned=450,
        )

        self.assertEqual(daily_log.calculate_energy_balance(), 1550)

    def test_hybrid_calories_uses_met_for_cardio(self):
        burned = DailyLog.calculate_hybrid_calories(
            category="Cardio",
            met=8.0,
            weight=70.0,
            duration_min=30,
            sets=0,
            reps=0,
        )

        self.assertEqual(burned, 280.0)

    def test_hybrid_calories_uses_tut_for_strength(self):
        burned = DailyLog.calculate_hybrid_calories(
            category="Forță",
            met=5.0,
            weight=70.0,
            duration_min=30,
            sets=3,
            reps=10,
        )

        self.assertEqual(burned, 58.62)


if __name__ == "__main__":
    unittest.main()
