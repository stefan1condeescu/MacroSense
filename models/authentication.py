import hashlib
from database import get_connection
from models.profile_constants import USER_GOALS
from models.text_validation import has_obvious_html_chars, is_valid_person_name
from models.tracking_models.weight_log import WeightLog

class UserAccount:
    """Common account data shared by users and administrators."""
    def __init__(self, email: str, password_hash: str = None, registration_date=None):
        self.email = email.strip() if email else email
        self.password_hash = password_hash
        self.registration_date = registration_date

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a plain-text password for database comparison."""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, plain_password: str) -> bool:
        """Return whether the provided password is valid for this account."""
        return False

    def logout(self):
        """Placeholder for account-level logout behavior."""
        pass


class Admin(UserAccount):
    """Administrator account backed by the admins table."""
    def __init__(self, email: str, access_level: int = 1, password_hash: str = None):
        super().__init__(email, password_hash)
        self.access_level = access_level

    def authenticate(self, plain_password: str) -> bool:
        """Authenticate an administrator and load the access level."""
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
    """Standard application user backed by the users table."""
    MIN_HEIGHT_CM = 100.0
    MAX_HEIGHT_CM = 250.0
    MIN_AGE = 10
    MAX_AGE = 120
    VALID_GENDERS = ("M", "F")
    VALID_GOALS = USER_GOALS

    def __init__(self, email: str, full_name: str = None, height_cm: float = None, age: int = None, gender: str = None, goal: str = None, password_hash: str = None):
        super().__init__(email, password_hash)
        self.id = None
        self.full_name = full_name.strip() if full_name else full_name
        self.height_cm = height_cm
        self.age = age
        self.gender = gender
        self.goal = goal.strip() if goal else goal
        self.last_error_code = None

    def authenticate(self, plain_password: str) -> bool:
        """Authenticate a user and load the profile fields used by the UI."""
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

    def register(self, plain_password: str, initial_weight_kg: float) -> bool:
        """
        Saves the new user and their initial weight to the PostgreSQL database.
        Inserts into both 'users' and 'weight_logs' in a single atomic transaction.
        """
        self.last_error_code = None

        if not self.email or not self.full_name or not plain_password:
            print("Registration blocked: Missing mandatory fields.")
            self.last_error_code = "missing_required_fields"
            return False

        if has_obvious_html_chars(self.email):
            print("Registration blocked: Invalid email.")
            self.last_error_code = "invalid_email"
            return False

        if not is_valid_person_name(self.full_name):
            print("Registration blocked: Invalid full name.")
            self.last_error_code = "invalid_full_name"
            return False

        try:
            initial_weight_value = float(initial_weight_kg)
        except (TypeError, ValueError):
            print("Registration blocked: Invalid initial weight.")
            self.last_error_code = "invalid_initial_weight"
            return False

        if not WeightLog.MIN_WEIGHT_KG <= initial_weight_value <= WeightLog.MAX_WEIGHT_KG:
            print("Registration blocked: Initial weight outside supported range.")
            self.last_error_code = "initial_weight_out_of_range"
            return False

        try:
            height_value = float(self.height_cm)
        except (TypeError, ValueError):
            print("Registration blocked: Invalid height.")
            self.last_error_code = "invalid_height"
            return False

        if not self.MIN_HEIGHT_CM <= height_value <= self.MAX_HEIGHT_CM:
            print("Registration blocked: Height outside supported range.")
            self.last_error_code = "invalid_height"
            return False

        try:
            age_numeric = float(self.age)
        except (TypeError, ValueError):
            print("Registration blocked: Invalid age.")
            self.last_error_code = "invalid_age"
            return False

        if not age_numeric.is_integer() or not self.MIN_AGE <= int(age_numeric) <= self.MAX_AGE:
            print("Registration blocked: Age outside supported range.")
            self.last_error_code = "invalid_age"
            return False

        if self.gender not in self.VALID_GENDERS:
            print("Registration blocked: Invalid gender.")
            self.last_error_code = "invalid_gender"
            return False

        if self.goal not in self.VALID_GOALS:
            print("Registration blocked: Invalid goal.")
            self.last_error_code = "invalid_goal"
            return False

        self.height_cm = height_value
        self.age = int(age_numeric)

        conn = get_connection()
        if not conn:
            self.last_error_code = "database_connection_failed"
            return False

        try:
            cursor = conn.cursor()
            hashed_pw = self._hash_password(plain_password)

            cursor.execute(
                """INSERT INTO users (email, password_hash, full_name, height_cm, age, gender, goal)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (self.email, hashed_pw, self.full_name, self.height_cm,
                 self.age, self.gender, self.goal)
            )
            new_user_id = cursor.fetchone()[0]

            cursor.execute(
                """INSERT INTO weight_logs (user_id, log_date, weight_kg)
                   VALUES (%s, CURRENT_DATE, %s)""",
                (new_user_id, initial_weight_value)
            )

            conn.commit()
            return True
        except Exception as e:
            print(f"Registration failed: {e}")
            self.last_error_code = self._map_registration_error(e)
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def _map_registration_error(error) -> str:
        """Maps database exceptions to stable UI-safe error codes."""
        pgcode = getattr(error, "pgcode", None)
        constraint_name = getattr(getattr(error, "diag", None), "constraint_name", None)

        if pgcode == "23505":
            return "duplicate_email"

        if pgcode == "23514":
            if constraint_name == "chk_user_email_trimmed":
                return "invalid_email"
            if constraint_name == "chk_user_email_no_html":
                return "invalid_email"
            if constraint_name == "chk_user_full_name_no_html":
                return "invalid_full_name"
            if constraint_name == "chk_user_full_name_chars":
                return "invalid_full_name"
            if constraint_name == "chk_user_full_name_has_letter":
                return "invalid_full_name"
            if constraint_name == "chk_user_height":
                return "invalid_height"
            if constraint_name == "chk_user_age":
                return "invalid_age"
            if constraint_name == "chk_user_gender":
                return "invalid_gender"
            if constraint_name == "chk_user_goal":
                return "invalid_goal"
            if constraint_name == "chk_weight_range":
                return "initial_weight_out_of_range"
            return "invalid_profile_data"

        return "registration_failed"
