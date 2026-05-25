import unittest

from ui.pages.admin_routes import build_admin_identity_html


class AdminRoutesTests(unittest.TestCase):
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
