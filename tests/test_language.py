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

            app.button(key="language_ro").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["language"], "ro")
            self.assertEqual(app.caption[0].value, "Jurnal Alimentar")

            app.button(key="logout").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["language"], "ro")
            self.assertNotIn("role", app.session_state)
            self.assertNotIn("user_id", app.session_state)

            app.button(key="language_en").click().run()
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

    def test_change_language_resends_only_registered_selections(self):
        class RecordingState(dict):
            def __setitem__(self, key, value):
                writes.append((key, value))
                super().__setitem__(key, value)

        writes = []
        state = RecordingState(language="en", category="Forță", save=False, draft="Keep me")
        with patch.object(language.st, "session_state", state):
            self.assertEqual(language.translated_selection_key("category"), "category")
            language.translated_selection_key("missing_widget")
            language.translated_selection_key("category")
            language.change_language("ro")
        self.assertEqual(writes, [("category", "Forță"), ("language", "ro")])
        self.assertEqual(state["draft"], "Keep me")

    def test_change_language_rejects_unsupported_language(self):
        with patch.object(language.st, "session_state", {"language": "en"}):
            with self.assertRaises(ValueError):
                language.change_language("invalid")
            self.assertEqual(language.st.session_state["language"], "en")

    def test_replacing_old_selector_keeps_language_on_later_reruns(self):
        app = AppTest.from_string('''
import streamlit as st
from ui.language import render_language_selector
if st.session_state.get("legacy_selector", True):
    st.segmented_control("Language", ["en", "ro"], default="en", key="language")
else:
    render_language_selector()
st.button("Refresh", key="refresh")
''')
        with patch.dict(language.os.environ, {language.DEFAULT_LANGUAGE_ENV_VAR: "ro"}):
            app.run()
            app.session_state["legacy_selector"] = False
            app.run()
            for _ in range(3):
                app.button(key="refresh").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["language"], "en")

    def test_navigation_recovers_labels_without_changing_valid_ids(self):
        for pages in (
            {"food_catalog": {"label": "Food management"}, "activity_catalog": {"label": "Activity management"}},
            {"food_catalog": "Food management", "activity_catalog": "Activity management"},
        ):
            for selected, expected in (
                ("Activity management", "activity_catalog"),
                (language.ROMANIAN_TRANSLATIONS["Activity management"], "activity_catalog"),
                ("activity_catalog", "activity_catalog"),
                ("unknown", "food_catalog"),
            ):
                with self.subTest(selected=selected, pages=pages):
                    state = {"menu": selected}
                    with patch.object(language.st, "session_state", state):
                        language.normalize_navigation_selection("menu", pages)
                    self.assertEqual(state["menu"], expected)

    def test_switch_resends_new_labels_but_keeps_canonical_values(self):
        app = AppTest.from_string('''
import streamlit as st
from ui.language import render_language_selector, translate, translated_selection_key
render_language_selector()
pages = {"food_catalog": "Food management", "activity_catalog": "Activity management"}
st.selectbox("Admin menu", options=list(pages),
    format_func=lambda page: translate(pages[page]),
    key=translated_selection_key("admin_menu"))
st.radio("Main menu", options=list(pages),
    format_func=lambda page: translate(pages[page]),
    key=translated_selection_key("user_menu"))
st.selectbox("Category", options=["Cardio", "Forță"],
    format_func=lambda category: translate("Strength") if category == "Forță" else "Cardio",
    key=translated_selection_key("category"))
st.selectbox("Entry", options=[1, 7],
    format_func=lambda entry: f"{translate('Food journal')} {entry}",
    key=translated_selection_key("entry"))
st.button("Refresh", key="refresh")
''')
        app.session_state["language"] = "en"
        app.session_state["admin_menu"] = "activity_catalog"
        app.session_state["user_menu"] = "activity_catalog"
        app.session_state["category"] = "Forță"
        app.session_state["entry"] = 7
        # AppTest also calls format_func on its test thread, outside the app context.
        with patch(
            "streamlit.runtime.state.session_state_proxy.get_session_state",
            return_value=app.session_state,
        ):
            app.run()
            for language_code in ("ro", "en", "ro", "en"):
                app.button(key=f"language_{language_code}").click().run()
                self.assertFalse(app.exception)
                expected_label = (
                    language.ROMANIAN_TRANSLATIONS["Activity management"]
                    if language_code == "ro" else "Activity management"
                )
                for widget in (app.selectbox(key="admin_menu"), app.radio(key="user_menu")):
                    self.assertEqual(widget.value, "activity_catalog")
                    # Verify the browser receives a refreshed label, not just the Python ID.
                    self.assertTrue(widget.proto.set_value)
                    self.assertEqual(widget.proto.raw_value, expected_label)
                self.assertEqual(app.selectbox(key="category").value, "Forță")
                self.assertEqual(app.selectbox(key="entry").value, 7)
                app.button(key="refresh").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.selectbox(key="admin_menu").value, "activity_catalog")
                self.assertEqual(app.radio(key="user_menu").value, "activity_catalog")


if __name__ == "__main__":
    unittest.main()
