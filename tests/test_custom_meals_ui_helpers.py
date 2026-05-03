import unittest

from ui.pages.custom_meals_page import escape_html_text


class CustomMealUIHelperTests(unittest.TestCase):
    def test_escape_html_text_prevents_html_injection_in_cards(self):
        escaped = escape_html_text('A <span style="font-size:60px">TEST</span>')

        self.assertEqual(
            escaped,
            'A &lt;span style=&quot;font-size:60px&quot;&gt;TEST&lt;/span&gt;'
        )


if __name__ == "__main__":
    unittest.main()
