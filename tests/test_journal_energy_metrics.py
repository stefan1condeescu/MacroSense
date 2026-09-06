import inspect
import re
import unittest
from decimal import Decimal
from unittest.mock import patch

import pandas as pd

from ui import language
from ui.pages import activity_journal_page, food_journal_page, what_if_page
from ui import journal_energy_summary
from ui.journal_energy_summary import build_daily_energy_summary_cards


def _summary_values(energy_estimate, language_code="ro"):
    with patch.object(language.st, "session_state", {"language": language_code}):
        return {
            card["label"]: card["value"]
            for card in build_daily_energy_summary_cards(energy_estimate)
        }


class JournalEnergyMetricTests(unittest.TestCase):
    def test_food_and_activity_journals_use_dashboard_energy_estimate(self):
        for module in (food_journal_page, activity_journal_page):
            source = inspect.getsource(module)

            self.assertIn("get_daily_energy_estimate", source)
            self.assertIn("render_daily_energy_summary", source)
            self.assertNotIn("calculate_energy_balance()", source)

        summary_source = inspect.getsource(journal_energy_summary)
        self.assertIn("estimated_balance", summary_source)

    def test_what_if_uses_estimated_balance_not_activity_only_journal_balance(self):
        source = inspect.getsource(what_if_page)

        self.assertIn('translate("Estimated TDEE")', source)
        self.assertIn('translate("Estimated balance")', source)
        self.assertIn("estimated_balance", source)
        self.assertNotIn("journal_balance", source)

    def test_activity_strength_metric_normalizes_database_decimal_sums(self):
        activity_breakdown = pd.DataFrame(
            [
                {"category": "Forță", "total_calories_burned": Decimal("80.4")},
                {"category": "Cardio", "total_calories_burned": Decimal("562.0")},
            ]
        )

        result = activity_journal_page._sum_activity_breakdown_category(
            activity_breakdown,
            "Forță",
        )

        self.assertEqual(result, 80.4)

    def test_journal_summary_treats_activity_only_day_like_dashboard(self):
        values = _summary_values(
            {
                "has_food_logs": False,
                "food_calories_in": None,
                "activity_calories_burned": 320.0,
                "estimated_tdee": 2320.0,
                "estimated_balance": None,
            }
        )

        self.assertEqual(values["Calorii consumate"], "Nelogat")
        self.assertEqual(values["Calorii activități"], "320 kcal")
        self.assertEqual(values["TDEE estimat"], "2320 kcal")
        self.assertEqual(values["Balanță estimată"], "Nelogat")

    def test_journal_summary_treats_food_only_day_like_dashboard(self):
        values = _summary_values(
            {
                "has_food_logs": True,
                "food_calories_in": 1800.0,
                "activity_calories_burned": None,
                "estimated_tdee": 2100.0,
                "estimated_balance": -300.0,
            }
        )

        self.assertEqual(values["Calorii consumate"], "1800 kcal")
        self.assertEqual(values["Calorii activități"], "0 kcal")
        self.assertEqual(values["TDEE estimat"], "2100 kcal")
        self.assertEqual(values["Balanță estimată"], "-300 kcal")

    def test_journal_summary_uses_english_labels_when_selected(self):
        values = _summary_values(
            {
                "has_food_logs": False,
                "food_calories_in": None,
                "activity_calories_burned": 320.0,
                "estimated_tdee": 2320.0,
                "estimated_balance": None,
            },
            language_code="en",
        )

        self.assertEqual(values["Calories consumed"], "Not logged")
        self.assertEqual(values["Activity calories"], "320 kcal")
        self.assertEqual(values["Estimated TDEE"], "2320 kcal")
        self.assertEqual(values["Estimated balance"], "Not logged")

    def test_food_journal_recalculates_daily_totals_after_all_mutations(self):
        source = inspect.getsource(food_journal_page.render_food_journal_page)

        expected_patterns = [
            r"if food_log_entry\.save\(\):\s+daily_log_for_write\.recalculate_totals\(\)",
            r"if custom_meal_log_entry\.save\(\):\s+daily_log_for_write\.recalculate_totals\(\)",
            r"if FoodLog\.update\([\s\S]+?\):\s+daily_log\.recalculate_totals\(\)",
            r"elif FoodLog\.delete\([\s\S]+?\):\s+daily_log\.recalculate_totals\(\)",
        ]

        for pattern in expected_patterns:
            with self.subTest(pattern=pattern):
                self.assertRegex(source, pattern)

    def test_activity_journal_recalculates_daily_totals_after_all_mutations(self):
        source = inspect.getsource(activity_journal_page.render_activity_journal_page)

        expected_patterns = [
            r"if act_log_entry\.save\(\):\s+daily_log_for_write\.recalculate_totals\(\)",
            r"if ActivityLog\.update\([\s\S]+?\):\s+daily_log\.recalculate_totals\(\)",
            r"elif ActivityLog\.delete\([\s\S]+?\):\s+daily_log\.recalculate_totals\(\)",
        ]

        for pattern in expected_patterns:
            with self.subTest(pattern=pattern):
                self.assertRegex(source, pattern)


if __name__ == "__main__":
    unittest.main()
