import inspect
import unittest

from ui.pages import auth_page


class AuthPageHelperTests(unittest.TestCase):
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
        self.assertIn('st.session_state[AUTH_NAVIGATION_KEY] = "Autentificare"', source)


if __name__ == "__main__":
    unittest.main()
