import json
import re
import urllib.parse
import urllib.request


class USDAFoodDataClient:
    """Small client for USDA FoodData Central food search results."""

    BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    FOOD_DETAILS_URL = "https://fdc.nal.usda.gov/fdc-app.html#/food-details/{fdc_id}/nutrients"
    SOURCE_NAME = "USDA"
    ALLOWED_DATA_TYPES = ("SR Legacy", "Foundation", "Survey (FNDDS)")
    SEARCH_STOP_WORDS = {"and", "or", "the", "a", "an", "of", "with", "in"}
    DEFAULT_PAGE_SIZE = 25
    DEFAULT_MAX_PAGES = 4
    DEFAULT_MAX_RESULTS = 40

    def __init__(self, api_key: str):
        self.api_key = api_key

    @staticmethod
    def build_food_url(fdc_id) -> str:
        return USDAFoodDataClient.FOOD_DETAILS_URL.format(fdc_id=fdc_id)

    @classmethod
    def get_query_tokens(cls, query: str) -> list[str]:
        """Extracts meaningful USDA search tokens from an English query."""
        tokens = re.findall(r"[a-z0-9]+", (query or "").lower())
        return [
            token
            for token in tokens
            if token not in cls.SEARCH_STOP_WORDS and len(token) > 1
        ]

    @staticmethod
    def get_token_variants(token: str) -> set[str]:
        variants = {token}
        if token.endswith("ies") and len(token) > 4:
            variants.add(f"{token[:-3]}y")
        elif token.endswith("oes") and len(token) > 4:
            variants.add(token[:-2])
        elif token.endswith("s") and len(token) > 3:
            variants.add(token[:-1])
        elif token.endswith("y") and len(token) > 3:
            variants.add(f"{token[:-1]}ies")
        elif token.endswith("o") and len(token) > 3:
            variants.add(f"{token}es")
        elif len(token) > 3:
            variants.add(f"{token}s")
        return variants

    @classmethod
    def description_matches_query(cls, description: str, query_tokens: list[str]) -> bool:
        """Keeps only USDA foods whose description contains all query tokens."""
        if not query_tokens:
            return True

        description_words = set(re.findall(r"[a-z0-9]+", (description or "").lower()))
        for token in query_tokens:
            if not cls.get_token_variants(token).intersection(description_words):
                return False
        return True

    @classmethod
    def relevance_score(cls, description: str, query: str) -> tuple[int, int, str]:
        """Ranks exact phrase matches before looser token matches."""
        normalized_description = (description or "").lower()
        normalized_query = " ".join(cls.get_query_tokens(query))
        exact_phrase_penalty = 0 if normalized_query and normalized_query in normalized_description else 1
        prefix_penalty = 0 if normalized_description.startswith(normalized_query) else 1
        return (exact_phrase_penalty, prefix_penalty, normalized_description)

    @staticmethod
    def extract_macros(food: dict) -> dict | None:
        nutrients = food.get("foodNutrients") or []
        values = {
            "calories": None,
            "protein_g": None,
            "carbs_g": None,
            "fats_g": None,
        }

        for nutrient in nutrients:
            nutrient_id = nutrient.get("nutrientId") or nutrient.get("nutrientNumber")
            nutrient_name = (nutrient.get("nutrientName") or nutrient.get("name") or "").lower()
            unit_name = (nutrient.get("unitName") or "").lower()
            value = nutrient.get("value")
            if value is None:
                value = nutrient.get("amount")

            if value is None:
                continue

            try:
                numeric_value = round(float(value), 2)
            except (TypeError, ValueError):
                continue

            nutrient_id_text = str(nutrient_id)
            if (
                nutrient_id_text in ("1008", "208")
                or ("energy" in nutrient_name and unit_name == "kcal")
            ):
                values["calories"] = numeric_value
            elif nutrient_id_text in ("1003", "203") or nutrient_name == "protein":
                values["protein_g"] = numeric_value
            elif (
                nutrient_id_text in ("1005", "205")
                or "carbohydrate" in nutrient_name
            ):
                values["carbs_g"] = numeric_value
            elif (
                nutrient_id_text in ("1004", "204")
                or "total lipid" in nutrient_name
                or nutrient_name == "fat"
            ):
                values["fats_g"] = numeric_value

        if any(values[key] is None for key in values):
            return None
        return values

    @classmethod
    def normalize_food(cls, food: dict) -> dict | None:
        macros = cls.extract_macros(food)
        if not macros:
            return None
        if float(macros["calories"] or 0) <= 0:
            return None
        if all(float(macros[key] or 0) == 0 for key in ("protein_g", "carbs_g", "fats_g")):
            return None

        fdc_id = food.get("fdcId")
        if fdc_id is None:
            return None

        return {
            "fdc_id": str(fdc_id),
            "description": food.get("description") or "",
            "data_type": food.get("dataType") or "USDA",
            "source": cls.SOURCE_NAME,
            "source_url": cls.build_food_url(fdc_id),
            **macros,
        }

    def _request_search_page(self, query: str, data_types: list[str], page_size: int, page_number: int) -> dict:
        """Fetches one USDA search page."""
        url = f"{self.BASE_URL}/foods/search?{urllib.parse.urlencode({'api_key': self.api_key})}"
        payload = {
            "query": query,
            "dataType": data_types,
            "pageSize": page_size,
            "pageNumber": page_number,
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def search_foods(
        self,
        query: str,
        data_types: list[str],
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
        max_results: int = DEFAULT_MAX_RESULTS
    ) -> list[dict]:
        cleaned_query = query.strip()
        cleaned_data_types = [
            data_type
            for data_type in data_types
            if data_type in self.ALLOWED_DATA_TYPES
        ]

        if not cleaned_query or not cleaned_data_types:
            return []

        normalized_foods = []
        seen_ids = set()
        page_number = 1
        query_tokens = self.get_query_tokens(cleaned_query)

        while True:
            response_payload = self._request_search_page(
                cleaned_query,
                cleaned_data_types,
                page_size,
                page_number
            )
            foods = response_payload.get("foods") or []
            for food in foods:
                normalized = self.normalize_food(food)
                if not normalized or normalized["fdc_id"] in seen_ids:
                    continue
                if normalized["data_type"] not in cleaned_data_types:
                    continue
                if not self.description_matches_query(normalized["description"], query_tokens):
                    continue
                seen_ids.add(normalized["fdc_id"])
                normalized_foods.append(normalized)
                if len(normalized_foods) >= max_results:
                    break

            total_pages = int(response_payload.get("totalPages") or 1)
            if (
                len(normalized_foods) >= max_results
                or page_number >= total_pages
                or page_number >= max_pages
                or not foods
            ):
                break
            page_number += 1

        return sorted(
            normalized_foods,
            key=lambda food: self.relevance_score(food["description"], cleaned_query)
        )
