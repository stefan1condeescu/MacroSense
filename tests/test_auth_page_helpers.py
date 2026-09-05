import inspect
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from ui import language
from ui.pages import auth_page


class AuthPageHelperTests(unittest.TestCase):
    def test_auth_navigation_uses_stable_page_ids(self):
        self.assertEqual(tuple(auth_page.AUTH_PAGES), ("login", "register"))
        self.assertEqual(auth_page.AUTH_PAGES["login"], "Login")
        self.assertEqual(auth_page.AUTH_PAGES["register"], "Create account")

    def test_auth_page_labels_use_the_active_session_language(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(auth_page.display_auth_page_name("login"), "Autentificare")
        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(auth_page.display_auth_page_name("login"), "Login")

    def test_auth_goal_labels_translate_without_changing_stored_values(self):
        self.assertEqual(set(auth_page.AUTH_GOAL_LABELS), set(auth_page.User.VALID_GOALS))

        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(auth_page.display_auth_goal_name("Slabire"), "Slăbire")
            self.assertEqual(auth_page.display_auth_goal_name("Mentinere"), "Menținere")
            self.assertEqual(auth_page.display_auth_goal_name("Crestere"), "Creștere")
        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(auth_page.display_auth_goal_name("Slabire"), "Weight loss")
            self.assertEqual(auth_page.display_auth_goal_name("Mentinere"), "Maintenance")
            self.assertEqual(auth_page.display_auth_goal_name("Crestere"), "Muscle gain")

    def test_registration_errors_use_the_active_session_language(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(
                auth_page.get_registration_error_message("invalid_height"),
                "Înălțimea trebuie să fie între 100 și 250 cm.",
            )
        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(
                auth_page.get_registration_error_message("invalid_height"),
                "Height must be between 100 and 250 cm.",
            )

    def test_auth_navigation_formats_ids_for_display(self):
        source = inspect.getsource(auth_page.render_auth_page)

        self.assertIn("options=list(AUTH_PAGES)", source)
        self.assertIn("format_func=display_auth_page_name", source)

    def test_legacy_auth_labels_are_migrated_to_stable_ids(self):
        self.assertEqual(auth_page.normalize_auth_page_id("Autentificare"), "login")
        self.assertEqual(auth_page.normalize_auth_page_id("Creare Cont"), "register")
        self.assertEqual(auth_page.normalize_auth_page_id("Login"), "login")
        self.assertEqual(auth_page.normalize_auth_page_id("Create account"), "register")

    def test_unknown_auth_selection_falls_back_to_login(self):
        self.assertEqual(auth_page.normalize_auth_page_id("unknown"), "login")

    def test_login_form_is_rendered_in_clearable_placeholder(self):
        source = inspect.getsource(auth_page.render_auth_page)

        self.assertIn("login_slot = st.empty()", source)
        self.assertIn("with login_slot.container():", source)

    def test_login_form_uses_clean_centered_layout(self):
        source = inspect.getsource(auth_page.render_auth_page)

        self.assertIn("auth-login-panel", source)
        self.assertIn("auth-login-copy", source)
        self.assertIn("auth-login-note", source)
        self.assertIn('translate("Welcome back")', source)
        self.assertIn('translate("Log in to MacroSense to continue tracking.")', source)
        self.assertIn("st.columns([0.2, 1, 0.2])", source)
        self.assertIn('translate("Log in")', source)
        self.assertIn('width="stretch"', source)

    def test_successful_login_clears_form_before_rerun(self):
        source = inspect.getsource(auth_page.render_auth_page)

        self.assertGreaterEqual(source.count("login_slot.empty()"), 2)
        self.assertIn("st.session_state['role'] = 'admin'", source)
        self.assertIn("st.session_state['role'] = 'user'", source)

    def test_successful_registration_redirects_to_login_page(self):
        source = inspect.getsource(auth_page.render_auth_page)

        self.assertIn("key=translated_selection_key(AUTH_NAVIGATION_KEY)", source)
        self.assertIn("st.session_state[AUTH_REGISTER_SUCCESS_KEY]", source)
        self.assertIn("st.session_state[AUTH_REDIRECT_TO_LOGIN_KEY] = True", source)
        self.assertIn("st.session_state[AUTH_NAVIGATION_KEY] = AUTH_LOGIN_PAGE_ID", source)

    def test_auth_inputs_have_stable_keys_in_reactive_containers(self):
        source = inspect.getsource(auth_page.render_auth_page)

        self.assertNotIn("st.form(", source)
        self.assertNotIn("st.form_submit_button(", source)
        self.assertIn('st.container(border=True, key="register_form")', source)
        self.assertIn('st.container(border=True, key="login_form")', source)
        for key in (
            "auth_register_email", "auth_register_password", "auth_register_full_name",
            "auth_register_height", "auth_register_weight", "auth_register_age",
            "auth_register_gender", "auth_register_goal", "auth_register_submit",
            "auth_login_email", "auth_login_password", "auth_login_submit",
        ):
            with self.subTest(key=key):
                self.assertIn(f'"{key}"', source)

    def test_reactive_registration_only_saves_when_register_is_clicked(self):
        app = AppTest.from_string('''
from ui.pages.auth_page import render_auth_page
render_auth_page()
''')
        app.session_state["language"] = "en"
        app.session_state[auth_page.AUTH_NAVIGATION_KEY] = "register"

        with (
            patch("streamlit.runtime.state.session_state_proxy.get_session_state", return_value=app.session_state),
            patch.object(auth_page.User, "register", return_value=True) as register,
        ):
            app.run()
            self.assertFalse(app.exception)
            app.text_input(key="auth_register_email").input("draft@example.test")
            app.text_input(key="auth_register_password").input("test-password")
            app.text_input(key="auth_register_full_name").input("Draft User")
            app.number_input(key="auth_register_weight").set_value(72.3).run()
            self.assertFalse(app.exception)
            register.assert_not_called()

            app.button(key="auth_register_submit").click().run()
            self.assertFalse(app.exception)
            register.assert_called_once_with("test-password", 72.3)
            self.assertEqual(app.session_state[auth_page.AUTH_NAVIGATION_KEY], "login")

    def test_registration_draft_survives_language_roundtrip_without_submitting(self):
        app = AppTest.from_string('''
from ui.language import render_language_selector
from ui.pages.auth_page import render_auth_page
render_language_selector()
render_auth_page()
''')
        app.session_state["language"] = "en"
        app.session_state[auth_page.AUTH_NAVIGATION_KEY] = "register"

        # AppTest also invokes format_func outside the script thread when serializing widgets.
        with (
            patch("streamlit.runtime.state.session_state_proxy.get_session_state", return_value=app.session_state),
            patch.object(auth_page.User, "register") as register,
        ):
            app.run()
            self.assertFalse(app.exception)
            app.text_input(key="auth_register_email").input("draft@example.test")
            app.text_input(key="auth_register_password").input("test-password")
            app.text_input(key="auth_register_full_name").input("Draft User")
            app.number_input(key="auth_register_height").set_value(181.2)
            app.number_input(key="auth_register_weight").set_value(72.3)
            app.number_input(key="auth_register_age").set_value(32)
            app.selectbox(key="auth_register_gender").select("F")
            app.selectbox(key="auth_register_goal").select("Crestere").run()

            for language_code in ("ro", "en"):
                with self.subTest(language=language_code):
                    app.button(key=f"language_{language_code}").click().run()
                    self.assertFalse(app.exception)
                    self.assertEqual(app.session_state["language"], language_code)
                    self.assertEqual(app.session_state[auth_page.AUTH_NAVIGATION_KEY], "register")
                    self.assertEqual(app.text_input(key="auth_register_email").value, "draft@example.test")
                    self.assertEqual(app.text_input(key="auth_register_password").value, "test-password")
                    self.assertEqual(app.text_input(key="auth_register_full_name").value, "Draft User")
                    self.assertEqual(app.number_input(key="auth_register_height").value, 181.2)
                    self.assertEqual(app.number_input(key="auth_register_weight").value, 72.3)
                    self.assertEqual(app.number_input(key="auth_register_age").value, 32)
                    self.assertEqual(app.selectbox(key="auth_register_gender").value, "F")
                    self.assertEqual(app.selectbox(key="auth_register_goal").value, "Crestere")
                    register.assert_not_called()

    def test_reactive_login_only_authenticates_when_log_in_is_clicked(self):
        app = AppTest.from_string('''
from ui.language import render_language_selector
from ui.pages.auth_page import render_auth_page
render_language_selector()
render_auth_page()
''')
        app.session_state["language"] = "en"

        with (
            patch("streamlit.runtime.state.session_state_proxy.get_session_state", return_value=app.session_state),
            patch.object(auth_page.Admin, "authenticate", return_value=False) as admin_auth,
            patch.object(auth_page.User, "authenticate", return_value=False) as user_auth,
        ):
            app.run()
            self.assertFalse(app.exception)
            app.text_input(key="auth_login_email").input("draft@example.test")
            app.text_input(key="auth_login_password").input("test-password").run()
            self.assertFalse(app.exception)
            admin_auth.assert_not_called()
            user_auth.assert_not_called()

            for language_code in ("ro", "en"):
                app.button(key=f"language_{language_code}").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.text_input(key="auth_login_email").value, "draft@example.test")
                self.assertEqual(app.text_input(key="auth_login_password").value, "test-password")
                admin_auth.assert_not_called()
                user_auth.assert_not_called()

            app.button(key="auth_login_submit").click().run()
            self.assertFalse(app.exception)
            admin_auth.assert_called_once_with("test-password")
            user_auth.assert_called_once_with("test-password")


if __name__ == "__main__":
    unittest.main()
