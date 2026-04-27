import pandas as pd
from database import get_connection

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
        except Exception as e:
            print(f"Error fetching activities: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_catalog_options(cls) -> dict:
        """Fetches activities as option metadata for reactive UI selectors."""
        conn = get_connection()
        if not conn:
            return {}

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, met_multiplier, category
                FROM activities
                ORDER BY name ASC
                """
            )
            options = {}
            for row in cursor.fetchall():
                options[row[0]] = {
                    "id": row[0],
                    "name": row[1],
                    "met": float(row[2] or 0),
                    "category": row[3],
                }
            return options
        except Exception as e:
            print(f"Error fetching activity catalog options: {e}")
            return {}
        finally:
            if conn:
                conn.close()
