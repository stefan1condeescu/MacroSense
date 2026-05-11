import unittest

from services.analytics.energy import (
    calculate_base_tdee,
    calculate_bmi,
    calculate_bmr,
    calculate_estimated_balance,
    calculate_estimated_tdee,
)


class AnalyticsEnergyTests(unittest.TestCase):
    def test_calculate_bmi(self):
        self.assertEqual(calculate_bmi(80, 180), 24.69)

    def test_calculate_bmr_for_male(self):
        self.assertEqual(calculate_bmr(80, 180, 25, "M"), 1805.0)

    def test_calculate_bmr_for_female(self):
        self.assertEqual(calculate_bmr(65, 165, 30, "F"), 1370.25)

    def test_estimated_tdee_adds_logged_activity_to_sedentary_base(self):
        base_tdee = calculate_base_tdee(1805)
        self.assertEqual(base_tdee, 2166.0)
        self.assertEqual(calculate_estimated_tdee(base_tdee, 350), 2516.0)

    def test_estimated_balance_uses_total_estimated_tdee(self):
        self.assertEqual(calculate_estimated_balance(2100, 2516), -416.0)

    def test_calculate_bmr_rejects_unknown_gender(self):
        with self.assertRaises(ValueError):
            calculate_bmr(80, 180, 25, "X")


if __name__ == "__main__":
    unittest.main()
