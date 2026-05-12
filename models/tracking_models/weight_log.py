import datetime
import pandas as pd
from database import get_connection


class WeightLog:
    """
    Represents a user's measured body weight for a specific date.
    Used by MET calculations, progress charts, and future ML features.
    """
    MIN_WEIGHT_KG = 30.0
    MAX_WEIGHT_KG = 300.0

    def __init__(self, user_id: int, log_date: datetime.date, weight_kg: float, log_entry_id: int = None):
        self.id = log_entry_id
        self.user_id = user_id
        self.log_date = log_date
        self.weight_kg = weight_kg

        if self.user_id is None or self.user_id <= 0:
            raise ValueError("WeightLog user_id must be a positive integer.")
        self.log_date = self.validate_log_date(self.log_date)
        if self.weight_kg <= 0:
            raise ValueError("WeightLog weight must be strictly positive.")
        if not self.MIN_WEIGHT_KG <= self.weight_kg <= self.MAX_WEIGHT_KG:
            raise ValueError("WeightLog weight must be between 30 and 300 kg.")

    @staticmethod
    def validate_log_date(log_date: datetime.date) -> datetime.date:
        """Validates that weight journal rows are not dated in the future."""
        if isinstance(log_date, datetime.datetime):
            log_date = log_date.date()
        if not isinstance(log_date, datetime.date):
            raise ValueError("WeightLog log_date must be a valid date.")
        if log_date > datetime.date.today():
            raise ValueError("WeightLog log_date cannot be in the future.")
        return log_date

    def save(self) -> bool:
        """
        Saves the weight entry. If the user already has an entry for the same date,
        updates it to preserve the one-weight-per-day database rule.
        """
        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO weight_logs (user_id, log_date, weight_kg)
                VALUES (%s, %s, %s)
                ON CONFLICT ON CONSTRAINT uq_weight_log
                DO UPDATE SET weight_kg = EXCLUDED.weight_kg
                RETURNING id
                """,
                (self.user_id, self.log_date, self.weight_kg)
            )
            self.id = cursor.fetchone()[0]
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving weight log: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def update(cls, log_entry_id: int, user_id: int, log_date: datetime.date, weight_kg: float) -> bool:
        """Updates a WeightLog entry only if it belongs to the given user."""
        log_date = cls.validate_log_date(log_date)
        if weight_kg <= 0:
            raise ValueError("WeightLog weight must be strictly positive.")
        if not cls.MIN_WEIGHT_KG <= weight_kg <= cls.MAX_WEIGHT_KG:
            raise ValueError("WeightLog weight must be between 30 and 300 kg.")

        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE weight_logs
                SET log_date = %s,
                    weight_kg = %s
                WHERE id = %s
                  AND user_id = %s
                RETURNING id
                """,
                (log_date, weight_kg, log_entry_id, user_id)
            )
            updated_row = cursor.fetchone()
            conn.commit()
            return updated_row is not None
        except Exception as e:
            print(f"Error updating weight log: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def delete(cls, log_entry_id: int, user_id: int) -> bool:
        """Deletes a WeightLog entry only if it belongs to the user and is not the last one."""
        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM weight_logs WHERE user_id = %s",
                (user_id,)
            )
            entry_count = cursor.fetchone()[0]
            if entry_count <= 1:
                return False

            cursor.execute(
                """
                DELETE FROM weight_logs
                WHERE id = %s
                  AND user_id = %s
                RETURNING id
                """,
                (log_entry_id, user_id)
            )
            deleted_row = cursor.fetchone()
            conn.commit()
            return deleted_row is not None
        except Exception as e:
            print(f"Error deleting weight log: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_user_entries(cls, user_id: int) -> pd.DataFrame:
        """Returns the user's weight history ordered by date descending."""
        conn = get_connection()
        if not conn:
            return pd.DataFrame()

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, log_date, weight_kg
                FROM weight_logs
                WHERE user_id = %s
                ORDER BY log_date DESC, id DESC
                """,
                (user_id,)
            )
            rows = cursor.fetchall()
            if rows:
                formatted_rows = [
                    (row[0], row[1], float(row[2]))
                    for row in rows
                ]
                columns = ["id", "Data", "Greutate (kg)"]
                return pd.DataFrame(formatted_rows, columns=columns).set_index("id")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching weight logs: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_reference_for_user(user_id: int, target_date: datetime.date, fallback_weight: float = 70.0) -> dict:
        """
        Returns the most relevant weight for a target date.
        Priority: latest weight on/before date, earliest later weight, fallback only if no history exists.
        """
        conn = get_connection()
        if not conn:
            return {
                "weight": fallback_weight,
                "source_date": None,
                "uses_future_reference": False,
                "uses_fallback": True,
            }

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT weight_kg,
                       log_date,
                       CASE WHEN log_date > %s THEN TRUE ELSE FALSE END AS uses_future_reference
                FROM weight_logs
                WHERE user_id = %s
                ORDER BY
                    CASE WHEN log_date <= %s THEN 0 ELSE 1 END,
                    CASE WHEN log_date <= %s THEN log_date END DESC,
                    CASE WHEN log_date > %s THEN log_date END ASC
                LIMIT 1
                """,
                (target_date, user_id, target_date, target_date, target_date)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "weight": float(row[0]),
                    "source_date": row[1],
                    "uses_future_reference": bool(row[2]),
                    "uses_fallback": False,
                }
            return {
                "weight": fallback_weight,
                "source_date": None,
                "uses_future_reference": False,
                "uses_fallback": True,
            }
        except Exception as e:
            print(f"Error fetching weight reference: {e}")
            return {
                "weight": fallback_weight,
                "source_date": None,
                "uses_future_reference": False,
                "uses_fallback": True,
            }
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_latest_for_user(user_id: int, target_date: datetime.date, fallback_weight: float = 70.0) -> float:
        """Returns the best available weight for target_date, with a safe fallback."""
        return WeightLog.get_reference_for_user(user_id, target_date, fallback_weight)["weight"]

    @staticmethod
    def get_activity_day_weight_references(user_id: int, fallback_weight: float = 70.0) -> dict:
        """
        Returns the weight reference currently used by each activity day.
        Keys are daily_log IDs; values capture both source row and numeric weight.
        """
        conn = get_connection()
        if not conn:
            return {}

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    dl.id,
                    COALESCE(past_weight.id, future_weight.id, 0) AS reference_id,
                    COALESCE(past_weight.weight_kg, future_weight.weight_kg, %s) AS reference_weight
                FROM daily_logs dl
                LEFT JOIN LATERAL (
                    SELECT wl.id, wl.weight_kg
                    FROM weight_logs wl
                    WHERE wl.user_id = dl.user_id
                      AND wl.log_date <= dl.log_date
                    ORDER BY wl.log_date DESC, wl.id DESC
                    LIMIT 1
                ) past_weight ON TRUE
                LEFT JOIN LATERAL (
                    SELECT wl.id, wl.weight_kg
                    FROM weight_logs wl
                    WHERE wl.user_id = dl.user_id
                      AND wl.log_date > dl.log_date
                    ORDER BY wl.log_date ASC, wl.id ASC
                    LIMIT 1
                ) future_weight ON past_weight.id IS NULL
                WHERE dl.user_id = %s
                  AND EXISTS (
                      SELECT 1
                      FROM activity_logs al
                      WHERE al.log_id = dl.id
                        AND al.manual_calories_burned IS NULL
                  )
                ORDER BY dl.log_date ASC
                """,
                (fallback_weight, user_id)
            )
            rows = cursor.fetchall()
            return {
                int(row[0]): (int(row[1]), round(float(row[2]), 2))
                for row in rows
            }
        except Exception as e:
            print(f"Error fetching activity day weight references: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_changed_reference_ids(before_references: dict, after_references: dict) -> set:
        """Returns daily_log IDs whose weight reference changed between snapshots."""
        changed_ids = set()
        all_ids = set(before_references.keys()) | set(after_references.keys())

        for daily_log_id in all_ids:
            if before_references.get(daily_log_id) != after_references.get(daily_log_id):
                changed_ids.add(daily_log_id)

        return changed_ids

    @classmethod
    def recalculate_user_daily_logs(cls, user_id: int, before_references: dict = None) -> int:
        """Recalculates DailyLog rows that contain activities affected by weight-based MET."""
        from .daily_log import DailyLog

        affected_daily_log_ids = None
        if before_references is not None:
            after_references = cls.get_activity_day_weight_references(user_id)
            affected_daily_log_ids = cls.get_changed_reference_ids(before_references, after_references)
            if not affected_daily_log_ids:
                return 0

        conn = get_connection()
        if not conn:
            return 0

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, log_date, total_calories_in, total_calories_burned
                FROM daily_logs dl
                WHERE dl.user_id = %s
                  AND EXISTS (
                      SELECT 1
                      FROM activity_logs al
                      WHERE al.log_id = dl.id
                        AND al.manual_calories_burned IS NULL
                  )
                ORDER BY dl.log_date ASC
                """,
                (user_id,)
            )
            rows = cursor.fetchall()
        except Exception as e:
            print(f"Error fetching daily logs for weight recalculation: {e}")
            return 0
        finally:
            if conn:
                conn.close()

        recalculated_count = 0
        for row in rows:
            if affected_daily_log_ids is not None and int(row[0]) not in affected_daily_log_ids:
                continue

            daily_log = DailyLog(
                log_id=row[0],
                user_id=row[1],
                log_date=row[2],
                total_calories_in=float(row[3]),
                total_calories_burned=float(row[4])
            )
            if daily_log.recalculate_totals():
                recalculated_count += 1

        return recalculated_count
