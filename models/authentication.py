import hashlib
from database import get_connection

class UserAccount:
    """
    Base abstract class representing a generic system account.
    Corresponds to UserAccount in the UML Class Diagram.
    """
    def __init__(self, email: str, password_hash: str = None, registration_date=None):
        self.email = email
        self.password_hash = password_hash
        self.registration_date = registration_date

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hashes the password using SHA-256 for secure storage."""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, plain_password: str) -> bool:
        """
        Authenticates the user against the database.
        Maps to +authenticate(): boolean from the UML diagram.
        """
        conn = get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            hashed_pw = self._hash_password(plain_password)
            cursor.execute(
                "SELECT id FROM users WHERE email = %s AND password_hash = %s",
                (self.email, hashed_pw)
            )
            result = cursor.fetchone()
            return result is not None
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def logout(self):
        """
        Handles user logout logic. 
        Maps to +logout(): void from the UML diagram.
        (Implementation will be hooked to Streamlit session state)
        """
        pass


class User(UserAccount):
    """
    Concrete class representing a standard application user.
    Inherits from UserAccount. Maps to User in the UML Class Diagram.
    """
    def __init__(self, email: str, full_name: str, height_cm: float, age: int, gender: str, goal: str, password_hash: str = None):
        super().__init__(email, password_hash)
        self.full_name = full_name
        self.height_cm = height_cm
        self.age = age
        self.gender = gender
        self.goal = goal

    def calculateDailyCaloricNeeds(self) -> float:
        """
        Calculates TDEE (Total Daily Energy Expenditure).
        Maps to +calculateDailyCaloricNeeds(): double from the UML diagram.
        """
        # TODO: We will implement the actual BMR mathematical formula later
        return 2000.0 

    def register(self, plain_password: str) -> bool:
        """Saves the new user object to the PostgreSQL database."""
        conn = get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            hashed_pw = self._hash_password(plain_password)
            cursor.execute(
                """INSERT INTO users (email, password_hash, full_name, height_cm, age, gender, goal) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (self.email, hashed_pw, self.full_name, self.height_cm, self.age, self.gender, self.goal)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Registration failed: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @classmethod
    def get_user_by_email(cls, email: str):
        """Class method to fetch user data and instantiate a User object."""
        conn = get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT email, full_name, height_cm, age, gender, goal FROM users WHERE email = %s",
                (email,)
            )
            row = cursor.fetchone()
            if row:
                return cls(email=row[0], full_name=row[1], height_cm=row[2], age=row[3], gender=row[4], goal=row[5])
            return None
        finally:
            if conn:
                conn.close()