import inspect
import unittest
from unittest.mock import patch

from models.tracking import CustomMeal
from ui import language
from ui.pages import custom_meals_page
from ui.pages.custom_meals_page import (
    CUSTOM_MEAL_STATUS_SOURCE_TEXT,
    build_custom_meal_display_rows_and_totals,
    build_custom_meal_summary_cards_html,
    escape_html_text,
    format_custom_meal_status,
    format_display_number,
    get_edit_quantity_widget_keys_to_reset,
    render_custom_meals_page,
)


class CustomMealUIHelperTests(unittest.TestCase):
    def test_escape_html_text_prevents_html_injection_in_cards(self):
        escaped = escape_html_text('A <span style="font-size:60px">TEST</span>')

        self.assertEqual(
            escaped,
            'A &lt;span style=&quot;font-size:60px&quot;&gt;TEST&lt;/span&gt;'
        )

    def test_summary_cards_render_all_totals_in_both_languages(self):
        expected_labels = {
            "en": (
                "Total quantity",
                "Total calories",
                "Protein",
                "Carbohydrates",
                "Fats",
            ),
            "ro": (
                "Cantitate totală",
                "Calorii totale",
                "Proteine",
                "Carbohidrați",
                "Grăsimi",
            ),
        }

        for language_code, labels in expected_labels.items():
            with self.subTest(language_code=language_code):
                with patch.object(
                    language.st,
                    "session_state",
                    {"language": language_code},
                ):
                    summary_html = build_custom_meal_summary_cards_html(
                        total_quantity=300,
                        total_calories=744,
                        total_protein=26.3,
                        total_carbs=33.6,
                        total_fats=61.1,
                    )

                self.assertIn('class="custom-meal-summary-grid"', summary_html)
                self.assertEqual(
                    summary_html.count('class="custom-meal-summary-card"'),
                    5,
                )
                for label in labels:
                    self.assertIn(f"<span>{label}</span>", summary_html)
                for value in ("300 g", "744 kcal", "26.3 g", "33.6 g", "61.1 g"):
                    self.assertIn(value, summary_html)
                self.assertNotIn("\n        <div", summary_html)

    def test_status_labels_translate_without_changing_stored_values(self):
        self.assertEqual(
            CUSTOM_MEAL_STATUS_SOURCE_TEXT,
            {
                CustomMeal.ACTIVE_STATUS: "Saved",
                CustomMeal.ARCHIVED_STATUS: "Archived",
            },
        )
        self.assertEqual(CustomMeal.ACTIVE_STATUS, "Salvată")
        self.assertEqual(CustomMeal.ARCHIVED_STATUS, "Arhivată")

        with patch.object(language.st, "session_state", {"language": "en"}):
            self.assertEqual(format_custom_meal_status("Salvată"), "Saved")
            self.assertEqual(format_custom_meal_status("Arhivată"), "Archived")
            self.assertEqual(format_custom_meal_status("Future status"), "Future status")

        with patch.object(language.st, "session_state", {"language": "ro"}):
            self.assertEqual(format_custom_meal_status("Salvată"), "Salvată")
            self.assertEqual(format_custom_meal_status("Arhivată"), "Arhivată")

    def test_meal_display_totals_sum_the_visible_rounded_rows(self):
        rows, totals = build_custom_meal_display_rows_and_totals([
            {
                "name": "Carne de vitel",
                "source_label": "USDA SR",
                "quantity_g": 100.0,
                "calories_100g": 301.04,
                "protein_g": 14.04,
                "carbs_g": 3.04,
                "fats_g": 25.94,
            },
            {
                "name": "Ceapa",
                "source_label": "USDA FNDDS",
                "quantity_g": 57.0,
                "calories_100g": 32.0,
                "protein_g": 1.8,
                "carbs_g": 7.3,
                "fats_g": 0.2,
            },
        ])

        self.assertEqual(rows[0][5], 3.0)
        self.assertEqual(rows[1][5], 4.2)
        self.assertEqual(format_display_number(totals["carbs_g"], 1), "7.2")

    def test_saved_meal_cards_use_same_display_totals_as_edit_summary(self):
        page_source = inspect.getsource(render_custom_meals_page)
        card_renderer_start = page_source.index("def render_custom_meal_cards")
        card_renderer_source = page_source[
            card_renderer_start:
            page_source.index("recipe_name = st.text_input", card_renderer_start)
        ]

        self.assertIn("CustomMeal.get_ingredients", card_renderer_source)
        self.assertIn("build_custom_meal_display_rows_and_totals", card_renderer_source)
        self.assertIn("format_display_number(display_totals['carbs_g'], 1)", card_renderer_source)

    def test_page_preserves_raw_selection_ids_and_persistence_calls(self):
        page_source = inspect.getsource(custom_meals_page.render_custom_meals_page)

        self.assertIn(
            "food_selection_display_df = build_food_selection_display_dataframe(",
            page_source,
        )
        self.assertIn(
            'int(food_selection_df.iloc[selected_rows[0]]["_food_id"])',
            page_source,
        )
        self.assertIn("custom_meal_ids = list(custom_meal_options.keys())", page_source)
        self.assertIn("active_meal_ids = list(active_meal_options.keys())", page_source)
        self.assertIn("archived_meal_ids = list(archived_meal_options.keys())", page_source)
        self.assertGreaterEqual(page_source.count("options=custom_meal_ids"), 2)

        self.assertIn("CustomMeal.create_with_ingredients(", page_source)
        self.assertIn("ingredients=pending_ingredients", page_source)
        self.assertIn("CustomMeal.archive(selected_archive_meal_id, user_id)", page_source)
        self.assertIn("CustomMeal.restore(selected_restore_meal_id, user_id)", page_source)
        self.assertIn("CustomMeal.update_with_ingredients(", page_source)
        self.assertIn("meal_id=selected_edit_meal_id", page_source)
        self.assertIn("ingredients=edit_ingredients", page_source)

    def test_edit_quantity_reset_keeps_picker_widgets_stable(self):
        session_keys = [
            "custom_meal_edit_qty_12_existing_1",
            "custom_meal_edit_qty_12_new_2",
            "custom_meal_edit_add_quantity_12",
            "custom_meal_edit_ingredient_search_12_4",
            "custom_meal_edit_ingredient_category_12_4",
            "custom_meal_edit_ingredient_table_12_4",
            "custom_meal_edit_select_4",
            "custom_meal_edit_qty_13_existing_1",
        ]

        reset_keys = get_edit_quantity_widget_keys_to_reset(session_keys, 12)

        self.assertEqual(
            reset_keys,
            [
                "custom_meal_edit_qty_12_existing_1",
                "custom_meal_edit_qty_12_new_2",
                "custom_meal_edit_add_quantity_12",
            ],
        )

    def test_edit_success_refreshes_name_widgets_without_rebuilding_picker_table(self):
        page_source = inspect.getsource(render_custom_meals_page)
        update_success_source = page_source[page_source.index("if updated_meal:"):]

        self.assertIn("custom_meal_name_widget_version", update_success_source)
        self.assertIn("custom_meal_reset_edit_quantity_widgets", update_success_source)
        self.assertNotIn('st.session_state["custom_meal_reset_widgets"] = True', update_success_source)
        self.assertNotIn('st.session_state["custom_meal_details_selected_id"]', update_success_source)
        self.assertIn('f"custom_meal_edit_select_{custom_meal_name_widget_version}"', page_source)
        self.assertIn('f"custom_meal_edit_ingredient_table_{selected_edit_meal_id}_{custom_meal_widget_version}"', page_source)

    def test_edit_success_message_hides_internal_snapshot_workflow(self):
        page_source = inspect.getsource(render_custom_meals_page)
        update_success_source = page_source[page_source.index("if updated_meal:"):]

        self.assertNotIn("recalculate", update_success_source.lower())
        self.assertIn("remain unchanged", update_success_source)
        self.assertIn("translate(", update_success_source)


if __name__ == "__main__":
    unittest.main()
