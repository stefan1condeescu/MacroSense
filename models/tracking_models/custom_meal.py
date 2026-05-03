import pandas as pd
from database import get_connection
from .recipe_ingredient import RecipeIngredient

class CustomMeal:
    """
    Represents a reusable user-defined meal composed of catalog food items.
    """
    ACTIVE_STATUS = "Salvată"
    ARCHIVED_STATUS = "Arhivată"

    def __init__(self, user_id: int, recipe_name: str, status: str = "Salvată", meal_id: int = None):
        self.id = meal_id
        self.user_id = user_id
        self.recipe_name = recipe_name.strip() if recipe_name else ""
        self.status = status

        if not self.recipe_name:
            raise ValueError("Custom meal name cannot be empty.")
        if not self.is_valid_recipe_name(self.recipe_name):
            raise ValueError("Custom meal name must start with a letter.")

    @staticmethod
    def is_valid_recipe_name(recipe_name: str) -> bool:
        """Checks that a custom meal name starts with a letter and is not HTML-like markup."""
        cleaned_name = recipe_name.strip() if recipe_name else ""
        return bool(cleaned_name) and cleaned_name[0].isalpha() and "<" not in cleaned_name and ">" not in cleaned_name

    def save(self) -> bool:
        """Saves the custom meal header and updates the instance with the generated ID."""
        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO custom_meals (user_id, recipe_name, status)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (self.user_id, self.recipe_name, self.status)
            )
            self.id = cursor.fetchone()[0]
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving custom meal: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def add_ingredient(self, food_id: int, quantity_g: float) -> bool:
        """Adds a food item ingredient to an existing custom meal."""
        if not self.id:
            return False

        ingredient = RecipeIngredient(self.id, food_id, quantity_g)
        return ingredient.save()

    @classmethod
    def create_with_ingredients(cls, user_id: int, recipe_name: str, ingredients: list, status: str = "Salvată") -> "CustomMeal | None":
        """Creates a custom meal and all its ingredients in a single transaction."""
        meal_name = recipe_name.strip() if recipe_name else ""
        if not meal_name or not cls.is_valid_recipe_name(meal_name) or not ingredients:
            return None

        conn = get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO custom_meals (user_id, recipe_name, status)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (user_id, meal_name, status)
            )
            meal_id = cursor.fetchone()[0]

            for ingredient in ingredients:
                quantity_g = float(ingredient["quantity_g"])
                RecipeIngredient.validate_quantity(quantity_g)
                cursor.execute(
                    """
                    INSERT INTO recipe_ingredients (meal_id, food_id, quantity_g)
                    VALUES (%s, %s, %s)
                    """,
                    (meal_id, ingredient["food_id"], quantity_g)
                )

            conn.commit()
            return cls(user_id=user_id, recipe_name=meal_name, status=status, meal_id=meal_id)
        except Exception as e:
            print(f"Error creating custom meal with ingredients: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

    @classmethod
    def update_with_ingredients(cls, meal_id: int, user_id: int, recipe_name: str, ingredients: list, status: str = None) -> bool:
        """Updates a user's custom meal and replaces its ingredients in a single transaction."""
        meal_name = recipe_name.strip() if recipe_name else ""
        if not meal_name or not cls.is_valid_recipe_name(meal_name) or not ingredients:
            return False
        if status is not None and status not in (cls.ACTIVE_STATUS, cls.ARCHIVED_STATUS):
            return False

        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE custom_meals
                SET recipe_name = %s,
                    status = COALESCE(%s, status)
                WHERE id = %s AND user_id = %s
                RETURNING id
                """,
                (meal_name, status, meal_id, user_id)
            )
            updated_row = cursor.fetchone()
            if not updated_row:
                conn.rollback()
                return False

            cursor.execute(
                """
                DELETE FROM recipe_ingredients
                WHERE meal_id = %s
                """,
                (meal_id,)
            )

            for ingredient in ingredients:
                quantity_g = float(ingredient["quantity_g"])
                RecipeIngredient.validate_quantity(quantity_g)
                cursor.execute(
                    """
                    INSERT INTO recipe_ingredients (meal_id, food_id, quantity_g)
                    VALUES (%s, %s, %s)
                    """,
                    (meal_id, ingredient["food_id"], quantity_g)
                )

            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating custom meal with ingredients: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_affected_daily_log_ids(cls, meal_id: int, user_id: int) -> list:
        """Returns daily log IDs that reference a custom meal for the given user."""
        conn = get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT dl.id
                FROM daily_logs dl
                JOIN food_logs fl ON fl.log_id = dl.id
                WHERE dl.user_id = %s AND fl.custom_meal_id = %s
                """,
                (user_id, meal_id)
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching affected daily logs for custom meal: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def calculate_total_macros(self) -> dict:
        """Calculates total calories and macronutrients for the full recipe."""
        if not self.id:
            return {
                "quantity_g": 0.0,
                "calories": 0.0,
                "protein_g": 0.0,
                "carbs_g": 0.0,
                "fats_g": 0.0,
            }

        return self.calculate_total_macros_by_id(self.id)

    def calculateTotalMacros(self) -> dict:
        """Compatibility method matching the UML class diagram naming."""
        return self.calculate_total_macros()

    @staticmethod
    def calculate_total_macros_by_id(meal_id: int) -> dict:
        """Calculates total calories and macronutrients for a custom meal by ID."""
        conn = get_connection()
        if not conn:
            return {
                "quantity_g": 0.0,
                "calories": 0.0,
                "protein_g": 0.0,
                "carbs_g": 0.0,
                "fats_g": 0.0,
            }

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(ri.quantity_g), 0) AS total_quantity_g,
                    COALESCE(SUM(fi.calories_100g * ri.quantity_g / 100.0), 0) AS total_calories,
                    COALESCE(SUM(fi.protein_g * ri.quantity_g / 100.0), 0) AS total_protein_g,
                    COALESCE(SUM(fi.carbs_g * ri.quantity_g / 100.0), 0) AS total_carbs_g,
                    COALESCE(SUM(fi.fats_g * ri.quantity_g / 100.0), 0) AS total_fats_g
                FROM recipe_ingredients ri
                JOIN food_items fi ON fi.id = ri.food_id
                WHERE ri.meal_id = %s
                """,
                (meal_id,)
            )
            row = cursor.fetchone()
            return {
                "quantity_g": round(float(row[0]), 2),
                "calories": round(float(row[1]), 2),
                "protein_g": round(float(row[2]), 2),
                "carbs_g": round(float(row[3]), 2),
                "fats_g": round(float(row[4]), 2),
            }
        except Exception as e:
            print(f"Error calculating custom meal macros: {e}")
            return {
                "quantity_g": 0.0,
                "calories": 0.0,
                "protein_g": 0.0,
                "carbs_g": 0.0,
                "fats_g": 0.0,
            }
        finally:
            if conn:
                conn.close()

    @classmethod
    def set_status(cls, meal_id: int, user_id: int, status: str) -> bool:
        """Updates the status of a custom meal only if it belongs to the given user."""
        if status not in (cls.ACTIVE_STATUS, cls.ARCHIVED_STATUS):
            return False

        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE custom_meals
                SET status = %s
                WHERE id = %s AND user_id = %s
                RETURNING id
                """,
                (status, meal_id, user_id)
            )
            updated_row = cursor.fetchone()
            conn.commit()
            return updated_row is not None
        except Exception as e:
            print(f"Error updating custom meal status: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def archive(cls, meal_id: int, user_id: int) -> bool:
        """Archives a custom meal without deleting historical food log entries."""
        return cls.set_status(meal_id, user_id, cls.ARCHIVED_STATUS)

    @classmethod
    def restore(cls, meal_id: int, user_id: int) -> bool:
        """Restores an archived custom meal so it can be used again."""
        return cls.set_status(meal_id, user_id, cls.ACTIVE_STATUS)

    @classmethod
    def get_user_meal_options(cls, user_id: int, include_archived: bool = False) -> dict:
        """Fetches custom meals for a user as option metadata for selectors."""
        conn = get_connection()
        if not conn:
            return {}

        try:
            cursor = conn.cursor()
            status_filter = "" if include_archived else "AND (cm.status IS NULL OR cm.status = %s)"
            params = [user_id]
            if not include_archived:
                params.append(cls.ACTIVE_STATUS)

            cursor.execute(
                f"""
                WITH meal_totals AS (
                    SELECT
                        ri.meal_id,
                        COALESCE(SUM(ri.quantity_g), 0) AS total_quantity_g,
                        COALESCE(SUM(fi.calories_100g * ri.quantity_g / 100.0), 0) AS total_calories,
                        COALESCE(SUM(fi.protein_g * ri.quantity_g / 100.0), 0) AS total_protein_g,
                        COALESCE(SUM(fi.carbs_g * ri.quantity_g / 100.0), 0) AS total_carbs_g,
                        COALESCE(SUM(fi.fats_g * ri.quantity_g / 100.0), 0) AS total_fats_g
                    FROM recipe_ingredients ri
                    JOIN food_items fi ON fi.id = ri.food_id
                    GROUP BY ri.meal_id
                )
                SELECT
                    cm.id,
                    cm.recipe_name,
                    cm.status,
                    COALESCE(mt.total_quantity_g, 0),
                    COALESCE(mt.total_calories, 0),
                    COALESCE(mt.total_protein_g, 0),
                    COALESCE(mt.total_carbs_g, 0),
                    COALESCE(mt.total_fats_g, 0)
                FROM custom_meals cm
                LEFT JOIN meal_totals mt ON mt.meal_id = cm.id
                WHERE cm.user_id = %s
                  {status_filter}
                ORDER BY cm.recipe_name ASC
                """,
                tuple(params)
            )
            options = {}
            for row in cursor.fetchall():
                total_quantity_g = float(row[3] or 0)
                total_calories = float(row[4] or 0)
                calories_per_g = total_calories / total_quantity_g if total_quantity_g > 0 else 0.0
                options[row[0]] = {
                    "id": row[0],
                    "recipe_name": row[1],
                    "status": row[2] or cls.ACTIVE_STATUS,
                    "quantity_g": total_quantity_g,
                    "calories": total_calories,
                    "protein_g": float(row[5] or 0),
                    "carbs_g": float(row[6] or 0),
                    "fats_g": float(row[7] or 0),
                    "calories_per_g": calories_per_g,
                }
            return options
        except Exception as e:
            print(f"Error fetching custom meal options: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_all_as_dataframe(cls, user_id: int, include_archived: bool = True) -> pd.DataFrame:
        """Fetches all custom meals for a user as a pandas DataFrame."""
        meal_options = cls.get_user_meal_options(user_id, include_archived=include_archived)
        if not meal_options:
            return pd.DataFrame()

        rows = []
        for meal in meal_options.values():
            rows.append([
                meal["id"],
                meal["recipe_name"],
                round(meal["quantity_g"], 2),
                round(meal["calories"], 2),
                round(meal["protein_g"], 2),
                round(meal["carbs_g"], 2),
                round(meal["fats_g"], 2),
                meal["status"],
            ])
        columns = ["id", "Denumire", "Cantitate totală (g)", "Calorii", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)", "Status"]
        return pd.DataFrame(rows, columns=columns).set_index("id")

    @classmethod
    def get_ingredients(cls, meal_id: int, user_id: int) -> list:
        """Fetches a user's custom meal ingredients as structured dictionaries."""
        conn = get_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    ri.id,
                    fi.id,
                    fi.name,
                    ri.quantity_g,
                    fi.calories_100g,
                    fi.protein_g,
                    fi.carbs_g,
                    fi.fats_g,
                    COALESCE(
                        CASE
                            WHEN fi.source = 'USDA' AND fi.source_type = 'SR Legacy' THEN 'USDA SR'
                            WHEN fi.source = 'USDA' AND fi.source_type = 'Foundation' THEN 'USDA Foundation'
                            WHEN fi.source = 'USDA' AND fi.source_type = 'Survey (FNDDS)' THEN 'USDA FNDDS'
                            WHEN fi.source IS NOT NULL AND fi.source_type IS NOT NULL THEN fi.source || ' ' || fi.source_type
                            WHEN fi.source IS NOT NULL THEN fi.source
                            ELSE NULL
                        END,
                        'MacroSense'
                    ) AS source_label
                FROM recipe_ingredients ri
                JOIN food_items fi ON fi.id = ri.food_id
                JOIN custom_meals cm ON cm.id = ri.meal_id
                WHERE ri.meal_id = %s AND cm.user_id = %s
                ORDER BY fi.name ASC, ri.id ASC
                """,
                (meal_id, user_id)
            )
            ingredients = []
            for row in cursor.fetchall():
                ingredients.append({
                    "ingredient_id": row[0],
                    "food_id": row[1],
                    "name": row[2],
                    "quantity_g": float(row[3]),
                    "calories_100g": float(row[4] or 0),
                    "protein_g": float(row[5] or 0),
                    "carbs_g": float(row[6] or 0),
                    "fats_g": float(row[7] or 0),
                    "source_label": row[8] or "MacroSense",
                })
            return ingredients
        except Exception as e:
            print(f"Error fetching custom meal ingredient objects: {e}")
            return []
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_ingredients_as_dataframe(cls, meal_id: int, user_id: int) -> pd.DataFrame:
        """Fetches the ingredient list for a user's custom meal."""
        conn = get_connection()
        if not conn:
            return pd.DataFrame()

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    fi.name,
                    COALESCE(
                        CASE
                            WHEN fi.source = 'USDA' AND fi.source_type = 'SR Legacy' THEN 'USDA SR'
                            WHEN fi.source = 'USDA' AND fi.source_type = 'Foundation' THEN 'USDA Foundation'
                            WHEN fi.source = 'USDA' AND fi.source_type = 'Survey (FNDDS)' THEN 'USDA FNDDS'
                            WHEN fi.source IS NOT NULL AND fi.source_type IS NOT NULL THEN fi.source || ' ' || fi.source_type
                            WHEN fi.source IS NOT NULL THEN fi.source
                            ELSE NULL
                        END,
                        'MacroSense'
                    ) AS source_label,
                    ri.quantity_g,
                    ROUND(fi.calories_100g * ri.quantity_g / 100.0, 2),
                    ROUND(fi.protein_g * ri.quantity_g / 100.0, 2),
                    ROUND(fi.carbs_g * ri.quantity_g / 100.0, 2),
                    ROUND(fi.fats_g * ri.quantity_g / 100.0, 2)
                FROM recipe_ingredients ri
                JOIN food_items fi ON fi.id = ri.food_id
                JOIN custom_meals cm ON cm.id = ri.meal_id
                WHERE ri.meal_id = %s AND cm.user_id = %s
                ORDER BY fi.name ASC
                """,
                (meal_id, user_id)
            )
            rows = cursor.fetchall()
            if rows:
                columns = ["Ingredient", "Sursă", "Cantitate (g)", "Calorii", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)"]
                return pd.DataFrame(rows, columns=columns)
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching custom meal ingredients: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()
