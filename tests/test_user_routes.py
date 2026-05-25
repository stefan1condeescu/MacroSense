import inspect
import unittest

from ui.pages import user_routes
from ui.pages.user_routes import USER_MENU_OPTIONS, build_user_profile_summary_html


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
        self.assertIn("apply_page_theme(get_user_page_theme(choice))", source)

    def test_user_routes_force_clean_rerun_when_page_changes(self):
        source = inspect.getsource(user_routes.render_user_routes)

        self.assertIn("USER_LAST_RENDERED_PAGE_KEY", source)
        self.assertIn("last_rendered_page is None", source)
        self.assertIn("elif last_rendered_page != choice", source)
        self.assertIn("_reset_journal_date_selectors()", source)
        self.assertIn("st.rerun()", source)

    def test_user_routes_reset_journal_date_selectors_on_page_change(self):
        source = inspect.getsource(user_routes)

        self.assertIn("FOOD_JOURNAL_DATE_KEY", source)
        self.assertIn("ACTIVITY_JOURNAL_DATE_KEY", source)
        self.assertIn("WEIGHT_LOG_ADD_DATE_KEY_PREFIX", source)
        self.assertIn("JOURNAL_DATE_SELECTOR_KEYS", source)
        self.assertIn("JOURNAL_DATE_SELECTOR_PREFIXES", source)

    def test_user_routes_exposes_read_only_profile_summary(self):
        source = inspect.getsource(user_routes.render_user_routes)
        profile_source = inspect.getsource(user_routes.load_user_profile_summary)

        self.assertIn("_render_sidebar_profile_summary()", source)
        self.assertIn("Profilul meu", inspect.getsource(user_routes._render_sidebar_profile_summary))
        self.assertIn("SELECT email, full_name, height_cm, age, gender, goal, registration_date", profile_source)
        self.assertNotIn("password_hash", profile_source)

    def test_user_profile_summary_html_escapes_profile_values(self):
        html = build_user_profile_summary_html(
            {
                "email": "user<test>@example.com",
                "full_name": "Ana <Demo>",
                "height_cm": 168,
                "age": 29,
                "gender": "F",
                "goal": "Crestere",
                "registration_date": "2026-05-01",
                "latest_weight_kg": 76.2,
                "latest_weight_date": "2026-05-24",
                "bmi": 27.0,
            }
        )

        self.assertIn("user&lt;test&gt;@example.com", html)
        self.assertIn("Ana &lt;Demo&gt;", html)
        self.assertIn("76.2 kg (24.05.2026)", html)
        self.assertNotIn("href=", html)
        self.assertNotIn("password", html.lower())


if __name__ == "__main__":
    unittest.main()
