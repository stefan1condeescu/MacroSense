import inspect
import unittest

from ui.pages import what_if_page
from ui.pages.what_if_page import (
    REFERENCE_CONTEXT_COLUMN_WEIGHTS,
    _format_remaining_error_count,
    _format_signed_value,
    _format_value,
)


class WhatIfPageHelperTests(unittest.TestCase):
    def test_remaining_error_count_uses_singular_for_one_error(self):
        self.assertEqual(
            _format_remaining_error_count(1),
            "Încă o valoare invalidă în scenariu.",
        )

    def test_remaining_error_count_uses_plural_for_multiple_errors(self):
        self.assertEqual(
            _format_remaining_error_count(2),
            "Încă 2 valori invalide în scenariu.",
        )

    def test_reference_context_keeps_four_columns_to_replace_dashboard_card_row(self):
        source = inspect.getsource(what_if_page._render_reference_context)

        self.assertEqual(len(REFERENCE_CONTEXT_COLUMN_WEIGHTS), 4)
        self.assertIn("spacer_col", source)

    def test_what_if_loads_day_context_from_selected_date(self):
        source = inspect.getsource(what_if_page.render_what_if_page)

        self.assertIn("max_value=date.today()", source)
        self.assertIn("DailyLog.get_for_date(int(user_id), selected_date)", source)
        self.assertIn("WeightLog.get_reference_for_user(int(user_id), selected_date)", source)
        self.assertIn("get_daily_energy_estimate(int(user_id), selected_date)", source)

    def test_result_table_formats_kcal_like_dashboard_metrics(self):
        self.assertEqual(_format_value(1671.5, "kcal"), "1672 kcal")
        self.assertEqual(_format_value(2327.6, "kcal"), "2328 kcal")
        self.assertEqual(_format_signed_value(-656.1, "kcal"), "-656 kcal")

    def test_result_table_keeps_macro_grams_at_one_decimal(self):
        self.assertEqual(_format_value(193.04, "g"), "193.0 g")
        self.assertEqual(_format_signed_value(-0.04, "g"), "-0.0 g")


if __name__ == "__main__":
    unittest.main()
