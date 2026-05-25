import inspect
import unittest

from ui.pages.custom_meals_page import (
    build_custom_meal_display_rows_and_totals,
    build_custom_meal_summary_cards_html,
    escape_html_text,
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

    def test_summary_cards_render_all_current_meal_totals(self):
        summary_html = build_custom_meal_summary_cards_html(
            total_quantity=300,
            total_calories=744,
            total_protein=26.3,
            total_carbs=33.6,
            total_fats=61.1,
        )

        self.assertIn('class="custom-meal-summary-grid"', summary_html)
        self.assertEqual(summary_html.count('class="custom-meal-summary-card"'), 5)
        self.assertIn("Cantitate totală", summary_html)
        self.assertIn("300 g", summary_html)
        self.assertIn("Calorii totale", summary_html)
        self.assertIn("744 kcal", summary_html)
        self.assertIn("Proteine", summary_html)
        self.assertIn("26.3 g", summary_html)
        self.assertIn("Carbohidrați", summary_html)
        self.assertIn("33.6 g", summary_html)
        self.assertIn("Grăsimi", summary_html)
        self.assertIn("61.1 g", summary_html)
        self.assertNotIn("\n        <div", summary_html)

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
        card_renderer_source = page_source[
            page_source.index("def render_custom_meal_cards"):
            page_source.index('st.subheader("➕ Creează o masă personalizată")')
        ]

        self.assertIn("CustomMeal.get_ingredients", card_renderer_source)
        self.assertIn("build_custom_meal_display_rows_and_totals", card_renderer_source)
        self.assertIn("format_display_number(display_totals['carbs_g'], 1)", card_renderer_source)

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

        self.assertNotIn("Jurnale recalculate", page_source)
        self.assertNotIn("recalculate_totals", page_source)
        self.assertIn("Intrările deja salvate în jurnal rămân neschimbate", page_source)


if __name__ == "__main__":
    unittest.main()
