import pandas as pd
from database import get_connection
from models.text_validation import contains_letter, has_obvious_html_chars


class FoodItem:
    """
    Represents a food item in the system's nutritional database.
    Maps exactly to the FoodItem class in the UML Class Diagram.
    """
    def __init__(
        self,
        name: str,
        calories_100g: float,
        protein_g: float,
        carbs_g: float,
        fats_g: float,
        category: str,
        item_id: int = None,
        source: str = None,
        source_type: str = None,
        external_id: str = None,
        source_url: str = None
    ):
        self.id = item_id
        self.name = name.strip() if name else ""
        self.calories_100g = float(calories_100g or 0)
        self.protein_g = float(protein_g or 0)
        self.carbs_g = float(carbs_g or 0)
        self.fats_g = float(fats_g or 0)
        self.category = category.strip() if category else ""
        self.source = source
        self.source_type = source_type
        self.external_id = str(external_id) if external_id is not None else None
        self.source_url = source_url

        nutrition_values = [self.calories_100g, self.protein_g, self.carbs_g, self.fats_g]
        if not self.name:
            raise ValueError("Food item name cannot be empty.")
        if has_obvious_html_chars(self.name):
            raise ValueError("Food item name cannot contain HTML-like characters.")
        if not contains_letter(self.name):
            raise ValueError("Food item name must contain at least one letter.")
        if not self.category:
            raise ValueError("Food item category cannot be empty.")
        if any(value < 0 for value in nutrition_values):
            raise ValueError("Food item nutrition values cannot be negative.")
        if self.calories_100g <= 0:
            raise ValueError("Food item calories must be strictly positive.")
        if all(value == 0 for value in [self.protein_g, self.carbs_g, self.fats_g]):
            raise ValueError("Food item must contain at least one positive macronutrient.")

    def save(self) -> bool:
        """Saves the FoodItem object state to the PostgreSQL database."""
        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO food_items (
                    name, calories_100g, protein_g, carbs_g, fats_g, category,
                    source, source_type, external_id, source_url
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    self.name,
                    self.calories_100g,
                    self.protein_g,
                    self.carbs_g,
                    self.fats_g,
                    self.category,
                    self.source,
                    self.source_type,
                    self.external_id,
                    self.source_url
                )
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving food item: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_all_as_dataframe(cls) -> pd.DataFrame:
        """Fetches all food items and returns them as a pandas DataFrame for UI rendering."""
        conn = get_connection()
        if not conn:
            return pd.DataFrame()

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    name,
                    calories_100g,
                    protein_g,
                    carbs_g,
                    fats_g,
                    category,
                    COALESCE(
                        CASE
                            WHEN source = 'USDA' AND source_type = 'SR Legacy' THEN 'USDA SR'
                            WHEN source = 'USDA' AND source_type = 'Foundation' THEN 'USDA Foundation'
                            WHEN source = 'USDA' AND source_type = 'Survey (FNDDS)' THEN 'USDA FNDDS'
                            WHEN source IS NOT NULL AND source_type IS NOT NULL THEN source || ' ' || source_type
                            WHEN source IS NOT NULL THEN source
                            ELSE NULL
                        END,
                        'MacroSense'
                    ) AS source_label
                FROM food_items
                ORDER BY name ASC
                """
            )
            rows = cursor.fetchall()
            if rows:
                columns = ["Denumire", "Calorii/100g", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)", "Categorie", "Sursă"]
                return pd.DataFrame(rows, columns=columns)
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching food items: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

    @classmethod
    def external_reference_exists(cls, source: str, external_id: str) -> bool:
        """Checks whether an external food reference was already imported."""
        if not source or external_id is None:
            return False

        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1
                FROM food_items
                WHERE source = %s AND external_id = %s
                LIMIT 1
                """,
                (source, str(external_id))
            )
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error checking food external reference: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_catalog_options(cls) -> dict:
        """Fetches food items as option metadata for reactive UI selectors."""
        conn = get_connection()
        if not conn:
            return {}

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    calories_100g,
                    protein_g,
                    carbs_g,
                    fats_g,
                    category,
                    COALESCE(
                        CASE
                            WHEN source = 'USDA' AND source_type = 'SR Legacy' THEN 'USDA SR'
                            WHEN source = 'USDA' AND source_type = 'Foundation' THEN 'USDA Foundation'
                            WHEN source = 'USDA' AND source_type = 'Survey (FNDDS)' THEN 'USDA FNDDS'
                            WHEN source IS NOT NULL AND source_type IS NOT NULL THEN source || ' ' || source_type
                            WHEN source IS NOT NULL THEN source
                            ELSE NULL
                        END,
                        'MacroSense'
                    ) AS source_label
                FROM food_items
                ORDER BY name ASC
                """
            )
            options = {}
            for row in cursor.fetchall():
                options[row[0]] = {
                    "id": row[0],
                    "name": row[1],
                    "calories_100g": float(row[2] or 0),
                    "protein_g": float(row[3] or 0),
                    "carbs_g": float(row[4] or 0),
                    "fats_g": float(row[5] or 0),
                    "category": row[6] or "Altele",
                    "source_label": row[7] or "MacroSense",
                }
            return options
        except Exception as e:
            print(f"Error fetching food catalog options: {e}")
            return {}
        finally:
            if conn:
                conn.close()
