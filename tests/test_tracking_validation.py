import datetime
import unittest

from models.tracking import ActivityLog, CustomMeal, DailyLog, FoodLog, RecipeIngredient


class FoodLogValidationTests(unittest.TestCase):
    def test_food_log_requires_positive_quantity(self):
        with self.assertRaises(ValueError):
            FoodLog(
                log_id=1,
                quantity_g=0,
                meal_type="Pranz",
                meal_time=datetime.time(12, 0),
                food_id=1,
            )

    def test_food_log_requires_exactly_one_food_source(self):
        with self.assertRaises(ValueError):
            FoodLog(
                log_id=1,
                quantity_g=100,
                meal_type="Pranz",
                meal_time=datetime.time(12, 0),
            )

        with self.assertRaises(ValueError):
            FoodLog(
                log_id=1,
                quantity_g=100,
                meal_type="Pranz",
                meal_time=datetime.time(12, 0),
                food_id=1,
                custom_meal_id=1,
            )

    def test_food_log_accepts_catalog_food_or_custom_meal(self):
        catalog_entry = FoodLog(
            log_id=1,
            quantity_g=100,
            meal_type="Pranz",
            meal_time=datetime.time(12, 0),
            food_id=1,
        )
        custom_entry = FoodLog(
            log_id=1,
            quantity_g=100,
            meal_type="Pranz",
            meal_time=datetime.time(12, 0),
            custom_meal_id=1,
        )

        self.assertEqual(catalog_entry.food_id, 1)
        self.assertIsNone(catalog_entry.custom_meal_id)
        self.assertEqual(custom_entry.custom_meal_id, 1)
        self.assertIsNone(custom_entry.food_id)


class ActivityLogValidationTests(unittest.TestCase):
    def test_activity_log_requires_positive_duration(self):
        with self.assertRaises(ValueError):
            ActivityLog(log_id=1, activity_id=1, duration_min=0)

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


class CustomMealValidationTests(unittest.TestCase):
    def test_custom_meal_name_must_start_with_letter(self):
        invalid_names = ["", "  ", "123 Salata", "-Salata"]

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


class RecipeIngredientValidationTests(unittest.TestCase):
    def test_recipe_ingredient_requires_positive_quantity(self):
        with self.assertRaises(ValueError):
            RecipeIngredient(meal_id=1, food_id=1, quantity_g=0)


class DailyLogCalculationTests(unittest.TestCase):
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
