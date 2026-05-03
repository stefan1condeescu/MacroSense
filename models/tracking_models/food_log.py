import datetime
from database import get_connection

class FoodLog:
    """
    Represents a specific food consumption event in a user's daily log.
    Maps to the FoodLog class in the UML Class Diagram.
    """
    MIN_QUANTITY_G = 1.0
    MAX_QUANTITY_G = 5000.0
    VALID_MEAL_TYPES = ("Mic dejun", "Prânz", "Cină", "Gustare")

    def __init__(self, log_id: int, quantity_g: float, meal_type: str, meal_time: datetime.time, 
                 food_id: int = None, custom_meal_id: int = None, log_entry_id: int = None):
        self.id = log_entry_id
        self.log_id = log_id
        self.quantity_g = quantity_g
        self.meal_type = meal_type
        self.meal_time = meal_time

        self.validate_quantity(self.quantity_g)
        self.validate_meal_type(self.meal_type)
        self.validate_meal_time(self.meal_time)
        
        if (food_id is None and custom_meal_id is None) or (food_id is not None and custom_meal_id is not None):
            raise ValueError("FoodLog must reference exactly one: either food_id OR custom_meal_id.")
            
        self.food_id = food_id
        self.custom_meal_id = custom_meal_id

    @classmethod
    def validate_quantity(cls, quantity_g: float) -> None:
        """Validates consumed quantity consistently with the UI and database constraints."""
        if quantity_g < cls.MIN_QUANTITY_G:
            raise ValueError("FoodLog quantity must be at least 1 gram.")
        if quantity_g > cls.MAX_QUANTITY_G:
            raise ValueError("FoodLog quantity must be at most 5000 grams.")

    @classmethod
    def validate_meal_type(cls, meal_type: str) -> None:
        """Validates meal type consistently with the database constraint."""
        if meal_type not in cls.VALID_MEAL_TYPES:
            raise ValueError("FoodLog meal type is not supported.")

    @staticmethod
    def validate_meal_time(meal_time: datetime.time) -> None:
        """Validates that food entries always have a concrete consumption time."""
        if not isinstance(meal_time, datetime.time):
            raise ValueError("FoodLog meal time must be a valid time.")

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

    @classmethod
    def delete(cls, log_entry_id: int, user_id: int) -> bool:
        """Deletes a FoodLog entry only if it belongs to the given user."""
        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM food_logs fl
                USING daily_logs dl
                WHERE fl.log_id = dl.id
                  AND fl.id = %s
                  AND dl.user_id = %s
                RETURNING fl.id
                """,
                (log_entry_id, user_id)
            )
            deleted_row = cursor.fetchone()
            conn.commit()
            return deleted_row is not None
        except Exception as e:
            print(f"Error deleting food log: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def update(cls, log_entry_id: int, user_id: int, quantity_g: float, meal_type: str, meal_time: datetime.time) -> bool:
        """Updates editable FoodLog fields only if the entry belongs to the given user."""
        cls.validate_quantity(quantity_g)
        cls.validate_meal_type(meal_type)
        cls.validate_meal_time(meal_time)

        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE food_logs fl
                SET quantity_g = %s,
                    meal_type = %s,
                    meal_time = %s
                FROM daily_logs dl
                WHERE fl.log_id = dl.id
                  AND fl.id = %s
                  AND dl.user_id = %s
                RETURNING fl.id
                """,
                (quantity_g, meal_type, meal_time, log_entry_id, user_id)
            )
            updated_row = cursor.fetchone()
            conn.commit()
            return updated_row is not None
        except Exception as e:
            print(f"Error updating food log: {e}")
            return False
        finally:
            if conn:
                conn.close()
