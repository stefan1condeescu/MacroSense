import unittest
from pathlib import Path


class AppRoutingTests(unittest.TestCase):
    def setUp(self):
        self.app_source = Path("app.py").read_text(encoding="utf-8")

    def test_app_renders_active_role_inside_placeholder(self):
        self.assertIn("route_slot = st.empty()", self.app_source)
        self.assertIn("with route_slot.container():", self.app_source)

    def test_app_forces_clean_rerun_when_auth_role_changes(self):
        self.assertIn("APP_LAST_RENDERED_ROLE_KEY", self.app_source)
        self.assertIn("current_role = st.session_state[\"role\"]", self.app_source)
        self.assertIn("st.session_state[APP_LAST_RENDERED_ROLE_KEY] = current_role", self.app_source)
        self.assertIn("st.rerun()", self.app_source)

    def test_app_initializes_language_after_page_configuration(self):
        self.assertIn("from ui.language import initialize_language", self.app_source)
        self.assertIn("initialize_language()", self.app_source)
        self.assertLess(
            self.app_source.index("configure_page()"),
            self.app_source.index("initialize_language()"),
        )


if __name__ == "__main__":
    unittest.main()
