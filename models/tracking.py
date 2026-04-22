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

class DailyLog:
    """
    Represents the daily nutritional and fitness summary for a user.
    Maps to the DailyLog class in the UML Class Diagram and the daily_logs table.
    """
    def __init__(self, user_id: int, log_date: datetime.date, 
                 total_calories_in: float = 0.0, 
                 total_calories_burned: float = 0.0, 
                 log_id: int = None):
        self.id = log_id
        self.user_id = user_id
        self.log_date = log_date
        self.total_calories_in = total_calories_in
        self.total_calories_burned = total_calories_burned

    def calculate_energy_balance(self) -> float:
        """Returns the net caloric balance for the day (calories_in - calories_burned)."""
        return round(self.total_calories_in - self.total_calories_burned, 2)

    @classmethod
    def get_or_create(cls, user_id: int, log_date: datetime.date) -> "DailyLog | None":
        """
        Fetches the DailyLog for the given user and date.
        If it does not exist, creates a new empty record and returns it.
        Uses the UNIQUE constraint (user_id, log_date) to avoid duplicates.
        """
        conn = get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO daily_logs (user_id, log_date, total_calories_in, total_calories_burned)
                VALUES (%s, %s, 0, 0)
                ON CONFLICT ON CONSTRAINT uq_daily_log DO NOTHING
                """,
                (user_id, log_date)
            )
            conn.commit()
            
            cursor.execute(
                """
                SELECT id, user_id, log_date, total_calories_in, total_calories_burned
                FROM daily_logs
                WHERE user_id = %s AND log_date = %s
                """,
                (user_id, log_date)
            )
            row = cursor.fetchone()
            if row:
                return cls(
                    user_id=row[1],
                    log_date=row[2],
                    total_calories_in=float(row[3]),
                    total_calories_burned=float(row[4]),
                    log_id=row[0]
                )
            return None
        except Exception as e:
            print(f"Error in DailyLog.get_or_create: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def recalculate_totals(self) -> bool:
        """
        Recomputes total_calories_in (from food_logs) and total_calories_burned (from activity_logs)
        and updates the daily_logs record in the database.
        """
        conn = get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # 1. Calculate Calories IN (Food)
            cursor.execute(
                """
                SELECT COALESCE(SUM(fi.calories_100g * fl.quantity_g / 100.0), 0)
                FROM food_logs fl
                JOIN food_items fi ON fi.id = fl.food_id
                WHERE fl.log_id = %s AND fl.food_id IS NOT NULL
                """,
                (self.id,)
            )
            calories_from_food = float(cursor.fetchone()[0])
            calories_from_meals = 0.0 # TODO: Delegate to CustomMeals later
            self.total_calories_in = round(calories_from_food + calories_from_meals, 2)
            
            # 2. Fetch latest user weight for MET calculation
            cursor.execute(
                """
                SELECT weight_kg FROM weight_logs 
                WHERE user_id = %s AND log_date <= %s 
                ORDER BY log_date DESC LIMIT 1
                """,
                (self.user_id, self.log_date)
            )
            weight_row = cursor.fetchone()
            # Fallback to standard weight if no log exists (safety net)
            current_weight = float(weight_row[0]) if weight_row else 70.0

            # 3. Calculate Calories BURNED (Activities via MET formula)
            # Formula: MET * Weight(kg) * (Duration(min) / 60)
            cursor.execute(
                """
                SELECT COALESCE(SUM(a.met_multiplier * (al.duration_min / 60.0)), 0)
                FROM activity_logs al
                JOIN activities a ON a.id = al.activity_id
                WHERE al.log_id = %s
                """,
                (self.id,)
            )
            met_duration_factor = float(cursor.fetchone()[0])
            self.total_calories_burned = round(met_duration_factor * current_weight, 2)
            
            # 4. Update the DailyLog record
            cursor.execute(
                """
                UPDATE daily_logs 
                SET total_calories_in = %s, total_calories_burned = %s 
                WHERE id = %s
                """,
                (self.total_calories_in, self.total_calories_burned, self.id)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error recalculating DailyLog totals: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_food_entries(cls, log_id: int) -> "pd.DataFrame":
        """
        Returns all food-item FoodLog entries for a given daily_log id as a DataFrame,
        joined with food_items to show human-readable names and computed calories.
        """
        conn = get_connection()
        if not conn:
            return pd.DataFrame()
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    fl.id, 
                    fi.name                                              AS "Aliment",
                    fl.quantity_g                                        AS "Cantitate (g)",
                    ROUND(fi.calories_100g * fl.quantity_g / 100.0, 2)  AS "Calorii",
                    fl.meal_type                                         AS "Masă",
                    fl.meal_time                                         AS "Ora"
                FROM food_logs fl
                JOIN food_items fi ON fi.id = fl.food_id
                WHERE fl.log_id = %s AND fl.food_id IS NOT NULL
                ORDER BY fl.meal_time ASC NULLS LAST
                """,
                (log_id,)
            )
            rows = cursor.fetchall()
            if rows:
                columns = ["id", "Aliment", "Cantitate (g)", "Calorii", "Masă", "Ora"]
                df = pd.DataFrame(rows, columns=columns)
                return df.set_index("id")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching food entries: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()
class ActivityLog:
    """
    Represents a physical activity event logged by the user in a given day.
    Maps to the ActivityLog class in the UML Class Diagram.
    """
    def __init__(self, log_id: int, activity_id: int, duration_min: int, sets: int = None, reps: int = None, log_entry_id: int = None):
        self.id = log_entry_id
        self.log_id = log_id
        self.activity_id = activity_id
        self.duration_min = duration_min
        self.sets = sets
        self.reps = reps

        # Enforce duration constraint at object level
        if self.duration_min <= 0:
            raise ValueError("Duration must be strictly positive for MET calculation.")

    def save(self) -> bool:
        """Saves the ActivityLog entry to the PostgreSQL database."""
        conn = get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO activity_logs (log_id, activity_id, duration_min, sets, reps) 
                   VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                (self.log_id, self.activity_id, self.duration_min, self.sets, self.reps)
            )
            self.id = cursor.fetchone()[0]
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving activity log: {e}")
            return False
        finally:
            if conn:
                conn.close()