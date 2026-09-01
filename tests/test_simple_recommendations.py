import ast
import inspect
import unittest

from services.recommendations import simple_recommendations
from services.recommendations.simple_recommendations import (
    RecommendationContext,
    build_recommendation_cards,
)
from ui.translations_ro import ROMANIAN_TRANSLATIONS


def _base_context(**overrides):
    values = {
        "goal": "Slabire",
        "days": 14,
        "food_days": 14,
        "activity_days": 4,
        "weight_days": 3,
        "workouts_count": 4,
        "avg_estimated_balance": -350.0,
        "avg_protein_per_kg": 1.6,
        "avg_activity_calories_per_active_day": 250.0,
        "activity_total_calories": 1000.0,
        "current_weight_kg": 80.0,
        "current_bmi": 26.0,
        "interval_weight_delta_kg": -0.8,
        "predicted_change_kg": None,
        "predicted_horizon_days": None,
    }
    values.update(overrides)
    return RecommendationContext(**values)


def _card(cards, category):
    for card in cards:
        if card.category == category:
            return card
    raise AssertionError(f"Missing recommendation category: {category}")


class SimpleRecommendationTests(unittest.TestCase):
    def test_every_recommendation_source_text_has_a_romanian_translation(self):
        source_tree = ast.parse(inspect.getsource(simple_recommendations))
        card_calls = [
            node
            for node in ast.walk(source_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "RecommendationCard"
        ]

        self.assertTrue(card_calls)
        for card_call in card_calls:
            self.assertGreaterEqual(len(card_call.args), 4)
            for source_argument in card_call.args[:3]:
                self.assertIsInstance(source_argument, ast.Constant)
                self.assertIsInstance(source_argument.value, str)
                self.assertIn(source_argument.value, ROMANIAN_TRANSLATIONS)

    def test_weight_loss_large_deficit_without_many_workouts_stays_coherent(self):
        context = _base_context(
            goal="Slabire",
            avg_estimated_balance=-1100.0,
            activity_days=1,
            workouts_count=1,
            avg_activity_calories_per_active_day=200.0,
            activity_total_calories=200.0,
            interval_weight_delta_kg=-2.5,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Meals").status, "Too little food")
        self.assertEqual(_card(cards, "Movement").status, "Low activity")
        self.assertEqual(_card(cards, "Progress").status, "Progress too fast")

    def test_weight_loss_surplus_and_weight_gain_suggest_adjustment(self):
        context = _base_context(
            goal="Slabire",
            avg_estimated_balance=300.0,
            interval_weight_delta_kg=0.6,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Meals").status, "Meals too heavy")
        self.assertEqual(_card(cards, "Progress").status, "Slow progress")

    def test_weight_gain_goal_with_low_energy_and_regular_training(self):
        context = _base_context(
            goal="Crestere",
            avg_estimated_balance=-200.0,
            activity_days=6,
            workouts_count=6,
            avg_activity_calories_per_active_day=330.0,
            activity_total_calories=1980.0,
            interval_weight_delta_kg=-0.2,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Meals").status, "Too little food")
        self.assertEqual(_card(cards, "Movement").status, "Consistent activity")
        self.assertEqual(_card(cards, "Progress").status, "Slow progress")

    def test_weight_gain_goal_with_excessive_surplus_and_fast_gain(self):
        context = _base_context(
            goal="Crestere",
            avg_estimated_balance=950.0,
            interval_weight_delta_kg=1.8,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Meals").status, "Meals too heavy")
        self.assertEqual(_card(cards, "Progress").status, "Progress too fast")

    def test_maintenance_with_stable_weight_uses_stability_language(self):
        context = _base_context(
            goal="Mentinere",
            avg_estimated_balance=50.0,
            current_weight_kg=62.0,
            interval_weight_delta_kg=0.1,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Meals").status, "Meals on track")
        self.assertEqual(_card(cards, "Progress").status, "Stable weight")

    def test_weight_loss_on_target_uses_good_progress_status(self):
        cards = build_recommendation_cards(_base_context())

        self.assertEqual(_card(cards, "Progress").status, "Good progress")

    def test_maintenance_outside_stable_range_uses_variable_weight_status(self):
        context = _base_context(
            goal="Mentinere",
            avg_estimated_balance=50.0,
            interval_weight_delta_kg=1.0,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Progress").status, "Variable weight")

    def test_protein_card_is_independent_from_energy_card(self):
        context = _base_context(
            goal="Slabire",
            avg_estimated_balance=-350.0,
            avg_protein_per_kg=1.0,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Meals").status, "Meals on track")
        self.assertEqual(_card(cards, "Protein").status, "Low protein")

    def test_weight_gain_goal_accepts_near_target_protein(self):
        context = _base_context(
            goal="Crestere",
            avg_protein_per_kg=1.55,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Protein").status, "Enough protein")

    def test_high_protein_does_not_hide_rich_meals(self):
        context = _base_context(
            goal="Slabire",
            avg_estimated_balance=450.0,
            avg_protein_per_kg=2.0,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Meals").status, "Meals too heavy")
        self.assertEqual(_card(cards, "Protein").status, "Enough protein")

    def test_sparse_food_logs_do_not_force_nutrition_judgement(self):
        context = _base_context(
            food_days=2,
            avg_estimated_balance=-900.0,
            avg_protein_per_kg=0.8,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Meals").status, "Not enough data")
        self.assertEqual(_card(cards, "Protein").status, "Not enough data")

    def test_few_but_hard_workouts_are_not_called_little_movement(self):
        context = _base_context(
            activity_days=2,
            workouts_count=2,
            avg_activity_calories_per_active_day=800.0,
            activity_total_calories=1600.0,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Movement").status, "Intense activity")

    def test_excessive_activity_volume_gets_intense_rhythm(self):
        context = _base_context(
            activity_days=11,
            workouts_count=11,
            avg_activity_calories_per_active_day=300.0,
            activity_total_calories=3300.0,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Movement").status, "Training load too high")

    def test_new_user_with_one_activity_keeps_movement_data_sparse(self):
        context = _base_context(
            food_days=1,
            activity_days=1,
            weight_days=1,
            workouts_count=1,
            avg_estimated_balance=None,
            avg_protein_per_kg=None,
            avg_activity_calories_per_active_day=300.0,
            activity_total_calories=300.0,
            interval_weight_delta_kg=None,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Movement").status, "Not enough data")

    def test_conflicting_actual_and_ml_progress_stays_conservative(self):
        context = _base_context(
            goal="Slabire",
            interval_weight_delta_kg=-0.8,
            predicted_change_kg=0.6,
            predicted_horizon_days=14,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Progress").status, "Keep monitoring")

    def test_new_user_with_sparse_data_gets_data_messages(self):
        context = _base_context(
            food_days=0,
            activity_days=0,
            weight_days=0,
            workouts_count=0,
            avg_estimated_balance=None,
            avg_protein_per_kg=None,
            avg_activity_calories_per_active_day=None,
            activity_total_calories=None,
            current_weight_kg=None,
            interval_weight_delta_kg=None,
        )

        cards = build_recommendation_cards(context)

        self.assertEqual(_card(cards, "Meals").status, "Not enough data")
        self.assertEqual(_card(cards, "Protein").status, "Not enough data")
        self.assertEqual(_card(cards, "Movement").status, "Not enough data")
        self.assertEqual(_card(cards, "Progress").status, "Not enough data")


if __name__ == "__main__":
    unittest.main()
