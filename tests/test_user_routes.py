import inspect
import unittest

from ui.pages import user_routes
from ui.pages.user_routes import USER_MENU_OPTIONS


class UserRoutesTests(unittest.TestCase):
    def test_user_menu_keeps_home_visible_as_first_option(self):
        self.assertEqual(USER_MENU_OPTIONS[0], "Acasă")

    def test_user_menu_options_are_unique(self):
        self.assertEqual(len(USER_MENU_OPTIONS), len(set(USER_MENU_OPTIONS)))

    def test_user_menu_exposes_what_if_before_catalogs(self):
        self.assertIn("Simulator What-if", USER_MENU_OPTIONS)
        self.assertLess(
            USER_MENU_OPTIONS.index("Simulator What-if"),
            USER_MENU_OPTIONS.index("Catalog Alimente"),
        )

    def test_user_routes_render_active_page_in_placeholder(self):
        source = inspect.getsource(user_routes.render_user_routes)

        self.assertIn("st.empty()", source)
        self.assertIn("page_slot.container()", source)

    def test_user_routes_force_clean_rerun_when_page_changes(self):
        source = inspect.getsource(user_routes.render_user_routes)

        self.assertIn("USER_LAST_RENDERED_PAGE_KEY", source)
        self.assertIn("last_rendered_page is None", source)
        self.assertIn("elif last_rendered_page != choice", source)
        self.assertIn("st.rerun()", source)


if __name__ == "__main__":
    unittest.main()
