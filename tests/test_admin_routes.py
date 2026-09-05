import ast
import inspect
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from ui import language
from ui.pages import admin_routes
from ui.pages.admin_routes import (
    ADMIN_MENU_OPTIONS,
    ADMIN_PAGES,
    build_admin_identity_html,
)
from ui.translations_ro import ROMANIAN_TRANSLATIONS


class AdminRoutesTests(unittest.TestCase):
    def test_admin_routes_recover_stale_label_and_survive_language_roundtrip(self):
        app = AppTest.from_string('''
import streamlit as st
from ui.language import render_language_selector
from ui.pages.admin_routes import render_admin_routes
render_language_selector()
render_admin_routes()
st.button("Refresh", key="refresh")
''')
        app.session_state["language"] = "en"
        app.session_state["admin_main_menu"] = "Activity management"
        rendered_pages = []
        with (
            patch.dict(ADMIN_PAGES["activity_catalog"], {
                "render": lambda: rendered_pages.append("activity_catalog"),
            }),
            patch.dict(ADMIN_PAGES["food_catalog"], {
                "render": lambda: rendered_pages.append("food_catalog"),
            }),
            patch("streamlit.runtime.state.session_state_proxy.get_session_state",
                  return_value=app.session_state),
        ):
            app.run()
            for language_code in ("ro", "en"):
                self.assertFalse(app.exception)
                self.assertEqual(app.selectbox(key="admin_main_menu").value, "activity_catalog")
                app.button(key=f"language_{language_code}").click().run()
                app.button(key="refresh").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["admin_main_menu"], "activity_catalog")
            self.assertEqual(rendered_pages, ["activity_catalog"] * 5)

    def test_admin_route_english_source_text_has_romanian_translations(self):
        source_tree = ast.parse(inspect.getsource(admin_routes))
        source_keys = {
            node.args[0].value
            for node in ast.walk(source_tree)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "translate"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            )
        }

        for source_key in source_keys:
            with self.subTest(source_key=source_key):
                self.assertIn(source_key, ROMANIAN_TRANSLATIONS)

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

    def test_admin_identity_label_uses_the_active_session_language(self):
        with patch.object(language.st, "session_state", {"language": "ro"}):
            romanian_html = build_admin_identity_html("admin@test.com")
        with patch.object(language.st, "session_state", {"language": "en"}):
            english_html = build_admin_identity_html("admin@test.com")

        self.assertIn("Autentificat ca:", romanian_html)
        self.assertIn("Logged in as:", english_html)

    def test_admin_identity_email_is_escaped(self):
        html = build_admin_identity_html("<admin>@test.com")

        self.assertIn("&lt;admin&gt;@test.com", html)

    def test_admin_logout_preserves_selected_language(self):
        source = inspect.getsource(admin_routes.render_admin_routes)

        self.assertIn("clear_session_preserving_language()", source)
        self.assertNotIn("st.session_state.clear()", source)


if __name__ == "__main__":
    unittest.main()
