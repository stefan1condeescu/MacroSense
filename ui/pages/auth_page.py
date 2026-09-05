from html import escape

import streamlit as st
from models.authentication import Admin, User
from models.text_validation import has_obvious_html_chars, is_valid_person_name
from models.tracking import WeightLog
from ui.language import translate, translated_selection_key
from ui.page_theme import apply_page_theme


AUTH_NAVIGATION_KEY = "auth_navigation"
AUTH_REDIRECT_TO_LOGIN_KEY = "auth_redirect_to_login"
AUTH_REGISTER_SUCCESS_KEY = "auth_register_success_message"
AUTH_LOGIN_PAGE_ID = "login"
AUTH_REGISTER_PAGE_ID = "register"
AUTH_PAGES = {
    AUTH_LOGIN_PAGE_ID: "Login",
    AUTH_REGISTER_PAGE_ID: "Create account",
}
LEGACY_AUTH_PAGE_IDS = {
    "Autentificare": AUTH_LOGIN_PAGE_ID,
    "Creare Cont": AUTH_REGISTER_PAGE_ID,
    "Login": AUTH_LOGIN_PAGE_ID,
    "Create account": AUTH_REGISTER_PAGE_ID,
}
AUTH_GOAL_LABELS = {
    "Slabire": "Weight loss",
    "Mentinere": "Maintenance",
    "Crestere": "Muscle gain",
}


def get_registration_error_message(error_code: str) -> str:
    """Return a translated user-facing message for a stable registration error code."""
    messages = {
        "duplicate_email": translate("An account already exists for this email address."),
        "missing_required_fields": translate("Please complete all required fields."),
        "invalid_email": translate("The email address is not valid."),
        "invalid_full_name": translate(
            "The full name may contain only letters, spaces, hyphens, or apostrophes."
        ),
        "invalid_height": translate(
            "Height must be between {minimum:.0f} and {maximum:.0f} cm.",
            minimum=User.MIN_HEIGHT_CM,
            maximum=User.MAX_HEIGHT_CM,
        ),
        "invalid_age": translate(
            "Age must be between {minimum} and {maximum} years.",
            minimum=User.MIN_AGE,
            maximum=User.MAX_AGE,
        ),
        "invalid_gender": translate("The selected gender is not valid."),
        "invalid_goal": translate("The selected goal is not valid."),
        "invalid_initial_weight": translate("The initial weight is not valid."),
        "initial_weight_out_of_range": translate(
            "Weight must be between {minimum:.0f} and {maximum:.0f} kg.",
            minimum=WeightLog.MIN_WEIGHT_KG,
            maximum=WeightLog.MAX_WEIGHT_KG,
        ),
        "invalid_profile_data": translate(
            "The profile data does not satisfy the application rules."
        ),
        "database_connection_failed": translate(
            "The database connection could not be established."
        ),
    }
    return messages.get(
        error_code,
        translate("The account could not be created. Check the entered data and try again."),
    )


def display_auth_page_name(page_id: str) -> str:
    """Return the translated label for a stable authentication page ID."""
    source_label = AUTH_PAGES.get(page_id)
    if source_label is None:
        return page_id
    return translate(source_label)


def display_auth_goal_name(goal: str) -> str:
    """Return the translated display label for a stored user goal value."""
    source_label = AUTH_GOAL_LABELS.get(goal)
    if source_label is None:
        return goal
    return translate(source_label)


def normalize_auth_page_id(page_id: str | None) -> str:
    """Convert a current or legacy authentication selection to a stable ID."""
    if page_id in AUTH_PAGES:
        return str(page_id)
    return LEGACY_AUTH_PAGE_IDS.get(str(page_id), AUTH_LOGIN_PAGE_ID)


def render_auth_page() -> None:
    st.sidebar.title("MacroSense")
    if st.session_state.pop(AUTH_REDIRECT_TO_LOGIN_KEY, False):
        st.session_state[AUTH_NAVIGATION_KEY] = AUTH_LOGIN_PAGE_ID
    current_page = st.session_state.get(AUTH_NAVIGATION_KEY)
    normalized_page = normalize_auth_page_id(current_page)
    if current_page != normalized_page:
        st.session_state[AUTH_NAVIGATION_KEY] = normalized_page
    selected_page = st.sidebar.selectbox(
        translate("Navigation"),
        options=list(AUTH_PAGES),
        format_func=display_auth_page_name,
        key=translated_selection_key(AUTH_NAVIGATION_KEY),
    )
    apply_page_theme("auth")
    
    if selected_page == AUTH_REGISTER_PAGE_ID:
        st.subheader(translate("Create a new profile"))
        with st.container(border=True, key="register_form"):
            email = st.text_input(translate("Email address"), key="auth_register_email")
            password = st.text_input(
                translate("Password"), type="password", key="auth_register_password"
            )
            full_name = st.text_input(translate("Full name"), key="auth_register_full_name")
            col1, col2 = st.columns(2)
            with col1:
                height = st.number_input(
                    translate("Height (cm)"),
                    value=170.0,
                    step=0.1,
                    key="auth_register_height",
                    help=translate(
                        "Height must be between {minimum:.0f} and {maximum:.0f} cm.",
                        minimum=User.MIN_HEIGHT_CM,
                        maximum=User.MAX_HEIGHT_CM,
                    ),
                )
                weight = st.number_input(
                    translate("Current weight (kg)"),
                    value=70.0,
                    step=0.1,
                    key="auth_register_weight",
                    help=translate(
                        "Weight must be between {minimum:.0f} and {maximum:.0f} kg.",
                        minimum=WeightLog.MIN_WEIGHT_KG,
                        maximum=WeightLog.MAX_WEIGHT_KG,
                    ),
                )
                age = st.number_input(
                    translate("Age"),
                    value=25,
                    step=1,
                    key="auth_register_age",
                    help=translate(
                        "Age must be between {minimum} and {maximum} years.",
                        minimum=User.MIN_AGE,
                        maximum=User.MAX_AGE,
                    ),
                )
            with col2:
                gender = st.selectbox(
                    translate("Gender"), ["M", "F"],
                    key="auth_register_gender",
                )
                goal = st.selectbox(
                    translate("Goal"),
                    list(User.VALID_GOALS),
                    format_func=display_auth_goal_name,
                    key=translated_selection_key("auth_register_goal"),
                )
            submit_register = st.button(
                translate("Register"),
                width="stretch",
                type="primary",
                key="auth_register_submit",
            )
    
        if submit_register:
            cleaned_email = email.strip()
            cleaned_full_name = full_name.strip()
            if not cleaned_email or not password.strip() or not cleaned_full_name:
                st.warning(
                    translate("Please complete all required fields (Email, Password, Full name)!")
                )
            elif len(password) < 6:
                st.warning(translate("The password must contain at least 6 characters!"))
            elif has_obvious_html_chars(cleaned_email):
                st.warning(translate("Please enter a valid email address!"))
            elif "@" not in cleaned_email or cleaned_email.count("@") != 1 or "." not in cleaned_email.split("@")[1]:
                st.warning(translate("Please enter a valid email address!"))
            elif not is_valid_person_name(cleaned_full_name):
                st.error(get_registration_error_message("invalid_full_name"))
            elif not User.MIN_HEIGHT_CM <= float(height) <= User.MAX_HEIGHT_CM:
                st.error(get_registration_error_message("invalid_height"))
            elif not WeightLog.MIN_WEIGHT_KG <= float(weight) <= WeightLog.MAX_WEIGHT_KG:
                st.error(get_registration_error_message("initial_weight_out_of_range"))
            elif not User.MIN_AGE <= int(age) <= User.MAX_AGE:
                st.error(get_registration_error_message("invalid_age"))
            elif goal not in User.VALID_GOALS:
                st.error(get_registration_error_message("invalid_goal"))
            else:
                new_user = User(cleaned_email, cleaned_full_name, height, age, gender, goal)
                if new_user.register(password, weight):
                    st.session_state[AUTH_REGISTER_SUCCESS_KEY] = (
                        "Account created successfully! You can now log in."
                    )
                    st.session_state[AUTH_REDIRECT_TO_LOGIN_KEY] = True
                    st.rerun()
                else:
                    st.error(get_registration_error_message(new_user.last_error_code))
       
    elif selected_page == AUTH_LOGIN_PAGE_ID:
        registration_success_message = st.session_state.pop(AUTH_REGISTER_SUCCESS_KEY, None)
        if registration_success_message:
            st.success(translate(registration_success_message))
        login_slot = st.empty()
        with login_slot.container():
            st.markdown('<div class="auth-login-panel"></div>', unsafe_allow_html=True)
            _, login_col, _ = st.columns([0.2, 1, 0.2])
            with login_col:
                welcome_title = escape(translate("Welcome back"))
                welcome_text = escape(
                    translate("Log in to MacroSense to continue tracking.")
                )
                st.markdown(
                    f"""
                    <div class="auth-login-copy">
                        <h2>{welcome_title}</h2>
                        <p>{welcome_text}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                with st.container(border=True, key="login_form"):
                    email = st.text_input(translate("Email"), key="auth_login_email")
                    password = st.text_input(
                        translate("Password"), type="password", key="auth_login_password"
                    )
                    submit_login = st.button(
                        translate("Log in"),
                        width="stretch",
                        type="primary",
                        key="auth_login_submit",
                    )

                    if submit_login:
                        cleaned_email = email.strip()
                        if not cleaned_email or not password.strip():
                            st.warning(
                                translate("Please enter your email address and password.")
                            )
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
                                    st.error(translate("Incorrect email or password."))
                auth_note = escape(
                    translate(
                        "Don't have an account? Choose Create account from the menu on the left."
                    )
                )
                st.markdown(
                    f'<p class="auth-login-note">{auth_note}</p>',
                    unsafe_allow_html=True,
                )
