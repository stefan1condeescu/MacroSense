import inspect
import unittest

from services.what_if import loaders, simulator
from services.what_if.simulator import (
    build_activity_entry,
    build_custom_meal_entry,
    build_food_entry,
    calculate_repeated_daily_weight_impact,
    calculate_totals,
    compare_totals,
    describe_balance_delta,
    scenario_matches_real_day,
)


class WhatIfSimulatorTests(unittest.TestCase):
    def test_food_entry_scales_macros_from_per_100g_values(self):
        entry = build_food_entry(
            entry_id="food-1",
            label="Orez",
            entry_type="Aliment",
            quantity_g=150,
            calories_100g=120,
            protein_100g=3,
            carbs_100g=25,
            fats_100g=1,
        )

        self.assertEqual(entry.calories, 180.0)
        self.assertEqual(entry.protein_g, 4.5)
        self.assertEqual(entry.carbs_g, 37.5)
        self.assertEqual(entry.fats_g, 1.5)

    def test_missing_names_remain_empty_for_ui_fallbacks(self):
        food_entry = build_food_entry(
            entry_id="food-1",
            label="",
            entry_type="",
            quantity_g=100,
            calories_100g=100,
            protein_100g=10,
            carbs_100g=10,
            fats_100g=1,
        )
        custom_meal_entry = build_custom_meal_entry(
            entry_id="meal-1",
            meal={
                "recipe_name": "",
                "quantity_g": 100,
                "calories": 100,
                "protein_g": 10,
                "carbs_g": 10,
                "fats_g": 1,
            },
            quantity_g=100,
        )
        activity_entry = build_activity_entry(
            entry_id="activity-1",
            label="",
            category="",
            duration_min=30,
            met=5,
            weight_kg=70,
        )

        self.assertEqual(
            (food_entry.label, food_entry.entry_type),
            ("", "Aliment"),
        )
        self.assertEqual(
            (
                custom_meal_entry.label,
                custom_meal_entry.entry_type,
                custom_meal_entry.source_label,
            ),
            ("", "Masă personalizată", "Custom meal"),
        )
        self.assertEqual(
            (activity_entry.label, activity_entry.category),
            ("", "Altele"),
        )

    def test_food_entry_rejects_quantity_outside_supported_range(self):
        with self.assertRaises(ValueError):
            build_food_entry(
                entry_id="food-1",
                label="Orez",
                entry_type="Aliment",
                quantity_g=5001,
                calories_100g=120,
                protein_100g=3,
                carbs_100g=25,
                fats_100g=1,
            )

    def test_activity_entry_uses_manual_calories_when_provided(self):
        entry = build_activity_entry(
            entry_id="activity-1",
            label="Alergare",
            category="Cardio",
            duration_min=30,
            met=10,
            weight_kg=80,
            manual_calories_burned=250,
        )

        self.assertEqual(entry.calories_burned, 250.0)

    def test_activity_entry_validates_sets_and_reps_together(self):
        with self.assertRaises(ValueError):
            build_activity_entry(
                entry_id="activity-1",
                label="Forță",
                category="Forță",
                duration_min=30,
                met=5,
                weight_kg=80,
                sets=3,
                reps=None,
            )

    def test_totals_and_comparison_keep_real_and_simulated_values_separate(self):
        real_food = [
            build_food_entry(
                entry_id="real-food",
                label="Iaurt",
                entry_type="Aliment",
                quantity_g=100,
                calories_100g=100,
                protein_100g=10,
                carbs_100g=8,
                fats_100g=2,
                is_existing=True,
            )
        ]
        simulated_food = [
            build_food_entry(
                entry_id="sim-food",
                label="Iaurt",
                entry_type="Aliment",
                quantity_g=200,
                calories_100g=100,
                protein_100g=10,
                carbs_100g=8,
                fats_100g=2,
            )
        ]

        comparison = compare_totals(
            calculate_totals(real_food, [], base_tdee=1600),
            calculate_totals(simulated_food, [], base_tdee=1600),
        )

        self.assertEqual(comparison.real.calories_in, 100.0)
        self.assertEqual(comparison.simulated.calories_in, 200.0)
        self.assertEqual(comparison.difference.calories_in, 100.0)
        self.assertEqual(comparison.real.estimated_balance, -1500.0)
        self.assertEqual(comparison.difference.estimated_balance, 100.0)

    def test_totals_use_estimated_tdee_for_balance(self):
        food_entries = [
            build_food_entry(
                entry_id="food-1",
                label="Meniu",
                entry_type="Aliment",
                quantity_g=100,
                calories_100g=2100,
                protein_100g=100,
                carbs_100g=200,
                fats_100g=50,
            )
        ]
        activity_entries = [
            build_activity_entry(
                entry_id="activity-1",
                label="Alergare",
                category="Cardio",
                duration_min=30,
                met=10,
                weight_kg=70,
            )
        ]

        totals = calculate_totals(food_entries, activity_entries, base_tdee=2166)

        self.assertEqual(totals.activity_calories, 350.0)
        self.assertEqual(totals.estimated_tdee, 2516.0)
        self.assertEqual(totals.estimated_balance, -416.0)

    def test_totals_leave_balance_missing_without_food_entries(self):
        activity_entries = [
            build_activity_entry(
                entry_id="activity-1",
                label="Alergare",
                category="Cardio",
                duration_min=30,
                met=10,
                weight_kg=70,
            )
        ]

        totals = calculate_totals([], activity_entries, base_tdee=2166)

        self.assertFalse(totals.has_food_entries)
        self.assertEqual(totals.calories_in, 0.0)
        self.assertEqual(totals.activity_calories, 350.0)
        self.assertEqual(totals.estimated_tdee, 2516.0)
        self.assertIsNone(totals.estimated_balance)

    def test_balance_difference_is_missing_when_one_side_has_no_food(self):
        simulated_food = [
            build_food_entry(
                entry_id="food-1",
                label="Meniu",
                entry_type="Aliment",
                quantity_g=100,
                calories_100g=2100,
                protein_100g=100,
                carbs_100g=200,
                fats_100g=50,
            )
        ]

        comparison = compare_totals(
            calculate_totals([], [], base_tdee=1800),
            calculate_totals(simulated_food, [], base_tdee=1800),
        )

        self.assertIsNone(comparison.real.estimated_balance)
        self.assertEqual(comparison.simulated.estimated_balance, 300.0)
        self.assertIsNone(comparison.difference.estimated_balance)
        self.assertEqual(
            describe_balance_delta(None),
            "The estimated balance cannot be compared because food data is missing "
            "from the real day or the scenario.",
        )

    def test_totals_round_after_summing_raw_food_values(self):
        food_entries = [
            build_food_entry(
                entry_id="food-1",
                label="Iaurt",
                entry_type="Aliment",
                quantity_g=100,
                calories_100g=10,
                protein_100g=1.045,
                carbs_100g=0,
                fats_100g=0,
            ),
            build_food_entry(
                entry_id="food-2",
                label="Lapte",
                entry_type="Aliment",
                quantity_g=100,
                calories_100g=10,
                protein_100g=1.045,
                carbs_100g=0,
                fats_100g=0,
            ),
        ]

        totals = calculate_totals(food_entries, [], base_tdee=1600)

        self.assertEqual(totals.protein_g, 2.09)

    def test_totals_round_after_summing_raw_activity_values(self):
        activity_entries = [
            build_activity_entry(
                entry_id="activity-1",
                label="Mers",
                category="Cardio",
                duration_min=60,
                met=1.00045,
                weight_kg=10,
            ),
            build_activity_entry(
                entry_id="activity-2",
                label="Mers",
                category="Cardio",
                duration_min=60,
                met=1.00045,
                weight_kg=10,
            ),
        ]

        totals = calculate_totals([], activity_entries, base_tdee=1600)

        self.assertEqual(totals.activity_calories, 20.01)
        self.assertEqual(totals.estimated_tdee, 1620.01)
        self.assertIsNone(totals.estimated_balance)

    def test_identical_scenario_is_detected_explicitly(self):
        food = [
            build_food_entry(
                entry_id="real-food",
                label="Iaurt",
                entry_type="Aliment",
                quantity_g=100,
                calories_100g=100,
                protein_100g=10,
                carbs_100g=8,
                fats_100g=2,
            )
        ]

        comparison = compare_totals(
            calculate_totals(food, [], base_tdee=1600),
            calculate_totals(food, [], base_tdee=1600),
        )

        self.assertTrue(scenario_matches_real_day(comparison))
        self.assertEqual(
            describe_balance_delta(comparison.difference.estimated_balance),
            "The estimated balance remains unchanged compared with the real values.",
        )

    def test_balance_description_covers_each_non_neutral_direction(self):
        self.assertEqual(
            describe_balance_delta(-100),
            "The scenario lowers the estimated balance and moves further toward a deficit.",
        )
        self.assertEqual(
            describe_balance_delta(100),
            "The scenario raises the estimated balance and moves further toward a surplus.",
        )
        self.assertEqual(
            describe_balance_delta(50),
            "The scenario changes the estimated balance only slightly compared with the real values.",
        )

    def test_repeated_daily_impact_uses_7700_kcal_reference(self):
        self.assertEqual(calculate_repeated_daily_weight_impact(-550, 14), -1.0)

    def test_simulator_layer_has_no_database_write_or_connection_code(self):
        source = inspect.getsource(simulator)

        self.assertNotIn("get_connection", source)
        self.assertNotIn(".save(", source)
        self.assertNotIn(".update(", source)
        self.assertNotIn(".delete(", source)

    def test_loader_layer_is_select_only(self):
        source = inspect.getsource(loaders).upper()

        self.assertIn("SELECT", source)
        self.assertNotIn("INSERT", source)
        self.assertNotIn("UPDATE", source)
        self.assertNotIn("DELETE", source)


if __name__ == "__main__":
    unittest.main()
