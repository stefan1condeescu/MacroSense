import inspect
import unittest
from unittest.mock import patch

from ui import language
from ui.pages import user_routes
from ui.pages.user_routes import (
    USER_MENU_OPTIONS,
    USER_PAGES,
    build_user_profile_summary_html,
)


class UserRoutesTests(unittest.TestCase):
    def test_user_menu_keeps_home_visible_as_first_option(self):
        self.assertEqual(USER_MENU_OPTIONS[0], "dashboard")

    def test_user_menu_options_are_unique(self):
        self.assertEqual(len(USER_MENU_OPTIONS), len(set(USER_MENU_OPTIONS)))

    def test_user_menu_exposes_what_if_before_catalogs(self):
        self.assertIn("what_if", USER_MENU_OPTIONS)
        self.assertLess(
            USER_MENU_OPTIONS.index("what_if"),
            USER_MENU_OPTIONS.index("food_catalog"),
        )

    def test_user_pages_use_english_source_labels(self):
        self.assertEqual(USER_PAGES["dashboard"]["label"], "Home")
        self.assertEqual(USER_PAGES["food_journal"]["label"], "Food journal")

    def test_display_page_name_uses_the_active_session_language(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(user_routes.display_page_name("food_journal"), "Jurnal Alimentar")
        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(user_routes.display_page_name("food_journal"), "Food journal")

    def test_display_page_name_keeps_unknown_id_visible(self):
        self.assertEqual(user_routes.display_page_name("unknown_page"), "unknown_page")

    def test_user_routes_render_active_page_in_placeholder(self):
        source = inspect.getsource(user_routes.render_user_routes)

        self.assertIn("st.empty()", source)
        self.assertIn("page_slot.container()", source)
        self.assertIn("options=list(USER_PAGES)", source)
        self.assertIn("format_func=display_page_name", source)
        self.assertIn("apply_page_theme(get_user_page_theme(selected_page))", source)

    def test_user_page_registry_dispatches_by_stable_id(self):
        rendered_pages = []

        with patch.dict(
            USER_PAGES["food_journal"],
            {"render": lambda: rendered_pages.append("food_journal")},
        ):
            user_routes._render_selected_user_page("food_journal")

        self.assertEqual(rendered_pages, ["food_journal"])

    def test_user_routes_force_clean_rerun_when_page_changes(self):
        source = inspect.getsource(user_routes.render_user_routes)

        self.assertIn("USER_LAST_RENDERED_PAGE_KEY", source)
        self.assertIn("last_rendered_page is None", source)
        self.assertIn("elif last_rendered_page != selected_page", source)
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
        self.assertIn(
            'translate("My profile")',
            inspect.getsource(user_routes._render_sidebar_profile_summary),
        )
        self.assertIn("SELECT email, full_name, height_cm, age, gender, goal, registration_date", profile_source)
        self.assertNotIn("password_hash", profile_source)

    def test_user_sidebar_shell_uses_english_source_text(self):
        source = inspect.getsource(user_routes.render_user_routes)

        self.assertIn('"Hello, {name}!"', source)
        self.assertIn('translate("Log out")', source)

    def test_user_logout_preserves_selected_language(self):
        source = inspect.getsource(user_routes.render_user_routes)

        self.assertIn("clear_session_preserving_language()", source)
        self.assertNotIn("st.session_state.clear()", source)

    def test_user_profile_summary_uses_the_active_language(self):
        profile = {
            "email": "ana@example.com",
            "full_name": "Ana Demo",
            "height_cm": 168,
            "age": 29,
            "gender": "F",
            "goal": "Crestere",
            "registration_date": "2026-05-01",
            "latest_weight_kg": 76.2,
            "latest_weight_date": "2026-05-24",
            "bmi": 27.0,
        }

        with patch.object(language.st, "session_state", {"language": "en"}):
            english_html = build_user_profile_summary_html(profile)
        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_html = build_user_profile_summary_html(profile)

        self.assertIn("<span>Name</span>", english_html)
        self.assertIn("<span>Registration</span>", english_html)
        self.assertIn("<span>Age</span><strong>29 years</strong>", english_html)
        self.assertIn("<span>Goal</span><strong>Muscle gain</strong>", english_html)
        self.assertIn("<span>Nume</span>", romanian_html)
        self.assertIn("<span>Înregistrare</span>", romanian_html)
        self.assertIn("<span>Vârstă</span><strong>29 ani</strong>", romanian_html)
        self.assertIn("<span>Obiectiv</span><strong>Creștere</strong>", romanian_html)

    def test_user_profile_goal_translates_canonical_stored_values(self):
        expected_labels = {
            "Slabire": ("Weight loss", "Slăbire"),
            "Mentinere": ("Maintenance", "Menținere"),
            "Crestere": ("Muscle gain", "Creștere"),
        }

        for stored_goal, (english_label, romanian_label) in expected_labels.items():
            with self.subTest(stored_goal=stored_goal):
                with patch.object(language.st, "session_state", {"language": "en"}):
                    self.assertEqual(
                        user_routes._format_profile_goal(stored_goal),
                        english_label,
                    )
                with patch.object(language.st, "session_state", {"language": "ro"}):
                    self.assertEqual(
                        user_routes._format_profile_goal(stored_goal),
                        romanian_label,
                    )

    def test_user_profile_goal_keeps_unknown_stored_value_visible(self):
        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(user_routes._format_profile_goal("FutureGoal"), "FutureGoal")

    def test_user_profile_load_error_uses_the_active_language(self):
        with (
            patch.object(
                user_routes.st,
                "session_state",
                {"language": "en", "user_id": 7},
            ),
            patch.object(user_routes.st.sidebar, "expander") as expander,
            patch.object(user_routes, "load_user_profile_summary", return_value=None),
            patch.object(user_routes.st, "caption") as caption,
        ):
            expander.return_value.__enter__.return_value = None
            user_routes._render_sidebar_profile_summary()

        expander.assert_called_once_with("My profile")
        caption.assert_called_once_with("The profile cannot be loaded right now.")

    def test_user_profile_summary_html_escapes_profile_values(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
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
