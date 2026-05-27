import re
import unicodedata

import pandas as pd
from database import get_connection
from models.text_validation import contains_letter, has_obvious_html_chars

class Activity:
    """Represents a physical activity in the catalog."""
    MIN_MET_MULTIPLIER = 0.9
    ESTIMATION_METHODS = {
        "official_compendium": "Oficial Compendium",
        "compendium_mapping": "Mapare MacroSense",
        "manual_admin": "Manual Admin",
    }

    def __init__(
        self,
        name: str,
        met_multiplier: float,
        category: str,
        activity_id: int = None,
        source: str = None,
        source_type: str = None,
        external_id: str = None,
        source_url: str = None,
        met_source_code: str = None,
        met_source_description: str = None,
        met_estimation_method: str = "manual_admin",
    ):
        self.id = activity_id
        self.name = name.strip() if name else ""
        self.met_multiplier = float(met_multiplier or 0)
        self.category = category.strip() if category else ""
        self.source = source.strip() if source else None
        self.source_type = source_type.strip() if source_type else None
        self.external_id = str(external_id).strip() if external_id else None
        self.source_url = source_url.strip() if source_url else None
        self.met_source_code = str(met_source_code).strip() if met_source_code else None
        self.met_source_description = met_source_description.strip() if met_source_description else None
        self.met_estimation_method = (met_estimation_method or "manual_admin").strip()

        if not self.name:
            raise ValueError("Activity name cannot be empty.")
        if has_obvious_html_chars(self.name):
            raise ValueError("Activity name cannot contain HTML-like characters.")
        if not contains_letter(self.name):
            raise ValueError("Activity name must contain at least one letter.")
        if self.met_multiplier < self.MIN_MET_MULTIPLIER:
            raise ValueError("Activity MET multiplier is below the supported minimum.")
        if not self.category:
            raise ValueError("Activity category cannot be empty.")
        if self.met_estimation_method not in self.ESTIMATION_METHODS:
            raise ValueError("Activity MET estimation method is not supported.")

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalizes names for duplicate checks without depending on DB collation."""
        value = unicodedata.normalize("NFKD", name or "")
        ascii_value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", ascii_value).strip().lower()

    @classmethod
    def name_exists_normalized(cls, name: str) -> bool:
        """Checks duplicate activity names in a diacritic-insensitive way."""
        normalized_name = cls.normalize_name(name)
        if not normalized_name:
            return False

        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM activities")
            return any(cls.normalize_name(row[0]) == normalized_name for row in cursor.fetchall())
        except Exception as e:
            print(f"Error checking activity duplicate name: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def external_reference_exists(source: str, external_id) -> bool:
        """Checks whether a source/external ID pair is already present in the catalog."""
        if not source or external_id in (None, ""):
            return False

        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1
                FROM activities
                WHERE source = %s AND external_id = %s
                LIMIT 1
                """,
                (source, str(external_id))
            )
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error checking activity external reference: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_estimation_label(cls, method: str) -> str:
        """Returns the Romanian UI label for the internal MET estimation method."""
        return cls.ESTIMATION_METHODS.get(method, "Necunoscut")

    def save(self) -> bool:
        """Saves the Activity object state to the PostgreSQL database."""
        if self.name_exists_normalized(self.name):
            print("Error saving activity: duplicate activity name.")
            return False

        conn = get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO activities (
                    name, met_multiplier, category,
                    source, source_type, external_id, source_url,
                    met_source_code, met_source_description, met_estimation_method
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    self.name,
                    self.met_multiplier,
                    self.category,
                    self.source,
                    self.source_type,
                    self.external_id,
                    self.source_url,
                    self.met_source_code,
                    self.met_source_description,
                    self.met_estimation_method,
                )
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
            cursor.execute(
                """
                SELECT
                    name,
                    met_multiplier,
                    category,
                    CASE
                        WHEN source = 'Compendium' THEN 'Compendium'
                        ELSE 'MacroSense'
                    END AS source_label,
                    met_estimation_method
                FROM activities
                ORDER BY name ASC
                """
            )
            rows = cursor.fetchall()
            if rows:
                formatted_rows = [
                    (row[0], float(row[1]), row[2], row[3], cls.get_estimation_label(row[4]))
                    for row in rows
                ]
                columns = ["Denumire", "Coeficient MET", "Categorie", "Sursă", "Metodă MET"]
                return pd.DataFrame(formatted_rows, columns=columns)
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
                SELECT
                    id,
                    name,
                    met_multiplier,
                    category,
                    CASE
                        WHEN source = 'Compendium' THEN 'Compendium'
                        ELSE 'MacroSense'
                    END AS source_label,
                    met_estimation_method,
                    met_source_code,
                    met_source_description
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
                    "source_label": row[4],
                    "met_estimation_method": row[5],
                    "met_method_label": cls.get_estimation_label(row[5]),
                    "met_source_code": row[6],
                    "met_source_description": row[7],
                }
            return options
        except Exception as e:
            print(f"Error fetching activity catalog options: {e}")
            return {}
        finally:
            if conn:
                conn.close()
