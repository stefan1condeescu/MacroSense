from datetime import date
import inspect
import unittest
from unittest.mock import patch

import pandas as pd

from services.recommendations.simple_recommendations import RecommendationCard
from ui import language
from ui.pages import dashboard_page
from ui.pages.dashboard_page import (
    _analysis_date_context,
    _build_dashboard_card_html,
    _build_recommendation_card_html,
    _build_weight_prediction_cards,
    _daily_x_axis,
    _date_order_domain,
    _format_prediction_source_caption,
    _format_gender,
    _goal_description,
    _prepare_daily_rows,
    _prepare_daily_weight_rows,
    _prepare_macro_rows,
    _resolve_dashboard_analysis_date,
    _resolve_interval_label,
)
from services.ml.prediction import UserWeightPredictions, WeightPrediction


class DashboardPageHelperTests(unittest.TestCase):
    def test_recommendation_card_html_uses_the_active_language(self):
        card = RecommendationCard(
            "Meals",
            "Not enough data",
            "Log meals more often.",
            "quality",
        )

        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_html = _build_recommendation_card_html(card)
        with patch.object(language.st, "session_state", {"language": "en"}):
            english_html = _build_recommendation_card_html(card)

        self.assertIn(">Mese</div>", romanian_html)
        self.assertIn(">Date puține</div>", romanian_html)
        self.assertIn(">Loghează mesele mai des.</div>", romanian_html)
        self.assertIn(">Meals</div>", english_html)
        self.assertIn(">Not enough data</div>", english_html)
        self.assertIn(">Log meals more often.</div>", english_html)
        self.assertIn('class="recommendation-card quality"', romanian_html)
        self.assertIn('class="recommendation-card quality"', english_html)

    def test_recommendation_card_html_escapes_all_card_fields(self):
        card = RecommendationCard(
            "<Meals>",
            "<Status>",
            "<Message>",
            'quality" data-test="unsafe',
        )

        with patch.object(language.st, "session_state", {"language": "en"}):
            html = _build_recommendation_card_html(card)

        self.assertIn("&lt;Meals&gt;", html)
        self.assertIn("&lt;Status&gt;", html)
        self.assertIn("&lt;Message&gt;", html)
        self.assertNotIn("<Meals>", html)
        self.assertNotIn('data-test="unsafe"', html)

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
        self.assertEqual(prepared_rows["Calorii activități"].tolist(), [300, 0])

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

    def test_current_state_uses_goal_description_in_objective_tooltip(self):
        source = inspect.getsource(dashboard_page._render_current_state)

        self.assertIn('"help": _goal_description(current.get("goal")) or GOAL_HELP', source)
        self.assertNotIn("st.caption(goal_description)", source)
        self.assertEqual(
            _goal_description("Crestere"),
            "Accent pe surplus controlat, proteine și antrenamente de forță.",
        )

    def test_macro_chart_has_short_description(self):
        source = inspect.getsource(dashboard_page._render_macro_chart)

        self.assertIn(
            "Distribuția macronutrienților pe proteine, carbohidrați și grăsimi.",
            source,
        )

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

    def test_dashboard_analysis_date_defaults_and_blocks_future_dates(self):
        today = date(2026, 5, 25)

        self.assertEqual(
            _resolve_dashboard_analysis_date(
                None,
                default_date=date(2026, 5, 23),
                today=today,
            ),
            date(2026, 5, 23),
        )
        self.assertEqual(
            _resolve_dashboard_analysis_date(
                date(2026, 5, 26),
                default_date=date(2026, 5, 23),
                today=today,
            ),
            today,
        )

    def test_analysis_date_context_keeps_today_labels_only_for_current_day(self):
        today_context = _analysis_date_context(
            date(2026, 5, 25),
            today=date(2026, 5, 25),
        )
        historical_context = _analysis_date_context(
            date(2026, 5, 23),
            today=date(2026, 5, 25),
        )

        self.assertTrue(today_context["is_today"])
        self.assertEqual(today_context["day_phrase"], "azi")
        self.assertFalse(historical_context["is_today"])
        self.assertEqual(historical_context["day_phrase"], "la data analizată")

    def test_weight_prediction_cards_show_14_and_30_day_outputs(self):
        result = UserWeightPredictions(
            user_id=1,
            analysis_date=date(2026, 5, 18),
            predictions=[
                WeightPrediction(
                    horizon_days=14,
                    analysis_date=date(2026, 5, 18),
                    target_date=date(2026, 6, 1),
                    current_weight_kg=80.0,
                    predicted_change_kg=-0.8,
                    predicted_weight_kg=79.2,
                    model_name="gradient_boosting",
                    metrics={"mae": 0.23},
                ),
                WeightPrediction(
                    horizon_days=30,
                    analysis_date=date(2026, 5, 18),
                    target_date=date(2026, 6, 17),
                    current_weight_kg=80.0,
                    predicted_change_kg=-1.5,
                    predicted_weight_kg=78.5,
                    model_name="gradient_boosting",
                    metrics={"mae": 0.31},
                ),
            ],
            unavailable_horizons={},
        )

        cards = _build_weight_prediction_cards(result)

        self.assertEqual([card["label"] for card in cards], ["Peste 14 zile", "Peste 30 zile"])
        self.assertEqual(cards[0]["value"], "79.2 kg")
        self.assertIn("Schimbare estimată: -0.8 kg", cards[0]["caption"])
        self.assertIn("Data: 01.06.2026", cards[0]["caption"])
        self.assertIn("MAE: 0.23 kg", cards[0]["caption"])
        self.assertNotIn("orientativ", cards[0]["help"].lower())

    def test_weight_prediction_cards_show_missing_artifact_as_untrained_model(self):
        result = UserWeightPredictions(
            user_id=1,
            analysis_date=date(2026, 5, 18),
            predictions=[],
            unavailable_horizons={
                14: "Missing model artifact: artifacts/ml/weight_prediction_14d.joblib",
                30: "Nu există suficiente date recente pentru predicție.",
            },
        )

        cards = _build_weight_prediction_cards(result)

        self.assertEqual(cards[0]["value"], "Indisponibil")
        self.assertEqual(cards[0]["caption"], "Modelele ML nu au fost antrenate încă.")
        self.assertEqual(cards[1]["caption"], "Nu există suficiente date recente pentru predicție.")

    def test_weight_prediction_cards_explain_fallback_start_date(self):
        result = UserWeightPredictions(
            user_id=1,
            analysis_date=date(2026, 5, 23),
            predictions=[
                WeightPrediction(
                    horizon_days=14,
                    analysis_date=date(2026, 5, 23),
                    target_date=date(2026, 6, 6),
                    current_weight_kg=80.0,
                    predicted_change_kg=-0.5,
                    predicted_weight_kg=79.5,
                    model_name="gradient_boosting",
                    metrics={"mae": 0.23},
                )
            ],
            unavailable_horizons={},
        )

        cards = _build_weight_prediction_cards(
            result,
            requested_analysis_date=date(2026, 5, 25),
        )

        self.assertEqual(cards[0]["label"], "Peste 14 zile de la 23.05.2026")
        self.assertEqual(cards[0]["value"], "79.5 kg")

    def test_prediction_caption_mentions_today_is_avoided_for_current_day(self):
        result = UserWeightPredictions(
            user_id=1,
            analysis_date=date(2026, 5, 23),
            predictions=[],
            unavailable_horizons={},
        )

        caption = _format_prediction_source_caption(
            result,
            date(2026, 5, 25),
            today=date(2026, 5, 25),
        )

        self.assertIn("23.05.2026", caption)
        self.assertIn("Ziua curentă este evitată", caption)

    def test_prediction_caption_mentions_selected_date_without_recent_data(self):
        result = UserWeightPredictions(
            user_id=1,
            analysis_date=date(2026, 5, 20),
            predictions=[],
            unavailable_horizons={},
        )

        caption = _format_prediction_source_caption(
            result,
            date(2026, 5, 23),
            today=date(2026, 5, 25),
        )

        self.assertIn("20.05.2026", caption)
        self.assertIn("pentru 23.05.2026 nu există suficiente date recente", caption)

    def test_prediction_caption_for_exact_analysis_date_is_short(self):
        result = UserWeightPredictions(
            user_id=1,
            analysis_date=date(2026, 5, 23),
            predictions=[],
            unavailable_horizons={},
        )

        caption = _format_prediction_source_caption(
            result,
            date(2026, 5, 23),
            today=date(2026, 5, 25),
        )

        self.assertEqual(
            caption,
            "Predicție calculată din datele disponibile până la 23.05.2026.",
        )


if __name__ == "__main__":
    unittest.main()
