from datetime import date
import unittest

import pandas as pd

from ui.pages.dashboard_page import (
    _build_dashboard_card_html,
    _daily_x_axis,
    _date_order_domain,
    _format_gender,
    _prepare_daily_rows,
    _prepare_daily_weight_rows,
    _prepare_macro_rows,
    _resolve_interval_label,
)


class DashboardPageHelperTests(unittest.TestCase):
    def test_daily_chart_rows_use_one_discrete_label_per_day(self):
        rows = pd.DataFrame(
            [
                {
                    "log_date": date(2026, 5, 6),
                    "food_calories_in": 2000,
                    "estimated_tdee": 2400,
                    "estimated_balance": -400,
                    "activity_calories_burned": 300,
                },
                {
                    "log_date": date(2026, 5, 7),
                    "food_calories_in": 2200,
                    "estimated_tdee": 2500,
                    "estimated_balance": -300,
                    "activity_calories_burned": 0,
                },
            ]
        )

        prepared_rows = _prepare_daily_rows(rows)

        self.assertEqual(prepared_rows["DataLabel"].tolist(), ["06.05", "07.05"])
        self.assertEqual(
            prepared_rows["DataOrder"].tolist(), ["2026-05-06", "2026-05-07"]
        )
        self.assertEqual(prepared_rows["Calorii arse"].tolist(), [300, 0])

    def test_macro_chart_rows_keep_date_labels_for_melted_chart(self):
        rows = pd.DataFrame(
            [
                {
                    "log_date": date(2026, 5, 9),
                    "protein_g": 80,
                    "carbs_g": 240,
                    "fats_g": 40,
                }
            ]
        )

        prepared_rows = _prepare_macro_rows(rows)

        self.assertEqual(prepared_rows.loc[0, "DataLabel"], "09.05")
        self.assertEqual(prepared_rows.loc[0, "DataOrder"], "2026-05-09")

    def test_daily_weight_rows_include_reference_source_labels(self):
        rows = pd.DataFrame(
            [
                {
                    "log_date": date(2026, 5, 4),
                    "reference_weight_kg": 80,
                    "reference_weight_days_distance": 0,
                    "reference_weight_uses_future_reference": False,
                },
                {
                    "log_date": date(2026, 5, 5),
                    "reference_weight_kg": 80,
                    "reference_weight_days_distance": 1,
                    "reference_weight_uses_future_reference": False,
                },
                {
                    "log_date": date(2026, 5, 2),
                    "reference_weight_kg": 80,
                    "reference_weight_days_distance": 2,
                    "reference_weight_uses_future_reference": True,
                },
            ]
        )

        prepared_rows = _prepare_daily_weight_rows(rows)

        self.assertEqual(prepared_rows.loc[0, "Sursă referință"], "Cântărire reală")
        self.assertEqual(
            prepared_rows.loc[1, "Sursă referință"],
            "Greutate anterioară folosită ca referință",
        )
        self.assertEqual(
            prepared_rows.loc[2, "Sursă referință"],
            "Fallback din prima greutate viitoare",
        )

    def test_gender_is_compact_for_dashboard_cards(self):
        self.assertEqual(_format_gender("M"), "M")
        self.assertEqual(_format_gender("F"), "F")

    def test_dashboard_card_html_renders_caption_without_markdown_code_block(self):
        html = _build_dashboard_card_html(
            label="Consistență alimente",
            value="90.0%",
            caption="27 / 30 zile",
            help="Explicație",
        )

        self.assertNotIn("\n    <div", html)
        self.assertIn('<div class="dashboard-card-caption">27 / 30 zile</div>', html)

    def test_dashboard_card_html_escapes_user_visible_text(self):
        html = _build_dashboard_card_html(
            label="<b>Label</b>",
            value="<script>alert(1)</script>",
            caption="<span>caption</span>",
            help='quote " test',
        )

        self.assertIn("&lt;b&gt;Label&lt;/b&gt;", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("&lt;span&gt;caption&lt;/span&gt;", html)
        self.assertIn("quote &quot; test", html)

    def test_daily_x_axis_uses_discrete_dates_instead_of_temporal_ticks(self):
        axis_spec = _daily_x_axis().to_dict()

        self.assertEqual(axis_spec["field"], "DataOrder")
        self.assertEqual(axis_spec["type"], "nominal")
        self.assertIn("substring(datum.label", axis_spec["axis"]["labelExpr"])

    def test_daily_x_axis_can_share_the_full_interval_domain(self):
        axis_spec = _daily_x_axis(["2026-05-08", "2026-05-09", "2026-05-10"]).to_dict()

        self.assertEqual(
            axis_spec["scale"]["domain"], ["2026-05-08", "2026-05-09", "2026-05-10"]
        )

    def test_date_order_domain_uses_unique_calendar_days(self):
        rows = pd.DataFrame(
            {
                "DataOrder": ["2026-05-08", "2026-05-09", "2026-05-09"],
            }
        )

        self.assertEqual(_date_order_domain(rows), ["2026-05-08", "2026-05-09"])

    def test_dashboard_interval_defaults_without_session_state_assignment(self):
        self.assertEqual(_resolve_interval_label(None), "30 zile")
        self.assertEqual(_resolve_interval_label("90 zile"), "90 zile")
        self.assertEqual(_resolve_interval_label("invalid"), "30 zile")


if __name__ == "__main__":
    unittest.main()
