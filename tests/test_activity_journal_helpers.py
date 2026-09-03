import datetime
import inspect
import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from models.tracking import Activity
from ui import language
from ui.activity_selection import (
    ACTIVITY_CALCULATION_METHOD_SOURCE_TEXT,
    ACTIVITY_CATEGORY_SOURCE_TEXT,
    ACTIVITY_MET_METHOD_SOURCE_TEXT,
    build_activity_selection_dataframe,
    build_activity_selection_display_dataframe,
    build_activity_selection_state_key,
    format_activity_calculation_method_for_display,
    format_activity_category_for_display,
    format_activity_met_method_for_display,
    get_activity_category_filter_options,
)
from ui.activity_validation import (
    duration_range_help_for_ui,
    validate_duration_minutes_for_ui,
    validate_reps_for_ui,
    validate_sets_for_ui,
)
from ui.catalog_constants import ACTIVITY_CATEGORIES
from ui.pages import activity_journal_page
from ui.pages.activity_journal_page import (
    format_activity_journal_date,
    format_activity_log_option,
    is_strength_activity,
    validate_manual_calories_input,
)
from ui.tables import build_activity_log_cards_html


class ActivityJournalHelperTests(unittest.TestCase):
    def test_category_mapping_covers_stable_activity_categories(self):
        self.assertEqual(
            set(ACTIVITY_CATEGORY_SOURCE_TEXT),
            {"Toate", *ACTIVITY_CATEGORIES},
        )

        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(format_activity_category_for_display("Forță"), "Strength")
            self.assertEqual(format_activity_category_for_display("Necunoscută"), "Necunoscută")

        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(format_activity_category_for_display("Forță"), "Forță")
            self.assertEqual(format_activity_category_for_display("Sport de echipă"), "Sport de echipă")

    def test_strength_behavior_uses_raw_category_in_both_languages(self):
        for language_code in ("en", "ro"):
            with self.subTest(language_code=language_code):
                with patch.object(
                    language.st,
                    "session_state",
                    {"language": language_code},
                ):
                    self.assertTrue(is_strength_activity({"category": "Forță"}))
                    self.assertFalse(is_strength_activity({"category": "Strength"}))
                    self.assertFalse(is_strength_activity({"category": "Cardio"}))

    def test_selector_translates_a_copy_and_preserves_raw_ids_and_values(self):
        activity_options = {
            17: {
                "id": 17,
                "name": "Flotări moderate",
                "category": "Forță",
                "source_label": "MacroSense",
                "met_method_label": "Mapare MacroSense",
                "met": 3.8,
            }
        }
        raw_dataframe = build_activity_selection_dataframe(
            activity_options,
            "flotari",
            "Forță",
        )
        original_dataframe = raw_dataframe.copy(deep=True)

        with patch.object(language.st, "session_state", {"language": "en"}):
            english_dataframe = build_activity_selection_display_dataframe(raw_dataframe)
        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_dataframe = build_activity_selection_display_dataframe(raw_dataframe)

        assert_frame_equal(raw_dataframe, original_dataframe)
        self.assertEqual(english_dataframe.iloc[0]["_activity_id"], 17)
        self.assertEqual(english_dataframe.iloc[0]["MET"], 3.8)
        self.assertEqual(english_dataframe.iloc[0]["Sursă"], "MacroSense")
        self.assertEqual(english_dataframe.iloc[0]["Categorie"], "Strength")
        self.assertEqual(english_dataframe.iloc[0]["Metodă MET"], "MacroSense mapping")
        self.assertEqual(romanian_dataframe.iloc[0]["Categorie"], "Forță")
        self.assertEqual(romanian_dataframe.iloc[0]["Metodă MET"], "Mapare MacroSense")

    def test_filter_and_state_key_continue_to_use_raw_category(self):
        activity_options = {
            17: {
                "id": 17,
                "name": "Flotări moderate",
                "category": "Forță",
                "met": 3.8,
            },
            18: {
                "id": 18,
                "name": "Alergare",
                "category": "Cardio",
                "met": 7.0,
            },
        }

        self.assertEqual(
            get_activity_category_filter_options(activity_options),
            ["Toate", "Cardio", "Forță"],
        )
        filtered = build_activity_selection_dataframe(
            activity_options,
            "",
            "Forță",
        )
        self.assertEqual(filtered["_activity_id"].tolist(), [17])
        self.assertEqual(filtered["Categorie"].tolist(), ["Forță"])

        raw_key = build_activity_selection_state_key("flotari", "Forță")
        translated_key = build_activity_selection_state_key("flotari", "Strength")
        self.assertNotEqual(raw_key, translated_key)

    def test_met_method_mapping_covers_model_codes_and_labels(self):
        self.assertTrue(set(Activity.ESTIMATION_METHODS).issubset(ACTIVITY_MET_METHOD_SOURCE_TEXT))
        self.assertTrue(set(Activity.ESTIMATION_METHODS.values()).issubset(ACTIVITY_MET_METHOD_SOURCE_TEXT))

        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(
                format_activity_met_method_for_display("official_compendium"),
                "Official Compendium",
            )
            self.assertEqual(
                format_activity_met_method_for_display("Mapare MacroSense"),
                "MacroSense mapping",
            )
            self.assertEqual(format_activity_met_method_for_display("custom"), "custom")

        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(
                format_activity_met_method_for_display("compendium_mapping"),
                "Mapare MacroSense",
            )
            self.assertEqual(
                format_activity_met_method_for_display("Manual Admin"),
                "Manual Admin",
            )

    def test_calculation_method_mapping_keeps_raw_service_values(self):
        self.assertEqual(
            set(ACTIVITY_CALCULATION_METHOD_SOURCE_TEXT),
            {"Manual", "Estimare MacroSense"},
        )
        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(format_activity_calculation_method_for_display("Manual"), "Manual")
            self.assertEqual(
                format_activity_calculation_method_for_display("Estimare MacroSense"),
                "MacroSense estimate",
            )
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(
                format_activity_calculation_method_for_display("Estimare MacroSense"),
                "Estimare MacroSense",
            )

    def test_dates_and_log_options_translate_display_only(self):
        entries = pd.DataFrame(
            [
                {
                    "Activitate": "Flotări",
                    "Categorie": "Forță",
                    "Durată (min)": 30.0,
                    "Calorii Arse": 125.5,
                }
            ],
            index=[17],
        )

        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(format_activity_journal_date(datetime.date(2026, 5, 25)), "25 May 2026")
            self.assertEqual(
                format_activity_log_option(entries, 17),
                "Flotări (Strength, 30 min, 125.5 kcal)",
            )
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(format_activity_journal_date(datetime.date(2026, 5, 25)), "25 Mai 2026")
            self.assertEqual(
                format_activity_log_option(entries, 17),
                "Flotări (Forță, 30 min, 125.5 kcal)",
            )

        self.assertEqual(entries.index.tolist(), [17])

    def test_all_month_names_have_romanian_display_labels(self):
        expected_months = [
            "Ianuarie",
            "Februarie",
            "Martie",
            "Aprilie",
            "Mai",
            "Iunie",
            "Iulie",
            "August",
            "Septembrie",
            "Octombrie",
            "Noiembrie",
            "Decembrie",
        ]
        with patch.object(language.st, "session_state", {"language": "ro"}):
            actual_months = [
                format_activity_journal_date(datetime.date(2026, month, 1)).split()[1]
                for month in range(1, 13)
            ]

        self.assertEqual(actual_months, expected_months)

    def test_activity_validation_messages_follow_the_selected_language(self):
        expectations = {
            "en": {
                "duration_invalid": "Duration must be a valid number.",
                "duration_low": "Duration must be at least 0.1 minutes.",
                "duration_high": "Duration must be at most 600 minutes.",
                "sets_low": "Set count must be at least 1.",
                "sets_high": "Set count must be at most 50.",
                "reps_low": "Repetition count must be at least 1.",
                "reps_high": "Repetition count must be at most 200.",
                "help": "Accepted range: 0.1-600 minutes.",
            },
            "ro": {
                "duration_invalid": "Durată trebuie să fie un număr valid.",
                "duration_low": "Durată trebuie să fie cel puțin 0.1 minute.",
                "duration_high": "Durată trebuie să fie cel mult 600 minute.",
                "sets_low": "Numărul de seturi trebuie să fie cel puțin 1.",
                "sets_high": "Numărul de seturi trebuie să fie cel mult 50.",
                "reps_low": "Numărul de repetări trebuie să fie cel puțin 1.",
                "reps_high": "Numărul de repetări trebuie să fie cel mult 200.",
                "help": "Interval acceptat: 0.1-600 minute.",
            },
        }

        for language_code, expected in expectations.items():
            with self.subTest(language_code=language_code):
                with patch.object(
                    language.st,
                    "session_state",
                    {"language": language_code},
                ):
                    self.assertEqual(validate_duration_minutes_for_ui("x"), expected["duration_invalid"])
                    self.assertEqual(validate_duration_minutes_for_ui(0), expected["duration_low"])
                    self.assertEqual(validate_duration_minutes_for_ui(601), expected["duration_high"])
                    self.assertIsNone(validate_duration_minutes_for_ui(0.1))
                    self.assertIsNone(validate_duration_minutes_for_ui(600))
                    self.assertEqual(validate_sets_for_ui(0), expected["sets_low"])
                    self.assertEqual(validate_sets_for_ui(51), expected["sets_high"])
                    self.assertIsNone(validate_sets_for_ui(1))
                    self.assertIsNone(validate_sets_for_ui(50))
                    self.assertEqual(validate_reps_for_ui(0), expected["reps_low"])
                    self.assertEqual(validate_reps_for_ui(201), expected["reps_high"])
                    self.assertIsNone(validate_reps_for_ui(1))
                    self.assertIsNone(validate_reps_for_ui(200))
                    self.assertEqual(duration_range_help_for_ui(), expected["help"])

    def test_manual_calorie_validation_follows_language_and_model_limits(self):
        for language_code, expected_error in (
            ("en", "Manual calories must be between 1 and 5000 kcal."),
            ("ro", "Caloriile manuale trebuie să fie între 1 și 5000 kcal."),
        ):
            with self.subTest(language_code=language_code):
                with patch.object(
                    language.st,
                    "session_state",
                    {"language": language_code},
                ):
                    self.assertIsNone(validate_manual_calories_input(None))
                    self.assertIsNone(validate_manual_calories_input(1))
                    self.assertIsNone(validate_manual_calories_input(5000))
                    self.assertEqual(validate_manual_calories_input(0), expected_error)
                    self.assertEqual(validate_manual_calories_input(5001), expected_error)

    def test_activity_cards_translate_display_without_mutating_service_data(self):
        dataframe = pd.DataFrame(
            [
                {
                    "Activitate": "Flotări <script>",
                    "Categorie": "Forță",
                    "Durată (min)": 30,
                    "Seturi": 3,
                    "Repetări": 12,
                    "Metodă calcul": "Manual",
                    "Calorii Arse": 125.5,
                },
                {
                    "Activitate": "Alergare",
                    "Categorie": "Cardio",
                    "Durată (min)": 45,
                    "Seturi": "-",
                    "Repetări": "-",
                    "Metodă calcul": "Estimare MacroSense",
                    "Calorii Arse": 420,
                },
            ]
        )
        original_dataframe = dataframe.copy(deep=True)

        with patch.object(language.st, "session_state", {"language": "en"}):
            english_html = build_activity_log_cards_html(dataframe)
        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_html = build_activity_log_cards_html(dataframe)

        assert_frame_equal(dataframe, original_dataframe)
        self.assertIn("log-entry-badge manual", english_html)
        self.assertIn("log-entry-badge estimated", english_html)
        self.assertIn(">MacroSense estimate</span>", english_html)
        self.assertIn("<span>Category</span><strong>Strength</strong>", english_html)
        self.assertIn("<span>Duration</span><strong>30.0 min</strong>", english_html)
        self.assertIn("<span>Calories</span><strong>125.5 kcal</strong>", english_html)
        self.assertIn(">Estimare MacroSense</span>", romanian_html)
        self.assertIn("<span>Categorie</span><strong>Forță</strong>", romanian_html)
        self.assertIn("<span>Durată</span><strong>30.0 min</strong>", romanian_html)
        self.assertIn("Flotări &lt;script&gt;", english_html)
        self.assertNotIn("Flotări <script>", english_html)

    def test_persistence_flow_still_passes_raw_ids_and_activity_values(self):
        source = inspect.getsource(activity_journal_page.render_activity_journal_page)

        self.assertIn('activity_id=selected_activity["id"]', source)
        self.assertIn('edited_activity["id"]', source)
        self.assertIn('(selected_activity["category"] or "").strip()', source)
        self.assertIn('(edited_activity["category"] or "").strip()', source)
        self.assertIn("manual_calories_burned=manual_calories", source)
        self.assertIn("manual_calories_burned=edited_manual_calories", source)
        self.assertIn("daily_log_for_write.recalculate_totals()", source)
        self.assertIn("DailyLog.delete_if_empty(daily_log.id, user_id)", source)


if __name__ == "__main__":
    unittest.main()
