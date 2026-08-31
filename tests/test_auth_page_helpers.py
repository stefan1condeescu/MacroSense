import inspect
import unittest
from unittest.mock import patch

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

    def test_auth_navigation_formats_ids_for_display(self):
        source = inspect.getsource(auth_page.render_auth_page)

        self.assertIn("options=list(AUTH_PAGES)", source)
        self.assertIn("format_func=display_auth_page_name", source)

    def test_legacy_auth_labels_are_migrated_to_stable_ids(self):
        self.assertEqual(auth_page.normalize_auth_page_id("Autentificare"), "login")
        self.assertEqual(auth_page.normalize_auth_page_id("Creare Cont"), "register")

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
        self.assertIn("Bine ai revenit", source)
        self.assertIn("Intră în MacroSense pentru a continua monitorizarea.", source)
        self.assertIn("st.columns([0.2, 1, 0.2])", source)
        self.assertIn('"Intră în cont"', source)
        self.assertIn('width="stretch"', source)

    def test_successful_login_clears_form_before_rerun(self):
        source = inspect.getsource(auth_page.render_auth_page)

        self.assertGreaterEqual(source.count("login_slot.empty()"), 2)
        self.assertIn("st.session_state['role'] = 'admin'", source)
        self.assertIn("st.session_state['role'] = 'user'", source)

    def test_successful_registration_redirects_to_login_page(self):
        source = inspect.getsource(auth_page.render_auth_page)

        self.assertIn("key=AUTH_NAVIGATION_KEY", source)
        self.assertIn("st.session_state[AUTH_REGISTER_SUCCESS_KEY]", source)
        self.assertIn("st.session_state[AUTH_REDIRECT_TO_LOGIN_KEY] = True", source)
        self.assertIn("st.session_state[AUTH_NAVIGATION_KEY] = AUTH_LOGIN_PAGE_ID", source)


if __name__ == "__main__":
    unittest.main()
