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
        except Exception as e:
            print(f"Error fetching food items: {e}")
            return pd.DataFrame()
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_catalog_options(cls) -> dict:
        """Fetches food items as option metadata for reactive UI selectors."""
        conn = get_connection()
        if not conn:
            return {}

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, calories_100g, protein_g, carbs_g, fats_g
                FROM food_items
                ORDER BY name ASC
                """
            )
            options = {}
            for row in cursor.fetchall():
                options[row[0]] = {
                    "id": row[0],
                    "name": row[1],
                    "calories_100g": float(row[2] or 0),
                    "protein_g": float(row[3] or 0),
                    "carbs_g": float(row[4] or 0),
                    "fats_g": float(row[5] or 0),
                }
            return options
        except Exception as e:
            print(f"Error fetching food catalog options: {e}")
            return {}
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
        except Exception as e:
            print(f"Error fetching activities: {e}")
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


class RecipeIngredient:
    """
    Represents an ingredient line inside a custom meal recipe.
    Links a CustomMeal to a FoodItem with a specific quantity in grams.
    """
    def __init__(self, meal_id: int, food_id: int, quantity_g: float, ingredient_id: int = None):
        self.id = ingredient_id
        self.meal_id = meal_id
        self.food_id = food_id
        self.quantity_g = quantity_g

        if self.quantity_g <= 0:
            raise ValueError("Ingredient quantity must be strictly positive.")

    def save(self) -> bool:
        """Saves the recipe ingredient to the PostgreSQL database."""
        conn = get_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO recipe_ingredients (meal_id, food_id, quantity_g)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (self.meal_id, self.food_id, self.quantity_g)
            )
            self.id = cursor.fetchone()[0]
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving recipe ingredient: {e}")
            return False
        finally:
            if conn:
                conn.close()


class CustomMeal:
    """
    Represents a reusable user-defined meal composed of catalog food items.
    """
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
        """Checks that a custom meal name starts with a letter."""
        cleaned_name = recipe_name.strip() if recipe_name else ""
        return bool(cleaned_name) and cleaned_name[0].isalpha()

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
                if quantity_g <= 0:
                    raise ValueError("Ingredient quantity must be strictly positive.")
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
    def get_user_meal_options(cls, user_id: int) -> dict:
        """Fetches custom meals for a user as option metadata for selectors."""
        conn = get_connection()
        if not conn:
            return {}

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
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
                ORDER BY cm.recipe_name ASC
                """,
                (user_id,)
            )
            options = {}
            for row in cursor.fetchall():
                total_quantity_g = float(row[3] or 0)
                total_calories = float(row[4] or 0)
                calories_per_g = total_calories / total_quantity_g if total_quantity_g > 0 else 0.0
                options[row[0]] = {
                    "id": row[0],
                    "recipe_name": row[1],
                    "status": row[2],
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
    def get_all_as_dataframe(cls, user_id: int) -> pd.DataFrame:
        """Fetches all custom meals for a user as a pandas DataFrame."""
        meal_options = cls.get_user_meal_options(user_id)
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
                columns = ["Ingredient", "Cantitate (g)", "Calorii", "Proteine (g)", "Carbohidrați (g)", "Grăsimi (g)"]
                return pd.DataFrame(rows, columns=columns)
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching custom meal ingredients: {e}")
            return pd.DataFrame()
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

    @staticmethod
    def calculate_hybrid_calories(category: str, met: float, weight: float, duration_min: int, sets: int, reps: int) -> float:
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
                WITH meal_totals AS (
                    SELECT
                        ri.meal_id,
                        COALESCE(SUM(ri.quantity_g), 0) AS total_quantity_g,
                        COALESCE(SUM(fi.calories_100g * ri.quantity_g / 100.0), 0) AS total_calories
                    FROM recipe_ingredients ri
                    JOIN food_items fi ON fi.id = ri.food_id
                    GROUP BY ri.meal_id
                )
                SELECT COALESCE(SUM(
                    CASE
                        WHEN mt.total_quantity_g > 0 THEN mt.total_calories * fl.quantity_g / mt.total_quantity_g
                        ELSE 0
                    END
                ), 0)
                FROM food_logs fl
                JOIN meal_totals mt ON mt.meal_id = fl.custom_meal_id
                WHERE fl.log_id = %s AND fl.custom_meal_id IS NOT NULL
                """,
                (self.id,)
            )
            calories_from_meals = float(cursor.fetchone()[0])
            self.total_calories_in = round(calories_from_food + calories_from_meals, 2)
            
            cursor.execute(
                """
                SELECT weight_kg FROM weight_logs 
                WHERE user_id = %s AND log_date <= %s 
                ORDER BY log_date DESC LIMIT 1
                """,
                (self.user_id, self.log_date)
            )
            weight_row = cursor.fetchone()
            current_weight = float(weight_row[0]) if weight_row else 70.0

            cursor.execute(
                """
                SELECT COALESCE(SUM(
                    CASE 
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

    @classmethod
    def get_food_entries(cls, log_id: int) -> "pd.DataFrame":
        """
        Returns all FoodLog entries for a given daily_log id as a DataFrame,
        including both catalog food items and custom meals.
        """
        conn = get_connection()
        if not conn:
            return pd.DataFrame()
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                WITH meal_totals AS (
                    SELECT
                        ri.meal_id,
                        COALESCE(SUM(ri.quantity_g), 0) AS total_quantity_g,
                        COALESCE(SUM(fi.calories_100g * ri.quantity_g / 100.0), 0) AS total_calories
                    FROM recipe_ingredients ri
                    JOIN food_items fi ON fi.id = ri.food_id
                    GROUP BY ri.meal_id
                )
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
                    JOIN food_items fi ON fi.id = fl.food_id
                    WHERE fl.log_id = %s AND fl.food_id IS NOT NULL

                    UNION ALL

                    SELECT
                        fl.id,
                        'Masă personalizată' AS "Tip",
                        cm.recipe_name AS "Aliment / Masă",
                        fl.quantity_g AS "Cantitate (g)",
                        ROUND(
                            CASE
                                WHEN mt.total_quantity_g > 0 THEN mt.total_calories * fl.quantity_g / mt.total_quantity_g
                                ELSE 0
                            END
                        , 2) AS "Calorii",
                        fl.meal_type AS "Masă",
                        fl.meal_time AS "Ora"
                    FROM food_logs fl
                    JOIN custom_meals cm ON cm.id = fl.custom_meal_id
                    LEFT JOIN meal_totals mt ON mt.meal_id = cm.id
                    WHERE fl.log_id = %s AND fl.custom_meal_id IS NOT NULL
                ) entries
                ORDER BY "Ora" ASC NULLS LAST
                """,
                (log_id, log_id)
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
        Helper method to fetch the user's weight on or before a specific date.
        Useful for real-time MET calorie estimations in the UI.
        """
        conn = get_connection()
        if not conn:
            return 70.0 # Fallback weight
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT weight_kg FROM weight_logs 
                WHERE user_id = %s AND log_date <= %s 
                ORDER BY log_date DESC LIMIT 1
                """,
                (user_id, target_date)
            )
            row = cursor.fetchone()
            return float(row[0]) if row else 70.0
        except Exception as e:
            print(f"Error fetching latest weight: {e}")
            return 70.0
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_activity_entries(cls, log_id: int) -> "pd.DataFrame":
        """
        Returns all ActivityLog entries for a given daily_log id as a DataFrame,
        joined with activities to show names, categories, and calculated burned calories.
        """
        conn = get_connection()
        if not conn:
            return pd.DataFrame()
        
        try:
            cursor = conn.cursor()
            # We use a CTE to get the user's latest weight relative to the log_date
            # to dynamically calculate the burned calories per activity row.
            cursor.execute(
                """
                WITH user_info AS (
                    SELECT user_id, log_date FROM daily_logs WHERE id = %s
                ),
                latest_weight AS (
                    SELECT COALESCE(
                        (SELECT weight_kg FROM weight_logs 
                         WHERE user_id = (SELECT user_id FROM user_info) 
                         AND log_date <= (SELECT log_date FROM user_info) 
                         ORDER BY log_date DESC LIMIT 1), 
                        70.0) AS weight
                )
                SELECT 
                    al.id, 
                    a.name AS "Activitate",
                    a.category AS "Categorie",
                    al.duration_min AS "Durată (min)",
                    al.sets AS "Seturi",
                    al.reps AS "Repetări",
                    ROUND(
                        CASE 
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
                ORDER BY al.id ASC
                """,
                (log_id, log_id)
            )
            rows = cursor.fetchall()
            if rows:
                columns = ["id", "Activitate", "Categorie", "Durată (min)", "Seturi", "Repetări", "Calorii Arse"]
                df = pd.DataFrame(rows, columns=columns)
                # Clean up None/NaN values for Sets and Reps to display cleanly in UI
                df['Seturi'] = df['Seturi'].fillna('-').astype(str)
                df['Repetări'] = df['Repetări'].fillna('-').astype(str)
                return df.set_index("id")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching activity entries: {e}")
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
