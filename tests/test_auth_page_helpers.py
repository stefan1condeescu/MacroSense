import inspect
import unittest

from ui.pages import auth_page


class AuthPageHelperTests(unittest.TestCase):
    def test_login_form_is_rendered_in_clearable_placeholder(self):
        source = inspect.getsource(auth_page.render_auth_page)

        self.assertIn("login_slot = st.empty()", source)
        self.assertIn("with login_slot.container():", source)

    def test_successful_login_clears_form_before_rerun(self):
        source = inspect.getsource(auth_page.render_auth_page)

        self.assertGreaterEqual(source.count("login_slot.empty()"), 2)
        self.assertIn("st.session_state['role'] = 'admin'", source)
        self.assertIn("st.session_state['role'] = 'user'", source)


if __name__ == "__main__":
    unittest.main()
