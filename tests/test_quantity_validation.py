import unittest

from ui.quantity_validation import quantity_range_help, validate_quantity_g


class QuantityValidationTests(unittest.TestCase):
    def test_quantity_rejects_values_below_minimum(self):
        error = validate_quantity_g(0, "Cantitatea")

        self.assertEqual(error, "Cantitatea trebuie să fie cel puțin 1 g.")

    def test_quantity_rejects_values_above_maximum(self):
        error = validate_quantity_g(5000.1, "Cantitatea nouă")

        self.assertEqual(error, "Cantitatea nouă trebuie să fie cel mult 5000 g.")

    def test_quantity_rejects_non_numeric_values(self):
        error = validate_quantity_g("abc", "Cantitatea")

        self.assertEqual(error, "Cantitatea trebuie să fie un număr valid.")

    def test_quantity_accepts_valid_range_edges(self):
        self.assertIsNone(validate_quantity_g(1))
        self.assertIsNone(validate_quantity_g(5000))

    def test_quantity_help_documents_supported_range(self):
        self.assertEqual(quantity_range_help(), "Interval acceptat: 1-5000 g.")


if __name__ == "__main__":
    unittest.main()
