from database import get_connection

class RecipeIngredient:
    """
    Represents an ingredient line inside a custom meal recipe.
    Links a CustomMeal to a FoodItem with a specific quantity in grams.
    """
    MIN_QUANTITY_G = 1.0
    MAX_QUANTITY_G = 5000.0

    def __init__(self, meal_id: int, food_id: int, quantity_g: float, ingredient_id: int = None):
        self.id = ingredient_id
        self.meal_id = meal_id
        self.food_id = food_id
        self.quantity_g = quantity_g

        self.validate_quantity(self.quantity_g)

    @classmethod
    def validate_quantity(cls, quantity_g: float) -> None:
        """Validates ingredient quantity consistently with the UI and database constraints."""
        if quantity_g < cls.MIN_QUANTITY_G:
            raise ValueError("Ingredient quantity must be at least 1 gram.")
        if quantity_g > cls.MAX_QUANTITY_G:
            raise ValueError("Ingredient quantity must be at most 5000 grams.")

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
