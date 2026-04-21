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
        Base authentication logic. Overridden by child classes.
        Maps to +authenticate(): boolean from the UML diagram.
        """
        return False  # Base class does not implement authentication

    def logout(self):
        """
        Handles user logout logic. 
        Maps to +logout(): void from the UML diagram.
        (Implementation hooked to Streamlit session state in app.py)
        """
        pass


class Admin(UserAccount):
    """
    Concrete class representing a system administrator.
    Inherits from UserAccount. Maps to Admin in the UML Class Diagram.
    """
    def __init__(self, email: str, access_level: int = 1, password_hash: str = None):
        super().__init__(email, password_hash)
        self.access_level = access_level

    def authenticate(self, plain_password: str) -> bool:
        """
        Overrides the base authenticate method to check the admins table.
        Populates access_level on success.
        """
        conn = get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            hashed_pw = self._hash_password(plain_password)
            cursor.execute(
                "SELECT id, access_level FROM admins WHERE email = %s AND password_hash = %s",
                (self.email, hashed_pw)
            )
            result = cursor.fetchone()
            if result:
                self.access_level = result[1]
                return True
            return False
        except Exception as e:
            print(f"Admin authentication failed: {e}")
            return False
        finally:
            if conn:
                conn.close()


class User(UserAccount):
    """
    Concrete class representing a standard application user.
    Inherits from UserAccount. Maps to User in the UML Class Diagram.
    """
    def __init__(self, email: str, full_name: str = None, height_cm: float = None, age: int = None, gender: str = None, goal: str = None, password_hash: str = None):
        super().__init__(email, password_hash)
        self.id = None  # populated on successful authenticate()
        self.full_name = full_name
        self.height_cm = height_cm
        self.age = age
        self.gender = gender
        self.goal = goal

    def authenticate(self, plain_password: str) -> bool:
        """
        Overrides the base authenticate method.
        Validates password and populates profile attributes (including ID) in a single DB query.
        """
        conn = get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            hashed_pw = self._hash_password(plain_password)
            cursor.execute(
                "SELECT id, full_name, height_cm, age, gender, goal FROM users WHERE email = %s AND password_hash = %s",
                (self.email, hashed_pw)
            )
            result = cursor.fetchone()
            if result:
                self.id = result[0]
                self.full_name = result[1]
                self.height_cm = result[2]
                self.age = result[3]
                self.gender = result[4]
                self.goal = result[5]
                return True
            return False
        except Exception as e:
            print(f"User authentication failed: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def calculateDailyCaloricNeeds(self) -> float:
        """
        Calculates TDEE (Total Daily Energy Expenditure).
        Maps to +calculateDailyCaloricNeeds(): double from the UML diagram.
        """
        return 2000.0 

    def register(self, plain_password: str) -> bool:
        """Saves the new user object to the PostgreSQL database."""
        if not self.email or not self.full_name or not plain_password:
            print("Registration blocked: Missing mandatory fields.")
            return False
            
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