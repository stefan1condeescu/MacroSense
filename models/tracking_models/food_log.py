import datetime
from database import get_connection

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

        if self.quantity_g <= 0:
            raise ValueError("FoodLog quantity must be strictly positive.")
        
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
        if quantity_g <= 0:
            raise ValueError("FoodLog quantity must be strictly positive.")

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
