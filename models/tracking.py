import datetime
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
        finally:
            if conn:
                conn.close()


class Activity:
    """
    Represents a physical activity in the system's catalog.
    Maps exactly to the Activity class in the UML Class Diagram.
    """
    def __init__(self, name: str, met_multiplier: float, category: str, activity_id: int = None):
        self.id = activity_id
        self.name = name
        self.met_multiplier = met_multiplier
        self.category = category

    def save(self) -> bool:
        """Saves the Activity object state to the PostgreSQL database."""
        conn = get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO activities (name, met_multiplier, category) VALUES (%s, %s, %s)",
                (self.name, self.met_multiplier, self.category)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving activity: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_all_as_dataframe(cls) -> pd.DataFrame:
        """Fetches all activities and returns them as a pandas DataFrame for UI rendering."""
        conn = get_connection()
        if not conn:
            return pd.DataFrame()
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name, met_multiplier, category FROM activities ORDER BY name ASC")
            rows = cursor.fetchall()
            if rows:
                columns = ["Denumire", "Coeficient MET", "Categorie"]
                return pd.DataFrame(rows, columns=columns)
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

class FoodLog:
    """
    Represents a specific food consumption event in a user's daily log.
    Maps to the FoodLog class in the UML Class Diagram.
    """
    def __init__(self, log_id: int, quantity_g: float, meal_type: str, meal_time: datetime.time, 
                 food_id: int = None, custom_meal_id: int = None, log_entry_id: int = None):
        self.id = log_entry_id
        self.log_id = log_id
        self.quantity_g = quantity_g
        self.meal_type = meal_type
        self.meal_time = meal_time
        
        # XOR Enforcement at Object Level: A log must be EITHER a basic food item OR a custom meal
        if (food_id is None and custom_meal_id is None) or (food_id is not None and custom_meal_id is not None):
            raise ValueError("FoodLog must reference exactly one: either food_id OR custom_meal_id.")
            
        self.food_id = food_id
        self.custom_meal_id = custom_meal_id

    def save(self) -> bool:
        """
        Saves the FoodLog entry to the PostgreSQL database 
        and updates the instance with the generated ID.
        """
        conn = get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO food_logs (log_id, food_id, custom_meal_id, quantity_g, meal_type, meal_time) 
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (self.log_id, self.food_id, self.custom_meal_id, self.quantity_g, self.meal_type, self.meal_time)
            )
            # Retrieve the auto-generated primary key
            self.id = cursor.fetchone()[0]
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving food log: {e}")
            return False
        finally:
            if conn:
                conn.close()