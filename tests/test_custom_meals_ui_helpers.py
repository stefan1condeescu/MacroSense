import inspect
import unittest

from ui.pages.custom_meals_page import (
    escape_html_text,
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
