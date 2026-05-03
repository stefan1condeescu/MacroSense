import unittest

from services.usda_food_data import USDAFoodDataClient


class USDAFoodDataParserTests(unittest.TestCase):
    def test_extract_macros_accepts_complete_usda_food(self):
        food = {
            "fdcId": 173944,
            "description": "Bananas, raw",
            "dataType": "SR Legacy",
            "foodNutrients": [
                {"nutrientId": 1008, "nutrientName": "Energy", "unitName": "KCAL", "value": 89},
                {"nutrientId": 1003, "nutrientName": "Protein", "unitName": "G", "value": 1.09},
                {"nutrientId": 1005, "nutrientName": "Carbohydrate, by difference", "unitName": "G", "value": 22.84},
                {"nutrientId": 1004, "nutrientName": "Total lipid (fat)", "unitName": "G", "value": 0.33},
            ],
        }

        normalized = USDAFoodDataClient.normalize_food(food)

        self.assertEqual(normalized["fdc_id"], "173944")
        self.assertEqual(normalized["description"], "Bananas, raw")
        self.assertEqual(normalized["data_type"], "SR Legacy")
        self.assertEqual(normalized["calories"], 89.0)
        self.assertEqual(normalized["protein_g"], 1.09)
        self.assertEqual(normalized["carbs_g"], 22.84)
        self.assertEqual(normalized["fats_g"], 0.33)

    def test_extract_macros_rejects_incomplete_usda_food(self):
        food = {
            "fdcId": 1,
            "description": "Incomplete food",
            "dataType": "Foundation",
            "foodNutrients": [
                {"nutrientId": 1008, "nutrientName": "Energy", "unitName": "KCAL", "value": 100},
            ],
        }

        self.assertIsNone(USDAFoodDataClient.normalize_food(food))

    def test_extract_macros_rejects_all_zero_nutrition(self):
        food = {
            "fdcId": 2,
            "description": "Zero macro sample",
            "dataType": "Survey (FNDDS)",
            "foodNutrients": [
                {"nutrientId": 1008, "nutrientName": "Energy", "unitName": "KCAL", "value": 0},
                {"nutrientId": 1003, "nutrientName": "Protein", "unitName": "G", "value": 0},
                {"nutrientId": 1005, "nutrientName": "Carbohydrate, by difference", "unitName": "G", "value": 0},
                {"nutrientId": 1004, "nutrientName": "Total lipid (fat)", "unitName": "G", "value": 0},
            ],
        }

        self.assertIsNone(USDAFoodDataClient.normalize_food(food))

    def test_extract_macros_rejects_zero_calories_even_with_macros(self):
        food = {
            "fdcId": 3,
            "description": "Zero calorie sample",
            "dataType": "Foundation",
            "foodNutrients": [
                {"nutrientId": 1008, "nutrientName": "Energy", "unitName": "KCAL", "value": 0},
                {"nutrientId": 1003, "nutrientName": "Protein", "unitName": "G", "value": 1},
                {"nutrientId": 1005, "nutrientName": "Carbohydrate, by difference", "unitName": "G", "value": 0},
                {"nutrientId": 1004, "nutrientName": "Total lipid (fat)", "unitName": "G", "value": 0},
            ],
        }

        self.assertIsNone(USDAFoodDataClient.normalize_food(food))

    def test_extract_macros_rejects_empty_macros_even_with_calories(self):
        food = {
            "fdcId": 4,
            "description": "No macro sample",
            "dataType": "Foundation",
            "foodNutrients": [
                {"nutrientId": 1008, "nutrientName": "Energy", "unitName": "KCAL", "value": 100},
                {"nutrientId": 1003, "nutrientName": "Protein", "unitName": "G", "value": 0},
                {"nutrientId": 1005, "nutrientName": "Carbohydrate, by difference", "unitName": "G", "value": 0},
                {"nutrientId": 1004, "nutrientName": "Total lipid (fat)", "unitName": "G", "value": 0},
            ],
        }

        self.assertIsNone(USDAFoodDataClient.normalize_food(food))

    def test_client_filters_unsupported_data_types_before_request(self):
        client = USDAFoodDataClient("dummy")

        self.assertEqual(client.search_foods("", ["Branded"]), [])

    def test_client_fetches_all_search_pages(self):
        class FakeClient(USDAFoodDataClient):
            def __init__(self):
                super().__init__("dummy")
                self.requested_pages = []

            def _request_search_page(self, query, data_types, page_size, page_number):
                self.requested_pages.append(page_number)
                foods_by_page = {
                    1: [
                        {
                            "fdcId": 1,
                            "description": "Food one",
                            "dataType": "SR Legacy",
                            "foodNutrients": [
                                {"nutrientId": 1008, "unitName": "KCAL", "value": 10},
                                {"nutrientId": 1003, "unitName": "G", "value": 1},
                                {"nutrientId": 1005, "unitName": "G", "value": 2},
                                {"nutrientId": 1004, "unitName": "G", "value": 3},
                            ],
                        }
                    ],
                    2: [
                        {
                            "fdcId": 2,
                            "description": "Food two",
                            "dataType": "Foundation",
                            "foodNutrients": [
                                {"nutrientId": 1008, "unitName": "KCAL", "value": 20},
                                {"nutrientId": 1003, "unitName": "G", "value": 2},
                                {"nutrientId": 1005, "unitName": "G", "value": 4},
                                {"nutrientId": 1004, "unitName": "G", "value": 6},
                            ],
                        }
                    ],
                }
                return {
                    "foods": foods_by_page[page_number],
                    "totalPages": 2,
                }

        client = FakeClient()

        results = client.search_foods("food", ["SR Legacy", "Foundation"])

        self.assertEqual(client.requested_pages, [1, 2])
        self.assertEqual([food["fdc_id"] for food in results], ["1", "2"])

    def test_client_keeps_only_results_matching_all_query_tokens(self):
        class FakeClient(USDAFoodDataClient):
            def __init__(self):
                super().__init__("dummy")

            def _request_search_page(self, query, data_types, page_size, page_number):
                nutrients = [
                    {"nutrientId": 1008, "unitName": "KCAL", "value": 100},
                    {"nutrientId": 1003, "unitName": "G", "value": 1},
                    {"nutrientId": 1005, "unitName": "G", "value": 2},
                    {"nutrientId": 1004, "unitName": "G", "value": 3},
                ]
                return {
                    "foods": [
                        {
                            "fdcId": 1,
                            "description": "Ice cream sandwich",
                            "dataType": "SR Legacy",
                            "foodNutrients": nutrients,
                        },
                        {
                            "fdcId": 2,
                            "description": "Cream of potato soup",
                            "dataType": "Survey (FNDDS)",
                            "foodNutrients": nutrients,
                        },
                    ],
                    "totalPages": 1,
                }

        client = FakeClient()

        results = client.search_foods("ice cream", ["SR Legacy", "Survey (FNDDS)"])

        self.assertEqual([food["description"] for food in results], ["Ice cream sandwich"])

    def test_client_filters_unexpected_data_types_from_response(self):
        class FakeClient(USDAFoodDataClient):
            def __init__(self):
                super().__init__("dummy")

            def _request_search_page(self, query, data_types, page_size, page_number):
                nutrients = [
                    {"nutrientId": 1008, "unitName": "KCAL", "value": 100},
                    {"nutrientId": 1003, "unitName": "G", "value": 1},
                    {"nutrientId": 1005, "unitName": "G", "value": 2},
                    {"nutrientId": 1004, "unitName": "G", "value": 3},
                ]
                return {
                    "foods": [
                        {
                            "fdcId": 1,
                            "description": "Chicken branded sample",
                            "dataType": "Branded",
                            "foodNutrients": nutrients,
                        },
                    ],
                    "totalPages": 1,
                }

        client = FakeClient()

        results = client.search_foods("chicken", ["Foundation"])

        self.assertEqual(results, [])

    def test_description_matching_handles_common_plural_forms(self):
        self.assertTrue(
            USDAFoodDataClient.description_matches_query(
                "Strawberry, raw",
                USDAFoodDataClient.get_query_tokens("strawberries")
            )
        )
        self.assertTrue(
            USDAFoodDataClient.description_matches_query(
                "Tomato, raw",
                USDAFoodDataClient.get_query_tokens("tomatoes")
            )
        )


if __name__ == "__main__":
    unittest.main()
