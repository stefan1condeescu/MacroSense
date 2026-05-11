import datetime
import pandas as pd
from database import get_connection


def format_optional_activity_count(value) -> str:
    """Formats optional sets/reps values without leaking Pandas float artifacts such as 6.0."""
    if value is None or pd.isna(value):
        return "-"

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return str(value)

    if numeric_value.is_integer():
        return str(int(numeric_value))
    return str(numeric_value)


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
    def get_by_id(cls, log_id: int, user_id: int) -> "DailyLog | None":
        """Fetches a DailyLog by ID only if it belongs to the given user."""
        conn = get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, log_date, total_calories_in, total_calories_burned
                FROM daily_logs
                WHERE id = %s AND user_id = %s
                """,
                (log_id, user_id)
            )
            row = cursor.fetchone()
            if row:
                return cls(
                    log_id=row[0],
                    user_id=row[1],
                    log_date=row[2],
                    total_calories_in=float(row[3]),
                    total_calories_burned=float(row[4])
                )
            return None
        except Exception as e:
            print(f"Error fetching daily log by ID: {e}")
            return None
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_for_date(cls, user_id: int, log_date: datetime.date) -> "DailyLog | None":
        """Fetches an existing DailyLog for a user/date without creating an empty row."""
        conn = get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
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
                    log_id=row[0],
                    user_id=row[1],
                    log_date=row[2],
                    total_calories_in=float(row[3]),
                    total_calories_burned=float(row[4])
                )
            return None
        except Exception as e:
            print(f"Error fetching daily log by date: {e}")
            return None
        finally:
            if conn:
                conn.close()

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

    @staticmethod
    def calculate_hybrid_calories(category: str, met: float, weight: float, duration_min: float, sets: int, reps: int) -> float:
        """
        Helper method to compute calories ensuring DRY logic between UI preview and DB.
        Applies standard MET for Cardio and Hybrid TUT (Time Under Tension) for Strength training.
        """
        if category == 'Forță' and sets and reps and sets > 0 and reps > 0:
            active_time = min(duration_min, (sets * reps * 3.0) / 60.0)
            rest_time = max(0, duration_min - active_time)
            return round((met * weight * (active_time / 60.0)) + (1.5 * weight * (rest_time / 60.0)), 2)
        return round(met * weight * (duration_min / 60.0), 2)

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

            cursor.execute(
                """
                SELECT COALESCE(SUM(fl.snapshot_calories_100g * fl.quantity_g / 100.0), 0)
                FROM food_logs fl
                WHERE fl.log_id = %s AND fl.custom_meal_id IS NOT NULL
                """,
                (self.id,)
            )
            calories_from_meals = float(cursor.fetchone()[0])
            self.total_calories_in = round(calories_from_food + calories_from_meals, 2)
            
            cursor.execute(
                """
                SELECT COALESCE(
                    (
                        SELECT weight_kg
                        FROM weight_logs
                        WHERE user_id = %s AND log_date <= %s
                        ORDER BY log_date DESC
                        LIMIT 1
                    ),
                    (
                        SELECT weight_kg
                        FROM weight_logs
                        WHERE user_id = %s AND log_date > %s
                        ORDER BY log_date ASC
                        LIMIT 1
                    ),
                    70.0
                )
                """,
                (self.user_id, self.log_date, self.user_id, self.log_date)
            )
            current_weight = float(cursor.fetchone()[0])

            cursor.execute(
                """
                SELECT COALESCE(SUM(
                    CASE 
                        -- Manual wearable/cardio-machine override
                        WHEN al.manual_calories_burned IS NOT NULL THEN
                            al.manual_calories_burned
                        -- Strength Training: Hybrid TUT Model
                        WHEN a.category = 'Forță' AND al.sets IS NOT NULL AND al.reps IS NOT NULL THEN
                            (a.met_multiplier * %s * (LEAST(al.duration_min, (al.sets * al.reps * 3.0)/60.0) / 60.0)) + 
                            (1.5 * %s * (GREATEST(0, al.duration_min - ((al.sets * al.reps * 3.0)/60.0)) / 60.0))
                        -- Cardio / Other: Standard MET
                        ELSE 
                            (a.met_multiplier * %s * (al.duration_min / 60.0))
                    END
                ), 0)
                FROM activity_logs al
                JOIN activities a ON a.id = al.activity_id
                WHERE al.log_id = %s
                """,
                (current_weight, current_weight, current_weight, self.id)
            )
            self.total_calories_burned = round(float(cursor.fetchone()[0]), 2)
            
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

    @staticmethod
    def delete_if_empty(log_id: int, user_id: int) -> bool:
        """Deletes a DailyLog only when it has no food or activity entries left."""
        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM daily_logs dl
                WHERE dl.id = %s
                  AND dl.user_id = %s
                  AND NOT EXISTS (SELECT 1 FROM food_logs fl WHERE fl.log_id = dl.id)
                  AND NOT EXISTS (SELECT 1 FROM activity_logs al WHERE al.log_id = dl.id)
                RETURNING dl.id
                """,
                (log_id, user_id)
            )
            deleted_row = cursor.fetchone()
            conn.commit()
            return deleted_row is not None
        except Exception as e:
            print(f"Error deleting empty DailyLog: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_food_entries(cls, log_id: int, user_id: int = None) -> "pd.DataFrame":
        """
        Returns all FoodLog entries for a given daily_log id as a DataFrame,
        including both catalog food items and custom meals.
        When user_id is provided, the daily log must belong to that user.
        """
        conn = get_connection()
        if not conn:
            return pd.DataFrame()
        
        try:
            cursor = conn.cursor()
            user_join = "JOIN daily_logs dl ON dl.id = fl.log_id" if user_id is not None else ""
            user_filter = "AND dl.user_id = %s" if user_id is not None else ""
            params = [log_id]
            if user_id is not None:
                params.append(user_id)
            params.append(log_id)
            if user_id is not None:
                params.append(user_id)

            cursor.execute(
                f"""
                SELECT *
                FROM (
                    SELECT
                        fl.id,
                        'Aliment' AS "Tip",
                        fi.name AS "Aliment / Masă",
                        fl.quantity_g AS "Cantitate (g)",
                        ROUND(fi.calories_100g * fl.quantity_g / 100.0, 2) AS "Calorii",
                        fl.meal_type AS "Masă",
                        fl.meal_time AS "Ora"
                    FROM food_logs fl
                    {user_join}
                    JOIN food_items fi ON fi.id = fl.food_id
                    WHERE fl.log_id = %s
                      {user_filter}
                      AND fl.food_id IS NOT NULL

                    UNION ALL

                    SELECT
                        fl.id,
                        'Masă personalizată' AS "Tip",
                        fl.snapshot_name AS "Aliment / Masă",
                        fl.quantity_g AS "Cantitate (g)",
                        ROUND(fl.snapshot_calories_100g * fl.quantity_g / 100.0, 2) AS "Calorii",
                        fl.meal_type AS "Masă",
                        fl.meal_time AS "Ora"
                    FROM food_logs fl
                    {user_join}
                    JOIN custom_meals cm ON cm.id = fl.custom_meal_id
                    WHERE fl.log_id = %s
                      {user_filter}
                      AND fl.custom_meal_id IS NOT NULL
                ) entries
                ORDER BY "Ora" ASC NULLS LAST
                """,
                tuple(params)
            )
            rows = cursor.fetchall()
            if rows:
                columns = ["id", "Tip", "Aliment / Masă", "Cantitate (g)", "Calorii", "Masă", "Ora"]
                df = pd.DataFrame(rows, columns=columns)
                return df.set_index("id")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching food entries: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def get_latest_weight(user_id: int, target_date: datetime.date) -> float:
        """
        Helper method to fetch the best available user weight for a specific date.
        Useful for real-time MET calorie estimations in the UI.
        """
        from .weight_log import WeightLog

        return WeightLog.get_latest_for_user(user_id, target_date)

    @classmethod
    def get_activity_entries(cls, log_id: int, user_id: int = None) -> "pd.DataFrame":
        """
        Returns all ActivityLog entries for a given daily_log id as a DataFrame,
        joined with activities to show names, categories, and calculated burned calories.
        When user_id is provided, the daily log must belong to that user.
        """
        conn = get_connection()
        if not conn:
            return pd.DataFrame()
        
        try:
            cursor = conn.cursor()
            # We use a CTE to get the user's latest weight relative to the log_date
            # to dynamically calculate the burned calories per activity row.
            user_filter = "AND user_id = %s" if user_id is not None else ""
            params = [log_id]
            if user_id is not None:
                params.append(user_id)
            params.append(log_id)

            cursor.execute(
                f"""
                WITH user_info AS (
                    SELECT user_id, log_date FROM daily_logs WHERE id = %s {user_filter}
                ),
                latest_weight AS (
                    SELECT COALESCE(
                        (SELECT weight_kg FROM weight_logs
                         WHERE user_id = (SELECT user_id FROM user_info)
                         AND log_date <= (SELECT log_date FROM user_info)
                         ORDER BY log_date DESC LIMIT 1),
                        (SELECT weight_kg FROM weight_logs
                         WHERE user_id = (SELECT user_id FROM user_info)
                         AND log_date > (SELECT log_date FROM user_info)
                         ORDER BY log_date ASC LIMIT 1),
                        70.0) AS weight
                )
                SELECT 
                    al.id, 
                    a.id AS "_activity_id",
                    a.name AS "Activitate",
                    a.category AS "Categorie",
                    al.duration_min AS "Durată (min)",
                    al.sets AS "Seturi",
                    al.reps AS "Repetări",
                    al.manual_calories_burned AS "_manual_calories_burned",
                    CASE
                        WHEN al.manual_calories_burned IS NOT NULL THEN 'Manual'
                        ELSE 'Estimare MacroSense'
                    END AS "Metodă calcul",
                    ROUND(
                        CASE 
                            WHEN al.manual_calories_burned IS NOT NULL THEN
                                al.manual_calories_burned
                            WHEN a.category = 'Forță' AND al.sets IS NOT NULL AND al.reps IS NOT NULL THEN
                                (a.met_multiplier * (SELECT weight FROM latest_weight) * (LEAST(al.duration_min, (al.sets * al.reps * 3.0)/60.0) / 60.0)) + 
                                (1.5 * (SELECT weight FROM latest_weight) * (GREATEST(0, al.duration_min - ((al.sets * al.reps * 3.0)/60.0)) / 60.0))
                            ELSE 
                                (a.met_multiplier * (SELECT weight FROM latest_weight) * (al.duration_min / 60.0))
                        END
                    , 2) AS "Calorii Arse"
                FROM activity_logs al
                JOIN activities a ON a.id = al.activity_id
                WHERE al.log_id = %s
                  AND EXISTS (SELECT 1 FROM user_info)
                ORDER BY al.id ASC
                """,
                tuple(params)
            )
            rows = cursor.fetchall()
            if rows:
                columns = [
                    "id",
                    "_activity_id",
                    "Activitate",
                    "Categorie",
                    "Durată (min)",
                    "Seturi",
                    "Repetări",
                    "_manual_calories_burned",
                    "Metodă calcul",
                    "Calorii Arse",
                ]
                df = pd.DataFrame(rows, columns=columns)
                df['Seturi'] = df['Seturi'].apply(format_optional_activity_count)
                df['Repetări'] = df['Repetări'].apply(format_optional_activity_count)
                return df.set_index("id")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching activity entries: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()
