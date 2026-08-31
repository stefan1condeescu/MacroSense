import unittest
from unittest.mock import patch

from ui import language
from ui.pages import admin_routes
from ui.pages.admin_routes import ADMIN_MENU_OPTIONS, ADMIN_PAGES, build_admin_identity_html


class AdminRoutesTests(unittest.TestCase):
    def test_admin_menu_uses_stable_page_ids(self):
        self.assertEqual(ADMIN_MENU_OPTIONS, ("food_catalog", "activity_catalog"))
        self.assertEqual(ADMIN_PAGES["food_catalog"]["label"], "Food management")

    def test_admin_page_labels_use_the_active_session_language(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(admin_routes.display_admin_page_name("food_catalog"), "Gestiune Alimente")
        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(admin_routes.display_admin_page_name("food_catalog"), "Food management")

    def test_admin_page_registry_dispatches_by_stable_id(self):
        rendered_pages = []

        with patch.dict(
            ADMIN_PAGES["activity_catalog"],
            {"render": lambda: rendered_pages.append("activity_catalog")},
        ):
            admin_routes._render_selected_admin_page("activity_catalog")

        self.assertEqual(rendered_pages, ["activity_catalog"])

    def test_admin_identity_email_is_plain_text_not_link(self):
        html = build_admin_identity_html("admin@test.com")

        self.assertIn("admin@test.com", html)
        self.assertNotIn("<a", html.lower())
        self.assertNotIn("mailto:", html.lower())

    def test_admin_identity_email_is_escaped(self):
        html = build_admin_identity_html("<admin>@test.com")

        self.assertIn("&lt;admin&gt;@test.com", html)


if __name__ == "__main__":
    unittest.main()
