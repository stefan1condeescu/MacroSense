from database import get_connection

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
        self.validate_sets_and_reps(self.sets, self.reps)

    @staticmethod
    def validate_sets_and_reps(sets: int = None, reps: int = None) -> None:
        """Validates optional strength-training details consistently for save and update flows."""
        if (sets is None) != (reps is None):
            raise ValueError("Sets and reps must be provided together.")
        if sets is not None and (sets <= 0 or reps <= 0):
            raise ValueError("Sets and reps must be strictly positive when provided.")

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
    def update(cls, log_entry_id: int, user_id: int, activity_id: int, duration_min: int, sets: int = None, reps: int = None) -> bool:
        """Updates editable ActivityLog fields only if the entry belongs to the given user."""
        if duration_min <= 0:
            raise ValueError("Duration must be strictly positive for MET calculation.")
        cls.validate_sets_and_reps(sets, reps)

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
                    reps = %s
                FROM daily_logs dl
                WHERE al.log_id = dl.id
                  AND al.id = %s
                  AND dl.user_id = %s
                RETURNING al.id
                """,
                (activity_id, duration_min, sets, reps, log_entry_id, user_id)
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
