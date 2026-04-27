import pandas as pd
from database import get_connection

class FoodItem:
    """
    Represents a food item in the system's nutritional database.
    Maps exactly to the FoodItem class in the UML Class Diagram.
    """
    def __init__(self, name: str, calories_100g: float, protein_g: float, carbs_g: float, fats_g: float, category: str, item_id: int = None):
        self.id = item_id
        self.name = name
        self.calories_100g = calories_100g
        self.protein_g = protein_g
        self.carbs_g = carbs_g
        self.fats_g = fats_g
        self.category = category

    def save(self) -> bool:
        """Saves the FoodItem object state to the PostgreSQL database."""
        conn = get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO food_items (name, calories_100g, protein_g, carbs_g, fats_g, category) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (self.name, self.calories_100g, self.protein_g, self.carbs_g, self.fats_g, self.category)
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
            cursor.execute("SELECT name, calories_100g, protein_g, carbs_g, fats_g, category FROM food_items ORDER BY name ASC")
            rows = cursor.fetchall()
            if rows:
                columns = ["Denumire", "Calorii/100g", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)", "Categorie"]
                return pd.DataFrame(rows, columns=columns)
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching food items: {e}")
            return pd.DataFrame()
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
                SELECT id, name, calories_100g, protein_g, carbs_g, fats_g
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
                }
            return options
        except Exception as e:
            print(f"Error fetching food catalog options: {e}")
            return {}
        finally:
            if conn:
                conn.close()
