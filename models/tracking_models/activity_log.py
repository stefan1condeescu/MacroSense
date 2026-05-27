from database import get_connection

class ActivityLog:
    """Represents a physical activity event logged for a day."""
    MIN_MANUAL_CALORIES_BURNED = 1.0
    MAX_MANUAL_CALORIES_BURNED = 5000.0
    MIN_DURATION_MINUTES = 0.1
    MAX_DURATION_MINUTES = 600.0
    MIN_SETS = 1
    MAX_SETS = 50
    MIN_REPS = 1
    MAX_REPS = 200

    def __init__(
        self,
        log_id: int,
        activity_id: int,
        duration_min: float,
        sets: int = None,
        reps: int = None,
        log_entry_id: int = None,
        manual_calories_burned: float = None,
    ):
        self.id = log_entry_id
        self.log_id = log_id
        self.activity_id = activity_id
        try:
            self.duration_min = float(duration_min)
        except (TypeError, ValueError):
            raise ValueError("Duration must be a valid number.")
        self.sets = sets
        self.reps = reps
        self.manual_calories_burned = (
            float(manual_calories_burned)
            if manual_calories_burned is not None
            else None
        )

        self.validate_duration(self.duration_min)
        self.validate_sets_and_reps(self.sets, self.reps)
        self.validate_manual_calories(self.manual_calories_burned)

    @classmethod
    def validate_duration(cls, duration_min: float) -> None:
        """Validates supported activity duration consistently for save and update flows."""
        try:
            duration_value = float(duration_min)
        except (TypeError, ValueError):
            raise ValueError("Duration must be a valid number.")
        if duration_value < cls.MIN_DURATION_MINUTES:
            raise ValueError("Duration must be strictly positive for MET calculation.")
        if duration_value > cls.MAX_DURATION_MINUTES:
            raise ValueError("Duration is above the supported maximum.")

    @classmethod
    def validate_sets_and_reps(cls, sets: int = None, reps: int = None) -> None:
        """Validates optional strength-training details consistently for save and update flows."""
        if (sets is None) != (reps is None):
            raise ValueError("Sets and reps must be provided together.")
        if sets is None and reps is None:
            return

        try:
            sets_value = int(sets)
            reps_value = int(reps)
        except (TypeError, ValueError):
            raise ValueError("Sets and reps must be valid integers.") from None

        if sets_value != sets or reps_value != reps:
            raise ValueError("Sets and reps must be whole numbers.")
        if sets_value <= 0 or reps_value <= 0:
            raise ValueError("Sets and reps must be strictly positive when provided.")
        if not cls.MIN_SETS <= sets_value <= cls.MAX_SETS:
            raise ValueError("Sets are outside the supported range.")
        if not cls.MIN_REPS <= reps_value <= cls.MAX_REPS:
            raise ValueError("Reps are outside the supported range.")

    @classmethod
    def validate_manual_calories(cls, manual_calories_burned: float = None) -> None:
        """Validates optional calories imported from a wearable or cardio machine."""
        if manual_calories_burned is None:
            return
        if not cls.MIN_MANUAL_CALORIES_BURNED <= float(manual_calories_burned) <= cls.MAX_MANUAL_CALORIES_BURNED:
            raise ValueError("Manual calories burned must be between 1 and 5000.")

    def save(self) -> bool:
        """Saves the ActivityLog entry to the PostgreSQL database."""
        conn = get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO activity_logs (
                    log_id, activity_id, duration_min, sets, reps, manual_calories_burned
                )
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (
                    self.log_id,
                    self.activity_id,
                    self.duration_min,
                    self.sets,
                    self.reps,
                    self.manual_calories_burned,
                )
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

    @classmethod
    def delete(cls, log_entry_id: int, user_id: int) -> bool:
        """Deletes an ActivityLog entry only if it belongs to the given user."""
        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM activity_logs al
                USING daily_logs dl
                WHERE al.log_id = dl.id
                  AND al.id = %s
                  AND dl.user_id = %s
                RETURNING al.id
                """,
                (log_entry_id, user_id)
            )
            deleted_row = cursor.fetchone()
            conn.commit()
            return deleted_row is not None
        except Exception as e:
            print(f"Error deleting activity log: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def update(
        cls,
        log_entry_id: int,
        user_id: int,
        activity_id: int,
        duration_min: float,
        sets: int = None,
        reps: int = None,
        manual_calories_burned: float = None,
    ) -> bool:
        """Updates editable ActivityLog fields only if the entry belongs to the given user."""
        cls.validate_duration(duration_min)
        cls.validate_sets_and_reps(sets, reps)
        cls.validate_manual_calories(manual_calories_burned)

        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE activity_logs al
                SET activity_id = %s,
                    duration_min = %s,
                    sets = %s,
                    reps = %s,
                    manual_calories_burned = %s
                FROM daily_logs dl
                WHERE al.log_id = dl.id
                  AND al.id = %s
                  AND dl.user_id = %s
                RETURNING al.id
                """,
                (activity_id, duration_min, sets, reps, manual_calories_burned, log_entry_id, user_id)
            )
            updated_row = cursor.fetchone()
            conn.commit()
            return updated_row is not None
        except Exception as e:
            print(f"Error updating activity log: {e}")
            return False
        finally:
            if conn:
                conn.close()
