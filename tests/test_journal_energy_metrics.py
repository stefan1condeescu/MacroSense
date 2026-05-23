import inspect
import re
import unittest
from decimal import Decimal

import pandas as pd

from ui.pages import activity_journal_page, food_journal_page, what_if_page


class JournalEnergyMetricTests(unittest.TestCase):
    def test_food_and_activity_journals_use_dashboard_energy_estimate(self):
        for module in (food_journal_page, activity_journal_page):
            source = inspect.getsource(module)

            self.assertIn("get_daily_energy_estimate", source)
            self.assertIn("estimated_balance", source)
            self.assertNotIn("calculate_energy_balance()", source)

    def test_what_if_uses_estimated_balance_not_activity_only_journal_balance(self):
        source = inspect.getsource(what_if_page)

        self.assertIn("TDEE estimat", source)
        self.assertIn("Balanță estimată", source)
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
