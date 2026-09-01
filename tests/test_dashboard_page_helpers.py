from datetime import date
import inspect
import unittest
from unittest.mock import patch

import pandas as pd

from services.recommendations.simple_recommendations import RecommendationCard
from ui import language
from ui.pages import dashboard_page
from ui.pages.dashboard_page import (
    DASHBOARD_INTERVAL_KEY,
    INTERVAL_OPTIONS,
    _analysis_date_context,
    _build_dashboard_card_html,
    _build_recommendation_card_html,
    _build_weight_prediction_cards,
    _daily_x_axis,
    _date_order_domain,
    _display_interval_name,
    _format_age,
    _format_gender,
    _format_goal,
    _format_kcal_or_missing,
    _format_prediction_source_caption,
    _format_prediction_unavailable_reason,
    _goal_description,
    _initialize_interval_selection,
    _interval_radio_kwargs,
    _prepare_daily_rows,
    _prepare_daily_weight_rows,
    _prepare_macro_rows,
    _render_interval_summary,
    _resolve_dashboard_analysis_date,
    _resolve_interval_days,
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

        self.assertIn("or translate(GOAL_HELP_SOURCE_TEXT)", source)
        self.assertNotIn("st.caption(goal_description)", source)
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(
                _goal_description("Crestere"),
                "Accent pe surplus controlat, proteine și antrenamente de forță.",
            )
        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(
                _goal_description("Crestere"),
                "Focus on a controlled surplus, protein, and strength training.",
            )

    def test_current_state_display_values_use_the_active_language(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(_format_age(25), "25 ani")
            self.assertEqual(_format_goal("Slabire"), "Slăbire")
            self.assertEqual(_format_kcal_or_missing(None), "Nelogat")

        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(_format_age(25), "25 years")
            self.assertEqual(_format_goal("Slabire"), "Weight loss")
            self.assertEqual(_format_kcal_or_missing(None), "Not logged")

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

    def test_dashboard_interval_registry_uses_stable_ids(self):
        self.assertEqual(INTERVAL_OPTIONS, (7, 30, 90))
        self.assertEqual(_resolve_interval_days(None), 30)
        self.assertEqual(_resolve_interval_days(90), 90)
        self.assertEqual(_resolve_interval_days("90 zile"), 90)
        self.assertEqual(_resolve_interval_days("invalid"), 30)

    def test_dashboard_interval_names_translate_without_changing_ids(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_names = {
                days: _display_interval_name(days) for days in INTERVAL_OPTIONS
            }
        with patch.object(language.st, "session_state", {"language": "en"}):
            english_names = {
                days: _display_interval_name(days) for days in INTERVAL_OPTIONS
            }

        self.assertEqual(
            romanian_names,
            {7: "7 zile", 30: "30 zile", 90: "90 zile"},
        )
        self.assertEqual(
            english_names,
            {7: "7 days", 30: "30 days", 90: "90 days"},
        )

    def test_dashboard_interval_migrates_legacy_session_value(self):
        session_state = {DASHBOARD_INTERVAL_KEY: "90 zile"}

        with patch.object(language.st, "session_state", session_state):
            selected_days = _initialize_interval_selection()
            radio_kwargs = _interval_radio_kwargs(selected_days)

        self.assertEqual(selected_days, 90)
        self.assertEqual(session_state[DASHBOARD_INTERVAL_KEY], 90)
        self.assertEqual(radio_kwargs, {})

        invalid_state = {DASHBOARD_INTERVAL_KEY: "invalid"}
        with patch.object(language.st, "session_state", invalid_state):
            fallback_days = _initialize_interval_selection()

        self.assertEqual(fallback_days, 30)
        self.assertEqual(invalid_state[DASHBOARD_INTERVAL_KEY], 30)

    def test_dashboard_uses_stable_interval_for_ui_and_analytics(self):
        analysis_date = date(2026, 5, 25)
        session_state = {
            "language": "en",
            "user_id": 42,
            DASHBOARD_INTERVAL_KEY: "90 zile",
        }
        dashboard_data = {"current": {}, "end_date": analysis_date}

        with (
            patch.object(language.st, "session_state", session_state),
            patch.object(dashboard_page.st, "title"),
            patch.object(dashboard_page.st, "caption"),
            patch.object(dashboard_page.st, "divider"),
            patch.object(dashboard_page.st, "subheader") as subheader,
            patch.object(
                dashboard_page.st,
                "radio",
                return_value=90,
            ) as radio,
            patch.object(
                dashboard_page,
                "get_latest_user_data_date",
                return_value=analysis_date,
            ),
            patch.object(
                dashboard_page,
                "_render_analysis_date_selector",
                return_value=analysis_date,
            ),
            patch.object(
                dashboard_page,
                "get_dashboard_data",
                return_value=dashboard_data,
            ) as get_data,
            patch.object(dashboard_page, "_render_current_state"),
            patch.object(
                dashboard_page,
                "_render_weight_prediction_section",
                return_value=None,
            ),
            patch.object(dashboard_page, "_render_recommendation_section"),
            patch.object(dashboard_page, "_render_interval_summary"),
            patch.object(dashboard_page, "_render_weight_chart"),
            patch.object(dashboard_page, "_render_calorie_chart"),
            patch.object(dashboard_page, "_render_balance_chart"),
            patch.object(dashboard_page, "_render_macro_chart"),
            patch.object(dashboard_page, "_render_activity_section"),
        ):
            dashboard_page.render_dashboard_page()
            formatted_interval_label = radio.call_args.kwargs["format_func"](30)

        self.assertEqual(session_state[DASHBOARD_INTERVAL_KEY], 90)
        get_data.assert_called_once_with(
            user_id=42,
            days=90,
            end_date=analysis_date,
        )
        subheader.assert_called_once_with("Progress over the interval")
        self.assertEqual(radio.call_args.args[:2], ("Analysis interval", [7, 30, 90]))
        self.assertNotIn("index", radio.call_args.kwargs)
        self.assertEqual(radio.call_args.kwargs["key"], DASHBOARD_INTERVAL_KEY)
        self.assertEqual(formatted_interval_label, "30 days")

    def test_dashboard_interval_default_does_not_prepopulate_session_state(self):
        session_state = {}

        with patch.object(language.st, "session_state", session_state):
            selected_days = _initialize_interval_selection()
            radio_kwargs = _interval_radio_kwargs(selected_days)

        self.assertEqual(selected_days, 30)
        self.assertNotIn(DASHBOARD_INTERVAL_KEY, session_state)
        self.assertEqual(radio_kwargs, {"index": 1})

    def test_dashboard_interval_summary_translates_without_changing_values(self):
        data = {
            "days": 30,
            "daily_rows": pd.DataFrame(
                [
                    {
                        "log_date": date(2026, 5, 1),
                        "reference_weight_kg": 80.0,
                        "reference_weight_days_distance": 0,
                        "reference_weight_uses_future_reference": False,
                    },
                    {
                        "log_date": date(2026, 5, 30),
                        "reference_weight_kg": 79.5,
                        "reference_weight_days_distance": 0,
                        "reference_weight_uses_future_reference": False,
                    },
                ]
            ),
            "summary": {
                "avg_calories_in": 2100.4,
                "avg_estimated_tdee": 2500.2,
                "avg_estimated_balance": -399.8,
                "food_logging_consistency": 80.0,
                "activity_logging_consistency": 50.0,
                "weight_logging_consistency": 10.0,
                "overall_logging_consistency": 90.0,
                "food_days": 24,
                "activity_days": 15,
                "weight_days": 3,
                "logged_days": 27,
                "activity_total_calories": 1235.4,
                "workouts_count": 12,
                "avg_protein_g": 120.3,
                "avg_protein_per_kg": 1.5,
                "has_energy_estimates": False,
            },
        }

        def render_summary(language_code):
            with (
                patch.object(
                    language.st,
                    "session_state",
                    {"language": language_code},
                ),
                patch.object(dashboard_page, "_render_card_grid") as card_grid,
                patch.object(dashboard_page.st, "info") as info,
            ):
                _render_interval_summary(data)
            return card_grid.call_args_list, info.call_args.args[0]

        romanian_calls, romanian_info = render_summary("ro")
        english_calls, english_info = render_summary("en")
        romanian_rows = [render_call.args[0] for render_call in romanian_calls]
        english_rows = [render_call.args[0] for render_call in english_calls]

        self.assertEqual(
            [card["label"] for row in romanian_rows for card in row],
            [
                "Trend greutate interval",
                "Consum mediu / zi logată",
                "TDEE mediu / zi alimentară",
                "Balanță medie / zi alimentară",
                "Consistență alimente",
                "Consistență antrenamente",
                "Consistență greutate",
                "Consistență generală",
                "Calorii activități totale",
                "Înregistrări exerciții",
                "Proteină medie",
                "Proteină / kg corp",
            ],
        )
        self.assertEqual(
            [card["label"] for row in english_rows for card in row],
            [
                "Interval weight trend",
                "Average intake / logged day",
                "Average TDEE / food-logged day",
                "Average balance / food-logged day",
                "Food logging consistency",
                "Activity logging consistency",
                "Weight logging consistency",
                "Overall logging consistency",
                "Total activity calories",
                "Exercise entries",
                "Average protein",
                "Protein / kg body weight",
            ],
        )
        self.assertEqual(
            [card["value"] for row in romanian_rows for card in row],
            [card["value"] for row in english_rows for card in row],
        )
        self.assertEqual(romanian_rows[0][0]["value"], "-0.5 kg")
        self.assertEqual(english_rows[0][3]["value"], "-400 kcal")
        self.assertEqual(romanian_rows[1][0]["caption"], "24 / 30 zile")
        self.assertEqual(english_rows[1][0]["caption"], "24 / 30 days")
        self.assertEqual(
            [render_call.kwargs["columns_count"] for render_call in romanian_calls],
            [4, 4, 4],
        )
        self.assertEqual(
            [card["accent"] for row in romanian_rows for card in row],
            [card["accent"] for row in english_rows for card in row],
        )
        self.assertTrue(
            all(
                romanian_card["help"] != english_card["help"]
                for romanian_row, english_row in zip(romanian_rows, english_rows)
                for romanian_card, english_card in zip(romanian_row, english_row)
            )
        )
        self.assertEqual(
            romanian_info,
            "Adaugă cel puțin o greutate pentru a putea calcula BMR, TDEE și "
            "balanța calorică estimată.",
        )
        self.assertEqual(
            english_info,
            "Add at least one weight entry to calculate BMR, TDEE, and the "
            "estimated calorie balance.",
        )

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
        with patch.object(language.st, "session_state", {"language": "ro"}):
            today_context = _analysis_date_context(
                date(2026, 5, 25),
                today=date(2026, 5, 25),
            )
            historical_context = _analysis_date_context(
                date(2026, 5, 23),
                today=date(2026, 5, 25),
            )

        self.assertTrue(today_context["is_today"])
        self.assertEqual(today_context["state_title"], "Starea curentă")
        self.assertEqual(today_context["day_phrase"], "azi")
        self.assertFalse(historical_context["is_today"])
        self.assertEqual(historical_context["state_title"], "Starea la data analizată")
        self.assertEqual(historical_context["day_phrase"], "la data analizată")

        with patch.object(language.st, "session_state", {"language": "en"}):
            english_today_context = _analysis_date_context(
                date(2026, 5, 25),
                today=date(2026, 5, 25),
            )
            english_historical_context = _analysis_date_context(
                date(2026, 5, 23),
                today=date(2026, 5, 25),
            )

        self.assertEqual(english_today_context["state_title"], "Current state")
        self.assertEqual(english_today_context["day_phrase"], "today")
        self.assertEqual(
            english_historical_context["state_title"],
            "State on the analysis date",
        )
        self.assertEqual(
            english_historical_context["day_phrase"],
            "on the analysis date",
        )

    def test_dashboard_header_and_login_warning_use_the_active_language(self):
        expected_text = {
            "ro": ("🏠 Acasă", "Autentifică-te pentru a vedea dashboard-ul."),
            "en": ("🏠 Home", "Log in to view the dashboard."),
        }

        for language_code, (expected_title, expected_warning) in expected_text.items():
            with self.subTest(language=language_code):
                with (
                    patch.object(
                        language.st,
                        "session_state",
                        {"language": language_code},
                    ),
                    patch.object(dashboard_page.st, "title") as title,
                    patch.object(dashboard_page.st, "caption"),
                    patch.object(dashboard_page.st, "warning") as warning,
                ):
                    dashboard_page.render_dashboard_page()

                title.assert_called_once_with(expected_title)
                warning.assert_called_once_with(expected_warning)

    def test_analysis_date_selector_uses_english_display_text(self):
        latest_data_date = date(2026, 5, 23)
        today = date(2026, 5, 25)

        with (
            patch.object(language.st, "session_state", {"language": "en"}),
            patch.object(
                dashboard_page.st,
                "date_input",
                return_value=latest_data_date,
            ) as date_input,
            patch.object(dashboard_page.st, "caption") as caption,
        ):
            selected_date = dashboard_page._render_analysis_date_selector(
                latest_data_date=latest_data_date,
                today=today,
            )

        self.assertEqual(selected_date, latest_data_date)
        self.assertEqual(date_input.call_args.args[0], "Analysis date")
        self.assertEqual(
            date_input.call_args.kwargs["help"],
            "The dashboard, recommendations, and ML prediction are calculated "
            "through this date.",
        )
        caption.assert_called_once_with(
            "The analysis date is the latest day with logged data."
        )

    def test_current_state_cards_translate_without_changing_data_values(self):
        current = {
            "height_cm": 180,
            "gender": "M",
            "age": 25,
            "goal": "Slabire",
            "current_weight_kg": 80,
            "weight_delta_kg": -0.5,
            "current_bmi": 24.7,
            "current_bmr": 1800,
            "today_estimated_tdee": 2400,
            "today_calories_in": None,
            "today_activity_calories": 300,
            "today_estimated_balance": None,
            "today_has_food_logs": True,
            "today_has_activity_logs": True,
        }

        def render_cards(language_code):
            with (
                patch.object(
                    language.st,
                    "session_state",
                    {"language": language_code},
                ),
                patch.object(dashboard_page.st, "subheader") as subheader,
                patch.object(dashboard_page, "_render_card_grid") as card_grid,
            ):
                dashboard_page._render_current_state(
                    current,
                    date(2026, 5, 25),
                    today=date(2026, 5, 25),
                )
            return (
                subheader.call_args.args[0],
                [call.args[0] for call in card_grid.call_args_list],
            )

        romanian_title, romanian_rows = render_cards("ro")
        english_title, english_rows = render_cards("en")

        self.assertEqual(romanian_title, "Starea curentă")
        self.assertEqual(english_title, "Current state")
        self.assertEqual(
            [card["label"] for card in romanian_rows[0]],
            ["Înălțime", "Sex", "Vârstă", "Obiectiv"],
        )
        self.assertEqual(
            [card["label"] for card in english_rows[0]],
            ["Height", "Gender", "Age", "Goal"],
        )
        self.assertEqual(romanian_rows[0][2]["value"], "25 ani")
        self.assertEqual(english_rows[0][2]["value"], "25 years")
        self.assertEqual(romanian_rows[0][3]["value"], "Slăbire")
        self.assertEqual(english_rows[0][3]["value"], "Weight loss")
        self.assertEqual(romanian_rows[2][0]["value"], "Nelogat")
        self.assertEqual(english_rows[2][0]["value"], "Not logged")
        self.assertEqual(
            [card["label"] for card in english_rows[2]],
            [
                "Calories consumed today",
                "Activity calories today",
                "Estimated balance today",
            ],
        )

    def test_current_state_missing_log_messages_use_date_context_and_language(self):
        today = date(2026, 5, 25)

        def render_info(language_code, analysis_date):
            with (
                patch.object(
                    language.st,
                    "session_state",
                    {"language": language_code},
                ),
                patch.object(dashboard_page.st, "subheader"),
                patch.object(dashboard_page, "_render_card_grid"),
                patch.object(dashboard_page.st, "info") as info,
            ):
                dashboard_page._render_current_state(
                    {},
                    analysis_date,
                    today=today,
                )
            return info.call_args.args[0]

        self.assertEqual(
            render_info("ro", today),
            "Adaugă mesele de azi ca să vezi consumul și balanța energetică. "
            "Fără antrenamente azi: activitatea logată este 0 kcal, deci ziua "
            "este considerată de repaus.",
        )
        self.assertEqual(
            render_info("en", today),
            "Add today's meals to see calorie intake and energy balance. "
            "No workouts today: logged activity is 0 kcal, so the day is treated "
            "as a rest day.",
        )
        self.assertEqual(
            render_info("en", date(2026, 5, 23)),
            "No meals are logged on the analysis date; calorie intake and energy "
            "balance remain unlogged. No workouts are logged on the analysis "
            "date; activity is 0 kcal, as on a rest day.",
        )

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

        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_cards = _build_weight_prediction_cards(result)
        with patch.object(language.st, "session_state", {"language": "en"}):
            english_cards = _build_weight_prediction_cards(result)

        self.assertEqual(
            [card["label"] for card in romanian_cards],
            ["Peste 14 zile", "Peste 30 zile"],
        )
        self.assertEqual(
            [card["label"] for card in english_cards],
            ["In 14 days", "In 30 days"],
        )
        self.assertEqual(romanian_cards[0]["value"], "79.2 kg")
        self.assertEqual(english_cards[0]["value"], "79.2 kg")
        self.assertIn(
            "Schimbare estimată: -0.8 kg",
            romanian_cards[0]["caption"],
        )
        self.assertIn("Estimated change: -0.8 kg", english_cards[0]["caption"])
        self.assertIn("Date: 01.06.2026", english_cards[0]["caption"])
        self.assertIn("MAE: 0.23 kg", english_cards[0]["caption"])
        self.assertNotIn("orientativ", romanian_cards[0]["help"].lower())

    def test_weight_prediction_runtime_error_uses_safe_translated_message(self):
        expected_text = {
            "ro": (
                "Predicție greutate",
                "Predicția ML nu este disponibilă momentan. Verifică modelele "
                "antrenate și conexiunea la baza de date.",
            ),
            "en": (
                "Weight prediction",
                "The ML prediction is temporarily unavailable. Check the trained "
                "models and database connection.",
            ),
        }

        for language_code, (expected_title, expected_info) in expected_text.items():
            with self.subTest(language=language_code):
                with (
                    patch.object(
                        language.st,
                        "session_state",
                        {"language": language_code},
                    ),
                    patch.object(dashboard_page.st, "subheader") as subheader,
                    patch.object(dashboard_page.st, "info") as info,
                    patch.object(
                        dashboard_page,
                        "get_latest_available_user_weight_predictions",
                        side_effect=RuntimeError("database details"),
                    ),
                ):
                    result = dashboard_page._render_weight_prediction_section(
                        user_id=7,
                        analysis_date=date(2026, 5, 25),
                        today=date(2026, 5, 25),
                    )

                self.assertIsNone(result)
                subheader.assert_called_once_with(expected_title)
                info.assert_called_once_with(expected_info)
                self.assertNotIn("database details", info.call_args.args[0])

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

        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_cards = _build_weight_prediction_cards(result)
        with patch.object(language.st, "session_state", {"language": "en"}):
            english_cards = _build_weight_prediction_cards(result)

        self.assertEqual(romanian_cards[0]["value"], "Indisponibil")
        self.assertEqual(english_cards[0]["value"], "Unavailable")
        self.assertEqual(
            romanian_cards[0]["caption"],
            "Modelele ML nu au fost antrenate încă.",
        )
        self.assertEqual(
            english_cards[0]["caption"],
            "The ML models have not been trained yet.",
        )
        self.assertEqual(
            romanian_cards[1]["caption"],
            "Nu există suficiente date recente pentru predicție.",
        )
        self.assertEqual(
            english_cards[1]["caption"],
            "There is not enough recent data for a prediction.",
        )

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

        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_cards = _build_weight_prediction_cards(
                result,
                requested_analysis_date=date(2026, 5, 25),
            )
        with patch.object(language.st, "session_state", {"language": "en"}):
            english_cards = _build_weight_prediction_cards(
                result,
                requested_analysis_date=date(2026, 5, 25),
            )

        self.assertEqual(
            romanian_cards[0]["label"],
            "Peste 14 zile de la 23.05.2026",
        )
        self.assertEqual(
            english_cards[0]["label"],
            "In 14 days from 23.05.2026",
        )
        self.assertEqual(english_cards[0]["value"], "79.5 kg")

    def test_prediction_caption_mentions_today_is_avoided_for_current_day(self):
        result = UserWeightPredictions(
            user_id=1,
            analysis_date=date(2026, 5, 23),
            predictions=[],
            unavailable_horizons={},
        )

        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_caption = _format_prediction_source_caption(
                result,
                date(2026, 5, 25),
                today=date(2026, 5, 25),
            )
        with patch.object(language.st, "session_state", {"language": "en"}):
            english_caption = _format_prediction_source_caption(
                result,
                date(2026, 5, 25),
                today=date(2026, 5, 25),
            )

        self.assertIn("Ziua curentă este evitată", romanian_caption)
        self.assertIn("The current day is skipped", english_caption)
        self.assertIn("23.05.2026", english_caption)

    def test_prediction_caption_mentions_selected_date_without_recent_data(self):
        result = UserWeightPredictions(
            user_id=1,
            analysis_date=date(2026, 5, 20),
            predictions=[],
            unavailable_horizons={},
        )

        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_caption = _format_prediction_source_caption(
                result,
                date(2026, 5, 23),
                today=date(2026, 5, 25),
            )
        with patch.object(language.st, "session_state", {"language": "en"}):
            english_caption = _format_prediction_source_caption(
                result,
                date(2026, 5, 23),
                today=date(2026, 5, 25),
            )

        self.assertIn(
            "pentru 23.05.2026 nu există suficiente date recente",
            romanian_caption,
        )
        self.assertIn(
            "there is not enough recent data for 23.05.2026",
            english_caption,
        )

    def test_prediction_caption_for_exact_analysis_date_is_short(self):
        result = UserWeightPredictions(
            user_id=1,
            analysis_date=date(2026, 5, 23),
            predictions=[],
            unavailable_horizons={},
        )

        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_caption = _format_prediction_source_caption(
                result,
                date(2026, 5, 23),
                today=date(2026, 5, 25),
            )
        with patch.object(language.st, "session_state", {"language": "en"}):
            english_caption = _format_prediction_source_caption(
                result,
                date(2026, 5, 23),
                today=date(2026, 5, 25),
            )

        self.assertEqual(
            romanian_caption,
            "Predicție calculată din datele disponibile până la 23.05.2026.",
        )
        self.assertEqual(
            english_caption,
            "Prediction calculated from data available through 23.05.2026.",
        )

    def test_prediction_unavailable_reason_hides_technical_details(self):
        with patch.object(language.st, "session_state", {"language": "en"}):
            missing_user = _format_prediction_unavailable_reason(
                "Utilizatorul nu există."
            )
            technical_error = _format_prediction_unavailable_reason(
                "ML model prediction failed: shape mismatch"
            )

        self.assertEqual(missing_user, "The user could not be found.")
        self.assertEqual(
            technical_error,
            "The ML prediction is temporarily unavailable.",
        )
        self.assertNotIn("shape mismatch", technical_error)


if __name__ == "__main__":
    unittest.main()
