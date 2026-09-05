import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from ui import language


class LanguageTests(unittest.TestCase):
    def test_language_defaults_to_english_in_session(self):
        session_state = {}

        with (
            patch.dict(language.os.environ, {}, clear=True),
            patch.object(language.st, "session_state", session_state),
        ):
            self.assertEqual(language.initialize_language(), "en")

        self.assertEqual(session_state[language.LANGUAGE_SESSION_KEY], "en")

    def test_language_can_default_to_romanian_from_local_configuration(self):
        session_state = {}

        with (
            patch.dict(
                language.os.environ,
                {language.DEFAULT_LANGUAGE_ENV_VAR: "ro"},
                clear=True,
            ),
            patch.object(language.st, "session_state", session_state),
        ):
            self.assertEqual(language.initialize_language(), "ro")

        self.assertEqual(session_state[language.LANGUAGE_SESSION_KEY], "ro")

    def test_invalid_configured_default_falls_back_to_english(self):
        with patch.dict(
            language.os.environ,
            {language.DEFAULT_LANGUAGE_ENV_VAR: "unsupported"},
            clear=True,
        ):
            self.assertEqual(language.get_configured_default_language(), "en")

    def test_translate_uses_romanian_dictionary(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(language.translate("Food journal"), "Jurnal Alimentar")

    def test_translate_keeps_english_source_text_for_english(self):
        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(language.translate("Food journal"), "Food journal")

    def test_translate_falls_back_to_source_text_for_missing_translation(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(language.translate("Untranslated text"), "Untranslated text")

    def test_translate_formats_dynamic_values_in_romanian(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
            message = language.translate(
                "Height must be between {minimum:.0f} and {maximum:.0f} cm.",
                minimum=100,
                maximum=250,
            )

        self.assertEqual(message, "Înălțimea trebuie să fie între 100 și 250 cm.")

    def test_translate_formats_dynamic_values_in_english(self):
        with patch.object(language.st, "session_state", {"language": "en"}):
            message = language.translate(
                "Height must be between {minimum:.0f} and {maximum:.0f} cm.",
                minimum=100,
                maximum=250,
            )

        self.assertEqual(message, "Height must be between 100 and 250 cm.")

    def test_invalid_session_language_falls_back_to_configured_default(self):
        session_state = {"language": "invalid"}

        with (
            patch.dict(
                language.os.environ,
                {language.DEFAULT_LANGUAGE_ENV_VAR: "ro"},
                clear=True,
            ),
            patch.object(language.st, "session_state", session_state),
        ):
            self.assertEqual(language.initialize_language(), "ro")

        self.assertEqual(session_state["language"], "ro")

    def test_language_names_are_recognizable_in_either_language(self):
        for language_code in language.SUPPORTED_LANGUAGES:
            with patch.object(language.st, "session_state", {"language": language_code}):
                self.assertEqual(language.display_language_name("en"), "English")
                self.assertEqual(language.display_language_name("ro"), "Română")
        self.assertEqual(language.display_language_name("future"), "future")

    def test_language_switch_rerenders_and_logout_preserves_selection(self):
        app = AppTest.from_string('''
import streamlit as st
from ui.language import (
    clear_session_preserving_language,
    render_language_selector,
    translate,
)

render_language_selector()
st.caption(translate("Food journal"))
if st.session_state.get("role") and st.button("Log out", key="logout"):
    clear_session_preserving_language()
    st.rerun()
''')
        app.session_state["role"] = "user"
        app.session_state["user_id"] = 7

        with patch.dict(language.os.environ, {language.DEFAULT_LANGUAGE_ENV_VAR: "en"}):
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(app.caption[0].value, "Food journal")

            app.button_group(key="language").set_value("ro").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["language"], "ro")
            self.assertEqual(app.caption[0].value, "Jurnal Alimentar")

            app.button(key="logout").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["language"], "ro")
            self.assertNotIn("role", app.session_state)
            self.assertNotIn("user_id", app.session_state)

            app.button_group(key="language").set_value("en").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.caption[0].value, "Food journal")

    def test_clear_session_preserves_only_the_selected_language(self):
        session_state = {
            "language": "ro",
            "role": "user",
            "user_id": 7,
            "user_main_menu": "dashboard",
        }

        with patch.object(language.st, "session_state", session_state):
            language.clear_session_preserving_language()

        self.assertEqual(session_state, {"language": "ro"})


if __name__ == "__main__":
    unittest.main()
