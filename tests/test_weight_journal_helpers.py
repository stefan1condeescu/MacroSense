import datetime
import inspect
import unittest
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from ui import language
from ui.pages import weight_journal_page
from ui.pages.weight_journal_page import (
    WEIGHT_CHANGE_MESSAGE_SOURCE_TEXT,
    clamp_weight_value,
    format_weight_change_message,
    format_weight_date,
    format_weight_option,
    future_weight_date_error_message,
    has_weight_entry_for_date,
    is_future_weight_date,
    is_weight_in_allowed_range,
    normalize_weight_date,
    weight_range_error_message,
)
from ui.tables import build_weight_log_cards_html


class WeightJournalHelperTests(unittest.TestCase):
    def test_weight_dates_are_normalized_and_formatted_consistently(self):
        timestamp = datetime.datetime(2026, 5, 25, 14, 30)
        log_date = datetime.date(2026, 5, 25)

        self.assertEqual(normalize_weight_date(timestamp), log_date)
        self.assertEqual(normalize_weight_date(log_date), log_date)
        self.assertEqual(format_weight_date(timestamp), "25.05.2026")
        self.assertEqual(format_weight_date(log_date), "25.05.2026")

    def test_weight_selector_formats_numeric_id_without_replacing_it(self):
        entries = pd.DataFrame(
            [{"Data": datetime.date(2026, 5, 25), "Greutate (kg)": 78.4}],
            index=[17],
        )

        for language_code in ("en", "ro"):
            with self.subTest(language_code=language_code):
                with patch.object(
                    language.st,
                    "session_state",
                    {"language": language_code},
                ):
                    self.assertEqual(
                        format_weight_option(entries, 17),
                        "25.05.2026 - 78.4 kg",
                    )

        self.assertEqual(entries.index.tolist(), [17])

    def test_duplicate_date_check_can_exclude_the_edited_numeric_id(self):
        entries = pd.DataFrame(
            [
                {"Data": datetime.datetime(2026, 5, 25, 8, 0)},
                {"Data": datetime.date(2026, 5, 26)},
            ],
            index=[17, 18],
        )

        self.assertTrue(
            has_weight_entry_for_date(entries, datetime.date(2026, 5, 25))
        )
        self.assertFalse(
            has_weight_entry_for_date(
                entries,
                datetime.date(2026, 5, 25),
                excluded_entry_id=17,
            )
        )
        self.assertTrue(
            has_weight_entry_for_date(
                entries,
                datetime.date(2026, 5, 26),
                excluded_entry_id=17,
            )
        )

    def test_weight_validation_keeps_model_limits_and_translates_messages(self):
        self.assertTrue(is_weight_in_allowed_range(30))
        self.assertTrue(is_weight_in_allowed_range(300))
        self.assertFalse(is_weight_in_allowed_range(29.9))
        self.assertFalse(is_weight_in_allowed_range(300.1))
        self.assertEqual(clamp_weight_value(20), 30)
        self.assertEqual(clamp_weight_value(310), 300)

        today = datetime.date(2026, 5, 25)
        self.assertFalse(is_future_weight_date(today, today))
        self.assertTrue(
            is_future_weight_date(datetime.date(2026, 5, 26), today)
        )

        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(
                weight_range_error_message(),
                "Weight must be between 30 and 300 kg.",
            )
            self.assertEqual(
                future_weight_date_error_message(),
                "The measurement date cannot be in the future.",
            )

        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(
                weight_range_error_message(),
                "Greutatea trebuie să fie între 30 și 300 kg.",
            )
            self.assertEqual(
                future_weight_date_error_message(),
                "Data măsurării nu poate fi în viitor.",
            )

    def test_weight_change_messages_use_stable_action_ids(self):
        self.assertEqual(
            set(WEIGHT_CHANGE_MESSAGE_SOURCE_TEXT),
            {"saved", "updated", "deleted"},
        )

        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(
                format_weight_change_message("saved", 2),
                "Weight saved. Affected days: 2.",
            )
            self.assertEqual(
                format_weight_change_message("updated", 3),
                "Weight updated. Affected days: 3.",
            )
            self.assertEqual(
                format_weight_change_message("deleted", 1),
                "Weight deleted. Affected days: 1.",
            )

        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(
                format_weight_change_message("saved", 2),
                "Greutate salvată. Zile afectate: 2.",
            )
            self.assertEqual(
                format_weight_change_message("updated", 3),
                "Greutate actualizată. Zile afectate: 3.",
            )
            self.assertEqual(
                format_weight_change_message("deleted", 1),
                "Greutate ștearsă. Zile afectate: 1.",
            )

    def test_weight_cards_translate_without_mutating_service_data(self):
        entries = pd.DataFrame(
            [
                {
                    "Data": "<script>alert(1)</script>",
                    "Greutate (kg)": "<img src=x onerror=alert(1)>",
                },
                *[
                    {
                        "Data": datetime.date(2026, 5, day),
                        "Greutate (kg)": 78.0 + day / 10,
                    }
                    for day in range(20, 26)
                ],
            ]
        )
        original_entries = entries.copy(deep=True)

        with patch.object(language.st, "session_state", {"language": "en"}):
            english_html, english_scrollable = build_weight_log_cards_html(entries)
        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_html, romanian_scrollable = build_weight_log_cards_html(entries)

        assert_frame_equal(entries, original_entries)
        self.assertTrue(english_scrollable)
        self.assertTrue(romanian_scrollable)
        self.assertIn("weight-history-list is-scrollable", english_html)
        self.assertIn(">Weight</span>", english_html)
        self.assertIn("<span>Weight</span>", english_html)
        self.assertIn(">Greutate</span>", romanian_html)
        self.assertIn("<span>Greutate</span>", romanian_html)
        self.assertNotIn("<script>", english_html)
        self.assertNotIn("<img", english_html)
        self.assertNotIn("<script>", romanian_html)
        self.assertNotIn("<img", romanian_html)

    def test_persistence_and_recalculation_flow_remains_unchanged(self):
        source = inspect.getsource(weight_journal_page.render_weight_journal_page)

        self.assertIn("WeightLog(", source)
        self.assertIn("user_id=user_id", source)
        self.assertIn("log_date=selected_date", source)
        self.assertIn("weight_kg=weight_kg", source)
        self.assertIn("int(selected_weight_log_id)", source)
        self.assertIn("edited_date", source)
        self.assertIn("edited_weight", source)
        self.assertIn("int(selected_delete_weight_log_id)", source)
        self.assertEqual(
            source.count("WeightLog.get_activity_day_weight_references(user_id)"),
            3,
        )
        self.assertEqual(
            source.count("recalculate_after_weight_change(before_references)"),
            3,
        )


if __name__ == "__main__":
    unittest.main()
