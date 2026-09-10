# MacroSense — AGENTS.md

## Technical stack

- Backend/UI: Python 3.x + Streamlit
- Database: PostgreSQL via psycopg2 (never an ORM)
- Architecture: modular monolith; UI pages call models and services within
  the same Streamlit process.
- File structure:
  - app.py — Streamlit entrypoint: configures the application and routes by role
  - assets/style.css — local CSS styles for UI polish
  - ui/config.py — Streamlit configuration and local CSS loading
  - ui/language.py — session language, EN/RO selector and `translate()`
  - ui/translations_ro.py — Romanian translations of English source text
  - ui/page_theme.py — visual theme for each page
  - ui/catalog_constants.py — local MacroSense categories used in the Admin
    UI and seed tests
  - ui/activity_selection.py — shared activity selection helpers with
    accent-insensitive search, category filtering and source/MET method display
  - ui/activity_validation.py — shared duration, sets and reps validation
    without automatic Streamlit clamping
  - ui/food_selection.py — shared food selection helpers with accent-insensitive
    search, category filtering and source display
  - ui/quantity_validation.py — shared quantity validation in grams
    without automatic Streamlit clamping
  - ui/tables.py — table rendering and shared `column_config` definitions
  - ui/formatters.py — display formatting helpers
  - ui/journal_energy_summary.py — energy cards shared by both journals
  - ui/pages/ — Streamlit pages separated by workflow:
    - auth_page.py — authentication and account creation
    - admin_routes.py — Administrator menu routing
    - admin_catalog_pages.py — Administrator catalog management
    - user_routes.py — User menu routing
    - dashboard_page.py — Home page
    - food_journal_page.py — Food Journal
    - activity_journal_page.py — Activity Journal
    - weight_journal_page.py — Weight Journal
    - custom_meals_page.py — Custom Meals
    - what_if_page.py — calorie scenarios kept only in the session
    - user_catalog_pages.py — catalogs visible to users
  - services/ — controlled external integrations and analytics:
    - usda_food_data.py — USDA FoodData Central client for food imports
    - analytics/energy.py — pure formulas for BMI, BMR, estimated TDEE and
      estimated calorie balance
    - analytics/dashboard_data.py — read-only dashboard and journal
      aggregations, without creating `daily_logs`
    - ml/ — synthetic data, feature engineering, training, evaluation and
      14/30-day weight predictions; local artifacts in `artifacts/ml/`
    - recommendations/simple_recommendations.py — explainable rules for
      food intake, protein, activity and progress, displayed in the dashboard
    - what_if/ — read-only loaders and pure scenario calculations
  - models/profile_constants.py — canonical values for persisted profile
    fields, including `USER_GOALS`
  - models/text_validation.py — shared validation helpers for persisted text
  - models/tracking.py — compatibility facade that re-exports tracking package classes
  - models/tracking_models/ — Tracking domain package, separated by class:
    - food_item.py — FoodItem
    - activity.py — Activity
    - food_log.py — FoodLog
    - activity_log.py — ActivityLog
    - recipe_ingredient.py — RecipeIngredient
    - custom_meal.py — CustomMeal
    - daily_log.py — DailyLog
    - weight_log.py — WeightLog
  - models/authentication.py — User, Admin
  - database.py — get_connection()
  - schema.sql — complete database schema
  - database/seeds/ — optional SQL scripts for catalog population
  - tests/ — `unittest` tests for models, services, UI, translations and SQL schema
  - STATUS.md — current project status (completed work, work in progress, backlog)
  - README.md — installation, usage and current architecture diagram
- Historical thesis references: `docs/DiagramaClase_UPDATED.png`,
  `docs/ERD_UPDATED.png`, `docs/LICENTA_faranumev12.docx` and
  `docs/STRUCTURA LUCRĂRII DE LICENŢĂ.docx`. The `docs/` directory is not
  available in this checkout; consistency with these files has not been verified.

## Strict rules

- All code (variables, classes, methods, comments) must be in ENGLISH.
- Streamlit UI source text is in ENGLISH and displayed through
  `ui.language.translate()`. Romanian translations are stored in
  `ui/translations_ro.py`; the UI supports EN and RO.
- Required DB pattern: try/except/finally with conn.close() in finally.
- Do not use st.form() in the Food Journal or Activity Journal.
- Use st.button() with an explicit key for submission.
- Never provide partial code or pseudocode — only complete, working code.
- Keep automated tests in `tests/` and extend them for every significant
  feature; do not delete them after validation.
- Test command on macOS/Linux: `./.venv/bin/python -m unittest discover -s tests -v`.
- Commands provided for manual execution use Bash syntax. For the existing
  Windows environment: `./venv/Scripts/python.exe -m unittest discover -s tests -v`.
- The developer makes commits MANUALLY after each approved change; the AI
  must never commit or push automatically.
  Exception: the AI may commit only when the developer explicitly requests it.

## Golden rule

Check architectural documentation against the code and `schema.sql` before
making architectural changes. Flag discrepancies before writing code.
When the thesis files in `docs/` are available, also check UML/ERD;
if they are missing, state this limitation without claiming the documentation is synchronized.

## OOP architecture

- DailyLog: get_or_create, get_for_date, recalculate_totals, get_food_entries,
  get_activity_entries, calculate_hybrid_calories (static),
  get_latest_weight (static), get_by_id, delete_if_empty,
  calculate_energy_balance
  (`get_food_entries()` and `get_activity_entries()` must be called with
  `user_id` from the UI to preserve user isolation even if a `log_id`
  accidentally reaches the wrong context; `log_date` cannot be later than today)
- FoodLog: save(), update(), delete()
  (`meal_type` must be one of the canonical DB values: `Mic dejun`,
  `Prânz`, `Cină`, `Gustare`; `meal_time` must be a valid `datetime.time`,
  not `None`; `quantity_g` must remain within 1-5000g;
  for `custom_meal_id`, `save()` stores a nutritional snapshot per 100g
  in `food_logs`, and `update()` preserves the existing snapshot)
- ActivityLog: save(), update(), delete()
  (`sets` and `reps` must also be validated together in the constructor,
  not only during update/in the UI; either both are null or they satisfy
  the ranges of 1-50 sets and 1-200 reps;
  `duration_min` must remain within 0.1-600 minutes;
  `manual_calories_burned` is optional and, when provided, replaces the
  MET/TUT formula for that entry)
- RecipeIngredient: save() method
  (`quantity_g` must remain within 1-5000g, matching the UI and DB)
- CustomMeal: save, add_ingredient, create_with_ingredients,
  update_with_ingredients, set_status, archive, restore,
  calculate_total_macros, calculateTotalMacros,
  get_user_meal_options(include_archived=False), get_affected_daily_log_ids,
  get_all_as_dataframe, get_ingredients, get_ingredients_as_dataframe
  (`update_with_ingredients()` changes only the current recipe; it does not
  backfill historical snapshots or recalculate previously saved journals)
- WeightLog: save(), update(), delete(), get_user_entries(),
  get_reference_for_user(), get_latest_for_user(),
  get_activity_day_weight_references(), get_changed_reference_ids(),
  recalculate_user_daily_logs()
  (`recalculate_user_daily_logs()` recalculates only days with workouts
  calculated through MET/TUT, ignoring entries with `manual_calories_burned`;
  when given a previous snapshot, it recalculates only days whose weight
  reference actually changed; `log_date` cannot be later than today)
- User: register(password, weight), authenticate(password)
  (`goal` must be one of the canonical values without diacritics:
  `Slabire`, `Mentinere`, `Crestere`, defined in `models.profile_constants`)
- Admin: authenticate(password)
- FoodItem, Activity: save(), get_all_as_dataframe(), get_catalog_options()
- FoodItem: external_reference_exists()
- FoodItem.get_catalog_options() must also include `source_label` so that
  selections in the Food Journal and Custom Meals distinguish MacroSense
  foods from USDA foods.
- Activity validates a nonempty name, a nonempty category and the minimum
  MET coefficient `Activity.MIN_MET_MULTIPLIER` at model level; the Admin
  UI must display errors for these cases before saving.
- Activity accepts optional catalog source metadata:
  `source`, `source_type`, `external_id`, `source_url`, `met_source_code`,
  `met_source_description`, `met_estimation_method`. Allowed methods are
  `official_compendium`, `compendium_mapping` and `manual_admin`; official
  Compendium activities and MacroSense mappings must be clearly distinguished
  in the UI and seeds.
- FoodItem validates a nonempty name, a nonempty category, nonnegative
  nutritional values, strictly positive calories and at least one positive
  macronutrient at model level; the name cannot contain obvious HTML characters
  (`<` or `>`) and must contain at least one letter.
- Activity and User block obvious HTML characters (`<` or `>`) in persisted
  text fields (`name`, `full_name`, `email`); activity names must contain at
  least one letter, and `full_name` accepts only letters, spaces, hyphens
  and apostrophes.
- FoodItem accepts optional source metadata for imported foods:
  `source`, `source_type`, `external_id`, `source_url`;
  USDA import must remain available only to the Administrator.
- User and administrator emails are trimmed with `strip()` but are not
  automatically lowercased; authentication is case-sensitive.

## UI conventions

- The language is stored in `st.session_state["language"]` (`en`/`ro`),
  including after logout. The default is `en`; `MACROSENSE_DEFAULT_LANGUAGE=ro`
  can change the initial language. The selector uses local SVG flags.
- Auth/User/Admin navigation uses stable IDs, and `format_func` translates
  only the label. Selections with translated labels are registered through
  `translated_selection_key()` for resynchronization when the language changes;
  older sessions with labels instead of IDs are normalized before rendering.
- Switching language preserves selections and unsaved values on the current
  page. Auth and manual Admin forms use reactive containers; validation and
  saving run only after the explicit button is pressed.
- Translation changes the display, not persisted values: goals, meal types,
  categories and statuses retain their canonical values.
  Catalog names and user-entered text are not translated automatically.
- The Food Journal and Activity Journal use `ui.journal_energy_summary`
  for four cards: calories consumed, activity calories, estimated TDEE
  and estimated balance. Days without food entries show missing data.
- Main User navigation is displayed as a sidebar radio list so that
  `Home` and the other pages remain visible at all times.
- Use hide_index=True on every st.dataframe().
- Daily lists in the Food Journal, Activity Journal and Weight Journal are
  displayed as compact rows/cards defined through local CSS, with all
  user-entered values escaped before use in custom HTML.
- Show a live calorie preview with st.caption() before the save button.
- In the Activity Journal, users can optionally enter calories reported by
  a wearable/cardio machine; the value is stored in
  `activity_logs.manual_calories_burned` and replaces the MET/TUT estimate
  only for that entry.
- The `Home` dashboard is read-only and consumes `services.analytics`,
  `services.ml` and `services.recommendations`; it does not use
  `DailyLog.get_or_create()` or create/modify data. In the dashboard,
  `daily_logs.total_calories_burned` is interpreted as the total calories
  burned through logged activities, and estimated TDEE is derived as
  `BMR * 1.2 + activity_calories_burned`.
- The dashboard treats days without food entries as missing-data days, not
  days with 0 kcal consumed; estimated calorie balance is calculated only
  for days with logged food.
- The dashboard retains metadata for the daily reference weight:
  source date, whether the value is imputed, whether it uses a future
  fallback and the distance in days. Future fallback is allowed only for
  read-only dashboard display; ML datasets must use only past references
  to avoid data leakage.
- The dashboard reports food, activity, weight and overall consistency
  separately; these values form the basis for feature engineering and must
  not be implicitly recombined in ML without justification.
- Weight predictions use local artifacts for 14/30 days and flag insufficient
  data or the use of a historical date. Dashboard recommendations are
  explainable rules without meal-plan or workout-program generation.
- The What-if simulator loads the real day read-only and keeps the scenario
  in the session. The 14/30-day impact calculation is deterministic; it does
  not save to the DB or represent a new ML prediction.
- In the Activity Journal, catalog activity selection does not use a selectbox
  for large lists; it uses search, a category filter and a selectable table,
  keeping the activity ID internal.
- Duration, sets and reps in the Activity Journal are validated manually
  through `ui.activity_validation`; do not use `min_value`/`max_value`
  on these `st.number_input` widgets, so Streamlit does not save the old
  value after a native warning.
- Reactive forms: st.button() with an explicit key=.
- In the Food Journal and Activity Journal, reactive panels with many
  widgets may use st.fragment() to limit visual rerendering and avoid flicker.
- Viewing a date in the Food Journal or Activity Journal must not create
  empty `daily_logs` rows; `DailyLog.get_or_create()` is used only when
  saving the first real entry.
- The Food Journal, Activity Journal and Weight Journal accept saves only
  for today or past dates; future dates are blocked in the UI, model and DB.
- Success messages following operations with a rerun must be kept in
  st.session_state and displayed as st.toast(), without moving the table.
- Food and custom-meal selectboxes use internal IDs but show users only
  the name, without technical suffixes such as #id.
- In the Food Journal, selecting a catalog food no longer uses a selectbox
  for large lists; it uses search, a category filter and a selectable table,
  keeping the food ID internal.
- In Custom Meals, ingredient selection uses the same logic as the Food
  Journal: accent-insensitive search, category filtering, a selectable
  table and a source column.
- Local food/ingredient searches must be accent-insensitive:
  `capsuni` must find `Căpșuni`.
- A custom meal name must start with a letter;
  names starting with a digit or special character are not accepted.
- Initial weight in the account creation form is validated manually
  against `WeightLog.MIN_WEIGHT_KG` - `WeightLog.MAX_WEIGHT_KG`;
  do not use automatic clamping through `min_value/max_value`.
- Quantities in grams in the Food Journal and Custom Meals are validated
  manually through `ui.quantity_validation`; do not use `min_value`/`max_value`
  on `st.number_input`, so Streamlit does not save the old value after a
  native warning.
- Height and age in the account creation form are validated manually
  against `User.MIN_HEIGHT_CM` - `User.MAX_HEIGHT_CM` and
  `User.MIN_AGE` - `User.MAX_AGE`; do not use automatic clamping through
  `min_value/max_value`.
- Custom CSS belongs in `assets/style.css`, not inline in `app.py`;
  use only stable Streamlit selectors or standard HTML tags, never generated
  classes such as `st-emotion-cache-*`.
- Any user-entered text displayed through custom HTML with
  `unsafe_allow_html=True` must be escaped before interpolation.
- User-entered names must not accept obvious HTML characters (`<` or `>`)
  if they are used as titles/cards in the UI.

## Database

- Local PostgreSQL via pgAdmin 4 (localhost:5432).
- Do not execute psql commands directly — generate .sql files for manual execution.
- schema.sql is the source of truth for the DB structure.
- The English demo uses the isolated `macrosense_demo_en` database, selected
  locally through `DB_NAME` in the ignored secrets file. The code's fallback
  remains `macrosense_db`; see `STATUS.md` for validation results and limits.
- Run schema and seed scripts manually in the explicitly selected new demo
  database, not against the existing database. Preserve the existing demo
  until it has been backed up, extra imports have been inventoried, and the
  new demo has passed live numerical parity and UI checks. Any later cleanup
  requires explicit approval of the exact target to remove.
- The seed files now use English descriptive names for foods, activities,
  demo people and recipes, with demo accounts under `example.com`. Names
  are descriptive only; preserve canonical categories, goals, meal types
  and statuses, along with IDs, numerical values and historical snapshots.
- The public Demo Admin is intended for the disposable synthetic demo database
  and retains all existing Administrator functions. Document public demo
  login credentials in `README.md`; technical `DB_PASSWORD` and
  `FDC_API_KEY` credentials remain private.
- `database/seeds/seed_food_items_usda_starter.sql` is an optional seed for
  an expanded food catalog with real USDA foods, run manually after
  `schema.sql` in pgAdmin.
- `database/seeds/seed_activities_compendium_official.sql` is an optional
  seed for official MET activities from the 2024 Adult Compendium of Physical
  Activities.
- `database/seeds/seed_activities_macrosense_mappings.sql` is an optional
  seed for practical MacroSense exercises explicitly mapped to generic
  Compendium codes; these exercises must not be presented as individually
  specified official Compendium rows.
- Activity seeds run manually after `schema.sql`: first
  `seed_activities_compendium_official.sql`, then
  `seed_activities_macrosense_mappings.sql`.
- `database/seeds/seed_demo_users.sql` is an optional seed for synthetic
  demo users with weight history, food logs, activity logs and custom meals.
  It runs last, after the food and activity seeds.
  Demo goals must use strictly the canonical values
  `Slabire`, `Mentinere`, `Crestere`.
- USDA import uses `FDC_API_KEY` from `.streamlit/secrets.toml` or
  environment variables; the key must never be committed to Git.
- Initially, only USDA sources `SR Legacy`, `Foundation` and
  `Survey (FNDDS)` are allowed for food imports; `Branded` remains
  excluded to avoid commercial duplicates.
- Foods added manually through Admin are displayed in the UI with the
  `MacroSense` source; they may have `source = NULL` in the DB.
- Manual food creation through Admin must block empty names, names with
  obvious HTML characters (`<`, `>`) and cases where all macronutrients
  are 0 or calories are 0.
- Nutritional fields in the Admin food form are validated manually; do not
  use `min_value`/automatic clamping that could convert invalid negative
  values to 0 before validation. For readability, the form displays only
  the first validation error at a time.
- Food categories are local MacroSense categories, not raw USDA categories;
  during USDA import, the application may suggest a category automatically,
  and the Administrator can adjust it before saving.
- Local food and activity categories are defined in `ui.catalog_constants`;
  tests must verify that seeds do not introduce categories absent from the UI.
- Admin USDA search must be explained as requiring English and must filter
  irrelevant results by matching the search terms against the USDA description,
  avoiding results such as `cream of potato` when searching for `ice cream`.

## Special DB constraints

- FoodLog uses an XOR constraint: it has either food_id or custom_meal_id
  (not both at the same time).
- Custom meals are not physically deleted through the UI; they are archived
  through `status = 'Arhivată'` to preserve Food Journal history.
- Custom meals saved in the Food Journal retain a nutritional snapshot per
  entry in `food_logs`, so editing a recipe affects only future uses,
  not previously logged history.
- For entries with `custom_meal_id`, the nutritional snapshot is mandatory
  at DB level; the application does not maintain compatibility flows for
  incomplete entries without a snapshot.
- `schema.sql` must preserve explicit range and basic integrity constraints:
  normalized email, nonnegative nutritional values, positive calories and
  at least one positive macronutrient for foods, a nonempty food category,
  catalog names containing at least one letter, blocking obvious HTML
  characters in persisted text fields, full names without arbitrary special
  characters, user goals in `Slabire`/`Mentinere`/`Crestere`, weight 30-300 kg,
  minimum MET 0.9, positive workout duration within 0.1-600 minutes, valid
  `sets`/`reps` pairs with 1-50 sets and 1-200 reps, manual workout calories
  of 1-5000 kcal when provided, food/ingredient quantities of 1-5000g, required
  meal type/time for food entries, and triggers blocking future
  `daily_logs.log_date` and `weight_logs.log_date`.

## Not implemented yet

- Personalized meal recommendations
- Personalized workout recommendations
