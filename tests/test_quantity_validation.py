import unittest
from unittest.mock import patch

from ui import language
from ui.quantity_validation import (
    quantity_range_help,
    quantity_range_help_for_ui,
    validate_quantity_g,
    validate_quantity_g_for_ui,
)


class QuantityValidationTests(unittest.TestCase):
    def test_quantity_rejects_values_below_minimum(self):
        error = validate_quantity_g(0, "Cantitatea")

        self.assertEqual(error, "Cantitatea trebuie să fie cel puțin 1 g.")

    def test_quantity_rejects_values_above_maximum(self):
        error = validate_quantity_g(5000.1, "Cantitatea nouă")

        self.assertEqual(error, "Cantitatea nouă trebuie să fie cel mult 5000 g.")

    def test_quantity_rejects_non_numeric_values(self):
        error = validate_quantity_g("abc", "Cantitatea")

        self.assertEqual(error, "Cantitatea trebuie să fie un număr valid.")

    def test_quantity_accepts_valid_range_edges(self):
        self.assertIsNone(validate_quantity_g(1))
        self.assertIsNone(validate_quantity_g(5000))

    def test_quantity_help_documents_supported_range(self):
        self.assertEqual(quantity_range_help(), "Interval acceptat: 1-5000 g.")

    def test_bilingual_quantity_validation_keeps_the_same_numeric_rules(self):
        cases = (
            ("abc", "Quantity", "Quantity must be a valid number.", "Cantitate trebuie să fie un număr valid."),
            (0, "Quantity", "Quantity must be at least 1 g.", "Cantitate trebuie să fie cel puțin 1 g."),
            (5000.1, "New quantity", "New quantity must be at most 5000 g.", "Cantitatea nouă trebuie să fie cel mult 5000 g."),
        )

        for value, field_label, english_error, romanian_error in cases:
            with self.subTest(value=value, field_label=field_label):
                with patch.object(language.st, "session_state", {"language": "en"}):
                    self.assertEqual(
                        validate_quantity_g_for_ui(value, field_label),
                        english_error,
                    )
                with patch.object(language.st, "session_state", {"language": "ro"}):
                    self.assertEqual(
                        validate_quantity_g_for_ui(value, field_label),
                        romanian_error,
                    )

        for language_code in ("en", "ro"):
            with patch.object(language.st, "session_state", {"language": language_code}):
                self.assertIsNone(validate_quantity_g_for_ui(1))
                self.assertIsNone(validate_quantity_g_for_ui(5000))

    def test_quantity_help_uses_the_active_language(self):
        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(quantity_range_help_for_ui(), "Accepted range: 1-5000 g.")
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(quantity_range_help_for_ui(), "Interval acceptat: 1-5000 g.")


if __name__ == "__main__":
    unittest.main()
