from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ui import page_theme
from ui.pages.user_routes import USER_MENU_OPTIONS


class PageThemeTests(unittest.TestCase):
    def test_user_menu_options_map_to_known_themes(self):
        for menu_choice in USER_MENU_OPTIONS:
            with self.subTest(menu_choice=menu_choice):
                theme_key = page_theme.get_user_page_theme(menu_choice)
                self.assertIn(theme_key, page_theme.PAGE_THEME_CLASSES)

    def test_admin_activity_catalog_uses_activity_theme(self):
        self.assertEqual(
            page_theme.get_admin_page_theme("Gestiune Activități"),
            "catalog_activity",
        )

    def test_apply_page_theme_writes_safe_marker_class(self):
        calls = []
        fake_streamlit = SimpleNamespace(
            markdown=lambda body, unsafe_allow_html=False: calls.append(
                (body, unsafe_allow_html)
            )
        )

        with patch.object(page_theme, "st", fake_streamlit):
            page_theme.apply_page_theme("food")

        self.assertEqual(len(calls), 1)
        self.assertIn("page-theme-marker", calls[0][0])
        self.assertIn("page-theme-food", calls[0][0])
        self.assertTrue(calls[0][1])

    def test_css_defines_consistent_domain_colors(self):
        css_text = Path("assets/style.css").read_text(encoding="utf-8")

        self.assertIn("--ms-food-accent: #16a34a", css_text)
        self.assertIn("--ms-meal-accent: #0d9488", css_text)
        self.assertIn("--ms-activity-accent: #6d5dfc", css_text)
        self.assertIn("--ms-weight-accent: #0284c7", css_text)
        self.assertIn(".stApp:has(.page-theme-food)", css_text)
        self.assertIn(".stApp:has(.page-theme-activity)", css_text)
        self.assertIn(".stApp:has(.page-theme-weight)", css_text)

    def test_css_colors_activity_cards_with_activity_accent(self):
        css_text = Path("assets/style.css").read_text(encoding="utf-8")

        self.assertIn(".log-entry-card.activity", css_text)
        self.assertIn("border-left-color: var(--ms-activity-accent)", css_text)

    def test_css_colors_custom_meals_with_meal_accent(self):
        css_text = Path("assets/style.css").read_text(encoding="utf-8")

        self.assertIn(".custom-meal-card.active", css_text)
        self.assertIn(".custom-meal-summary-grid", css_text)
        self.assertIn(".custom-meal-summary-card", css_text)
        self.assertIn("border-left: 4px solid var(--ms-meal-accent)", css_text)
        self.assertIn(".log-entry-card.custom-meal", css_text)
        self.assertIn(".log-entry-badge.custom-meal", css_text)

    def test_css_makes_weight_history_scrollable_when_needed(self):
        css_text = Path("assets/style.css").read_text(encoding="utf-8")

        self.assertIn(".weight-history-list.is-scrollable", css_text)
        self.assertIn("max-height: 680px", css_text)
        self.assertIn("overflow-y: auto", css_text)

    def test_css_makes_usda_preview_metrics_compact(self):
        css_text = Path("assets/style.css").read_text(encoding="utf-8")

        self.assertIn(".usda-preview-metric strong", css_text)
        self.assertIn("font-size: 1.85rem", css_text)
        self.assertIn("white-space: nowrap", css_text)

    def test_css_styles_auth_login_form_cleanly(self):
        css_text = Path("assets/style.css").read_text(encoding="utf-8")

        self.assertIn(".auth-login-panel", css_text)
        self.assertIn(".auth-login-copy", css_text)
        self.assertIn(".auth-login-note", css_text)
        self.assertIn("text-align: center", css_text)
        self.assertIn('.stApp:has(.auth-login-panel) div[data-testid="stForm"]', css_text)
        self.assertIn("border-radius: 12px", css_text)
        self.assertIn("box-shadow: 0 16px 34px", css_text)


if __name__ == "__main__":
    unittest.main()
