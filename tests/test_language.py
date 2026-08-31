import unittest
from unittest.mock import patch

from ui import language


class LanguageTests(unittest.TestCase):
    def test_language_defaults_to_romanian_in_session(self):
        session_state = {}

        with patch.object(language.st, "session_state", session_state):
            self.assertEqual(language.initialize_language(), "ro")

        self.assertEqual(session_state[language.LANGUAGE_SESSION_KEY], "ro")

    def test_translate_uses_romanian_dictionary(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(language.translate("Food journal"), "Jurnal Alimentar")

    def test_translate_keeps_english_source_text_for_english(self):
        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(language.translate("Food journal"), "Food journal")

    def test_translate_falls_back_to_source_text_for_missing_translation(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(language.translate("Untranslated text"), "Untranslated text")

    def test_invalid_language_falls_back_to_romanian(self):
        session_state = {"language": "invalid"}

        with patch.object(language.st, "session_state", session_state):
            self.assertEqual(language.initialize_language(), "ro")

        self.assertEqual(session_state["language"], "ro")


if __name__ == "__main__":
    unittest.main()
