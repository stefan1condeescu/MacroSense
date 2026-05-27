import streamlit as st
from models.authentication import Admin, User
from models.text_validation import has_obvious_html_chars, is_valid_person_name
from models.tracking import WeightLog
from ui.page_theme import apply_page_theme


AUTH_NAVIGATION_KEY = "auth_navigation"
AUTH_REDIRECT_TO_LOGIN_KEY = "auth_redirect_to_login"
AUTH_REGISTER_SUCCESS_KEY = "auth_register_success_message"


def get_registration_error_message(error_code: str) -> str:
    """Returns a user-facing Romanian message for a stable registration error code."""
    messages = {
        "duplicate_email": "Există deja un cont creat cu această adresă de email.",
        "missing_required_fields": "Te rog să completezi toate câmpurile obligatorii.",
        "invalid_email": "Adresa de email nu este validă.",
        "invalid_full_name": "Numele complet poate conține doar litere, spații, cratimă sau apostrof.",
        "invalid_height": (
            "Înălțimea trebuie să fie între "
            f"{User.MIN_HEIGHT_CM:.0f} și {User.MAX_HEIGHT_CM:.0f} cm."
        ),
        "invalid_age": (
            "Vârsta trebuie să fie între "
            f"{User.MIN_AGE} și {User.MAX_AGE} ani."
        ),
        "invalid_gender": "Sexul selectat nu este valid.",
        "invalid_goal": "Obiectivul selectat nu este valid.",
        "invalid_initial_weight": "Greutatea inițială nu este validă.",
        "initial_weight_out_of_range": (
            "Greutatea trebuie să fie între "
            f"{WeightLog.MIN_WEIGHT_KG:.0f} și {WeightLog.MAX_WEIGHT_KG:.0f} kg."
        ),
        "invalid_profile_data": "Datele profilului nu respectă regulile aplicației.",
        "database_connection_failed": "Nu s-a putut realiza conexiunea la baza de date.",
    }
    return messages.get(error_code, "Contul nu a putut fi creat. Verifică datele introduse și încearcă din nou.")


def render_auth_page() -> None:
    st.sidebar.title("MacroSense")
    menu = ["Autentificare", "Creare Cont"]
    if st.session_state.pop(AUTH_REDIRECT_TO_LOGIN_KEY, False):
        st.session_state[AUTH_NAVIGATION_KEY] = "Autentificare"
    if AUTH_NAVIGATION_KEY not in st.session_state:
        st.session_state[AUTH_NAVIGATION_KEY] = "Autentificare"
    choice = st.sidebar.selectbox("Navigație", menu, key=AUTH_NAVIGATION_KEY)
    apply_page_theme("auth")
    
    if choice == "Creare Cont":
        st.subheader("Creează un profil nou")
        with st.form("register_form"):
            email = st.text_input("Adresă Email")
            password = st.text_input("Parolă", type="password")
            full_name = st.text_input("Nume complet")
            col1, col2 = st.columns(2)
            with col1:
                height = st.number_input(
                    "Înălțime (cm)",
                    value=170.0,
                    step=0.1,
                    help=(
                        "Înălțimea trebuie să fie între "
                        f"{User.MIN_HEIGHT_CM:.0f} și {User.MAX_HEIGHT_CM:.0f} cm."
                    )
                )
                weight = st.number_input(
                    "Greutate curentă (kg)",
                    value=70.0,
                    step=0.1,
                    help=(
                        "Greutatea trebuie să fie între "
                        f"{WeightLog.MIN_WEIGHT_KG:.0f} și {WeightLog.MAX_WEIGHT_KG:.0f} kg."
                    )
                )
                age = st.number_input(
                    "Vârstă",
                    value=25,
                    step=1,
                    help=f"Vârsta trebuie să fie între {User.MIN_AGE} și {User.MAX_AGE} ani."
                )
            with col2:
                gender = st.selectbox("Sex", ["M", "F"])
                goal = st.selectbox("Obiectiv", list(User.VALID_GOALS))
            submit_register = st.form_submit_button("Înregistrează-te", width="stretch", type="primary")
    
        if submit_register:
            cleaned_email = email.strip()
            cleaned_full_name = full_name.strip()
            if not cleaned_email or not password.strip() or not cleaned_full_name:
                st.warning("Te rog să completezi toate câmpurile obligatorii (Email, Parolă, Nume complet)!")
            elif len(password) < 6:
                st.warning("Parola trebuie să conțină cel puțin 6 caractere!")
            elif has_obvious_html_chars(cleaned_email):
                st.warning("Te rog introdu o adresă de email validă!")
            elif "@" not in cleaned_email or cleaned_email.count("@") != 1 or "." not in cleaned_email.split("@")[1]:
                st.warning("Te rog introdu o adresă de email validă!")
            elif not is_valid_person_name(cleaned_full_name):
                st.error(get_registration_error_message("invalid_full_name"))
            elif not User.MIN_HEIGHT_CM <= float(height) <= User.MAX_HEIGHT_CM:
                st.error(get_registration_error_message("invalid_height"))
            elif not WeightLog.MIN_WEIGHT_KG <= float(weight) <= WeightLog.MAX_WEIGHT_KG:
                st.error(
                    "Greutatea trebuie să fie între "
                    f"{WeightLog.MIN_WEIGHT_KG:.0f} și {WeightLog.MAX_WEIGHT_KG:.0f} kg."
                )
            elif not User.MIN_AGE <= int(age) <= User.MAX_AGE:
                st.error(get_registration_error_message("invalid_age"))
            elif goal not in User.VALID_GOALS:
                st.error(get_registration_error_message("invalid_goal"))
            else:
                new_user = User(cleaned_email, cleaned_full_name, height, age, gender, goal)
                if new_user.register(password, weight):
                    st.session_state[AUTH_REGISTER_SUCCESS_KEY] = "Cont creat cu succes! Te poți autentifica acum."
                    st.session_state[AUTH_REDIRECT_TO_LOGIN_KEY] = True
                    st.rerun()
                else:
                    st.error(get_registration_error_message(new_user.last_error_code))
       
    elif choice == "Autentificare":
        registration_success_message = st.session_state.pop(AUTH_REGISTER_SUCCESS_KEY, None)
        if registration_success_message:
            st.success(registration_success_message)
        login_slot = st.empty()
        with login_slot.container():
            st.markdown('<div class="auth-login-panel"></div>', unsafe_allow_html=True)
            _, login_col, _ = st.columns([0.2, 1, 0.2])
            with login_col:
                st.markdown(
                    """
                    <div class="auth-login-copy">
                        <h2>Bine ai revenit</h2>
                        <p>Intră în MacroSense pentru a continua monitorizarea.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                with st.form("login_form"):
                    email = st.text_input("Email")
                    password = st.text_input("Parolă", type="password")
                    submit_login = st.form_submit_button(
                        "Intră în cont",
                        width="stretch",
                        type="primary",
                    )

                    if submit_login:
                        cleaned_email = email.strip()
                        if not cleaned_email or not password.strip():
                            st.warning("Te rog să introduci adresa de email și parola.")
                        else:
                            # Admin and user accounts are checked in separate tables.
                            admin_account = Admin(cleaned_email)
                            if admin_account.authenticate(password):
                                st.session_state['role'] = 'admin'
                                st.session_state['logged_in_email'] = admin_account.email
                                st.session_state['admin_access_level'] = admin_account.access_level
                                login_slot.empty()
                                st.rerun()
                            else:
                                user_account = User(cleaned_email)
                                if user_account.authenticate(password):
                                    st.session_state['role'] = 'user'
                                    st.session_state['logged_in_email'] = user_account.email
                                    st.session_state['user_full_name'] = user_account.full_name
                                    st.session_state['user_id'] = user_account.id
                                    login_slot.empty()
                                    st.rerun()
                                else:
                                    st.error("Email sau parolă incorecte.")
                st.markdown(
                    '<p class="auth-login-note">Nu ai cont? Alege Creare Cont din meniul din stânga.</p>',
                    unsafe_allow_html=True,
                )
