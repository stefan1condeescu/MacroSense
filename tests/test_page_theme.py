from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ui import page_theme
from ui.pages.admin_routes import ADMIN_MENU_OPTIONS
from ui.pages.user_routes import USER_MENU_OPTIONS


class PageThemeTests(unittest.TestCase):
    def test_user_page_ids_map_to_known_themes(self):
        for page_id in USER_MENU_OPTIONS:
            with self.subTest(page_id=page_id):
                theme_key = page_theme.get_user_page_theme(page_id)
                self.assertIn(theme_key, page_theme.PAGE_THEME_CLASSES)

    def test_every_user_page_id_has_an_explicit_theme_mapping(self):
        self.assertEqual(set(USER_MENU_OPTIONS), set(page_theme.USER_PAGE_THEMES))

    def test_user_page_theme_does_not_depend_on_display_language(self):
        self.assertEqual(page_theme.get_user_page_theme("food_journal"), "food")
        self.assertEqual(page_theme.get_user_page_theme("activity_catalog"), "activity")

    def test_every_admin_page_id_has_an_explicit_theme_mapping(self):
        self.assertEqual(set(ADMIN_MENU_OPTIONS), set(page_theme.ADMIN_PAGE_THEMES))

    def test_admin_page_ids_map_to_known_themes(self):
        for page_id in ADMIN_MENU_OPTIONS:
            with self.subTest(page_id=page_id):
                theme_key = page_theme.get_admin_page_theme(page_id)
                self.assertIn(theme_key, page_theme.PAGE_THEME_CLASSES)

    def test_admin_activity_catalog_uses_activity_theme(self):
        self.assertEqual(
            page_theme.get_admin_page_theme("activity_catalog"),
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
        self.assertIn('.stApp:has(.auth-login-panel) .st-key-login_form', css_text)
        self.assertIn("border-radius: 12px", css_text)
        self.assertIn("box-shadow: 0 16px 34px", css_text)

    def test_css_defines_light_and_dark_semantic_colors(self):
        """Check the stylesheet contract, not browser-rendered contrast."""
        css_text = Path("assets/style.css").read_text(encoding="utf-8")
        colors = {
            "text": ("#172033", "#f1f5f9"),
            "heading": ("#0f172a", "#f1f5f9"),
            "muted": ("#64748b", "#a9b7ca"),
            "secondary": ("#475569", "#c3cede"),
            "surface": ("#ffffff", "#171e2b"),
            "border": ("#d9e1ec", "#374151"),
        }

        for name, (light, dark) in colors.items():
            with self.subTest(token=name):
                self.assertRegex(
                    css_text,
                    rf"--ms-{name}\s*:\s*light-dark\(\s*{light}\s*,\s*{dark}\s*\)",
                )

    def test_css_background_tokens_support_both_color_schemes(self):
        css_text = Path("assets/style.css").read_text(encoding="utf-8")
        backgrounds = re.findall(
            r"(--ms-[\w-]*bg(?:-soft)?)\s*:\s*([^;]+);", css_text
        )

        self.assertTrue(backgrounds, "Expected page and domain background tokens")
        for name, value in backgrounds:
            with self.subTest(token=name, value=value):
                self.assertRegex(value, r"^light-dark\(.+,\s*.+\)$")

    def test_css_leaves_color_scheme_selection_to_streamlit(self):
        css_text = Path("assets/style.css").read_text(encoding="utf-8")
        declarations = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)

        self.assertNotRegex(declarations, r"(?<![\w-])color-scheme\s*:")
        self.assertNotIn("prefers-color-scheme", declarations)

    def test_css_does_not_override_native_select_and_popover_colors(self):
        css_text = Path("assets/style.css").read_text(encoding="utf-8")

        self.assertNotRegex(css_text, r'\[data-baseweb=["\'](?:select|popover|menu)["\']\]')
        self.assertNotRegex(css_text, r'\[role=["\'](?:listbox|option)["\']\]')

    def test_css_uses_stable_selectors_and_semantic_header(self):
        css_text = Path("assets/style.css").read_text(encoding="utf-8")

        self.assertNotIn(".st-emotion-cache-", css_text)
        self.assertRegex(css_text, r'(?m)^\[data-testid="stHeader"\]\s*\{')
        self.assertNotIn('div[data-testid="stHeader"]', css_text)

    def test_css_login_panel_uses_theme_surface(self):
        css_text = Path("assets/style.css").read_text(encoding="utf-8")
        panel_rule = re.search(
            r"\.stApp:has\(\.auth-login-panel\)\s+\.st-key-login_form\s*\{([^}]+)\}",
            css_text,
        )

        self.assertIsNotNone(panel_rule)
        self.assertRegex(panel_rule.group(1), r"background\s*:\s*var\(--ms-surface\)")


if __name__ == "__main__":
    unittest.main()
