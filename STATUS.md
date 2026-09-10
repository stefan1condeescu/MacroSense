# MacroSense Project Status

The history below preserves project milestones, including solutions replaced
later. For current behavior and architecture, see [README.md](README.md).
Thesis and diagram entries are historical: the `docs/` directory is unavailable
in this checkout, so UML/ERD alignment has not been reverified.

## Current checkpoint

The developer manually committed `8d18f2e`, "Prepare English demo data and verify
ML compatibility", on `feature/english-demo-data`. PR 1 is merged into `main`;
`main` and `origin/main` were at `530b789` at this checkpoint.

- [x] English seed content prepared: 182 food names, 109 activity names (67 official Compendium entries and 42 MacroSense mappings), five demo identities and four recipes. Numerical values, MET coefficients and canonical Romanian domain values are unchanged.
- [x] All 460 unit tests passed on 10 September 2026 (latest run: 6.191 seconds). The three new regression tests failed against the old code and pass after the numerical/nullable-input fixes below; the focused ML/What-if suite passed all 30 tests.
- [x] The name-only regression compares calculated calories, exact complete feature rows and predictions at 14 and 30 days using the same temporary model artifacts. It does not verify live database parity or the actual runtime model artifacts.
- [x] Created and seeded the separate `macrosense_demo_en` database with explicit developer authorization. It contains five users, one Admin, 182 foods, 109 activities, four recipes, 486 daily logs, 88 weights, 3,564 food entries and 234 activity entries. The ignored local secrets file now selects it through `DB_NAME`; no credentials were added to Git.
- [x] Compared both live databases after the fixes below: all 633 comparison checks passed (previously 632/633). Dashboard analytics, recommendations, complete ML features, actual 14/30-day local-model predictions and What-if outputs match across the checked cases for all five demo users. The run covered 20 analysis snapshots and 100 What-if snapshots with 730 non-vacuity checks. Predictions also match the pre-fix baseline. All four model/metadata hashes remain unchanged; no retraining or database writes were performed.
- [x] Exercised all eight User pages and both Admin catalogs in the browser: User/Admin login, food/activity/weight save-edit-delete, recipe rename/archive/restore, What-if edit/reset, catalog search and EN→RO→EN selection/draft retention. Removed temporary test entries and restored the recipe. Registration, live USDA import, mobile layout and exhaustive browser/theme combinations were not tested in this run.
- [x] Inventoried the two old-only foods: FNDDS 2705638 (vanilla ice cream) and 2706434 (barbecue chicken). Neither is referenced by food logs or recipes; both remain in the old database pending the developer's retention decision.
- [x] Final cleanup verification restored all ten English-demo table counts and confirmed recipe ingredients, historical logs and snapshots still match numerically. Every old-database table's count and full-row fingerprint matches its pre-test baseline. The normal local app at `127.0.0.1:8501` now opens the English demo successfully.
- [ ] Back up the old `macrosense_db` database and obtain explicit approval identifying the exact deletion target before removing it. It has not been deleted or replaced.

## Completed milestones

- [x] Set up the virtual environment (venv) and installed Streamlit.
- [x] Completed Chapters 1, 2 and 3 of the thesis in Romanian.
- [x] Completed UML and ERD diagrams and updated their names to English.
- [x] Created the `macrosense_db` database in PostgreSQL.
- [x] Ran the final `schema.sql` script in pgAdmin.
- [x] OOP refactor: created the folder architecture (`/models`).
- [x] Implemented the authentication package (`UserAccount`, `User`, `Admin`).
- [x] Connected the Streamlit interface in `app.py` to the OOP models.
- [x] Implemented `FoodItem` and `Activity` in the Tracking package, following the OOP class diagram.
- [x] Built the catalog interface for adding and viewing data.
- [x] Authentication refactor (UI and OOP): unified login with role-based routing, resolved abstract-class instantiation issues and limited catalog editing privileges to the Administrator.
- [x] Architecture/documentation alignment: added `quantity_g` to the `FoodLog` class and table, and required `duration_min` in `activity_logs` for accurate MET calculations.
- [x] Implemented `DailyLog` with `get_or_create`, OOP-safe `recalculate_totals` prepared for custom meals, and `get_food_entries`.
- [x] Implemented `FoodLog` with XOR validation (`food_id` versus `custom_meal_id`) and `quantity_g` persistence.
- [x] Implemented the Streamlit Food Journal page with an entry form, estimated calorie preview and daily energy balance.
- [x] Session optimization: stored `user_id` in `st.session_state` at login, removing a database round trip on every render.
- [x] UI fixes: localized month names to Romanian, hid database IDs in the table and migrated `use_container_width` to `width='stretch'`.
- [x] Registration update (UI and OOP): collected initial user weight and saved it atomically in `weight_logs` to support subsequent MET calculations. Updated thesis section 3.2.
- [x] Implemented `ActivityLog` in Tracking with object-level `duration_min > 0` validation (`ValueError`) and `save()` persistence in `activity_logs`.
- [x] Extended `DailyLog.recalculate_totals()` to calculate both intake (`food_logs`) and activity calories: hybrid TUT for `Forță` and classic MET for Cardio/Other. It uses history from `weight_logs`: the latest weight on or before the day, the first available weight for dates before the first measurement, and 70 kg only when weight history is empty.
- [x] Implemented `DailyLog.get_activity_entries(log_id)` and `DailyLog.get_latest_weight()` to query activity history and calculate calories burned for each row dynamically.
- [x] Activity Journal UI refactor: moved `st.selectbox` outside the form for reactive category changes. Sets/repetitions appeared only for `Forță` with `min_value=1` and were hidden for Cardio, Flexibility and Team Sport.
- [x] Corrected UI metrics: Activity Journal showed Strength Calories (TUT) versus Cardio and Other Calories (MET); Food Journal showed intake, calories burned and energy balance correctly.
- [x] Food/Activity Journal polish: removed `st.form` to support live calorie previews as inputs change. Field resets after saving remained handled through `st.rerun()`.
- [x] Admin/User catalog polish: hid database/Pandas indexes in all four food and activity catalog tables for a consistent presentation.
- [x] Activity Journal polish: redesigned metrics as a 3+2 layout, with Strength Calories, Cardio and Other Calories, and Total Calories Burned above centered Calories Consumed and Energy Balance.
- [x] Implemented `RecipeIngredient` and `CustomMeal` in Tracking using the existing `custom_meals` and `recipe_ingredients` structures in `schema.sql`.
- [x] Implemented `CustomMeal.calculateTotalMacros()` as specified by the UML diagram, alongside the Python-style `calculate_total_macros()`.
- [x] Implemented atomic custom-meal and ingredient saving through `CustomMeal.create_with_ingredients()`.
- [x] Integrated custom meals into `DailyLog.recalculate_totals()` so `total_calories_in` includes both catalog foods and consumed custom meals.
- [x] Extended `DailyLog.get_food_entries()` to display mixed journal entries: `Aliment` and `Masă personalizată`.
- [x] Implemented the Streamlit Custom Meals page: recipe creation, ingredient selection, calorie/macronutrient preview, saving and ingredient viewing.
- [x] Extended Food Journal to save either a catalog food or a custom meal while respecting the `FoodLog` XOR constraint.
- [x] Removed technical `#id` suffixes from food and custom-meal selectboxes, retaining IDs internally for reliable selection.
- [x] Custom Meals polish: organized preview metrics into two rows, with Quantity/Calories above Protein/Carbohydrates/Fats.
- [x] Added OOP and UI validation requiring custom-meal names to start with a letter, not a digit or special character.
- [x] Database access hardening: added `try/except/finally` to `FoodItem.get_all_as_dataframe()` and `Activity.get_all_as_dataframe()`, following the project rule.
- [x] Implemented Food Journal deletion: `FoodLog.delete()` checks ownership; the UI requires confirmation and recalculates daily totals afterward.
- [x] Implemented Food Journal editing: `FoodLog.update()` changes quantity, meal type and time with ownership checks and automatic daily total recalculation.
- [x] Stabilized Food Journal editing/deletion with isolated `st.fragment()` panels, `st.toast()` messages and removal of flicker caused by table placeholders.
- [x] Implemented Activity Journal editing/deletion: `ActivityLog.update()` and `ActivityLog.delete()` check ownership and automatically recalculate daily totals after each operation.
- [x] Stabilized Activity Journal with reactive `st.fragment()` panels, selectboxes using internal IDs and `st.toast()` confirmation messages.
- [x] Implemented Custom Meals editing: `CustomMeal.update_with_ingredients()` updates the name and ingredients atomically without recalculating historical Food Journal entries.
- [x] Extended Custom Meals with an edit panel for renaming, adding/removing ingredients, adjusting quantities and recalculating the calorie/macronutrient preview.
- [x] Custom Meals polish: moved CSS to `assets/style.css`, displayed meals as compact rows/cards and compacted ingredient tables with `column_config`.
- [x] Global UI polish: standardized compact tables across Admin, Food Journal, Activity Journal and catalogs, with distinct save/delete button colors.
- [x] Implemented custom-meal archive/restore: archived meals remain in food history but are unavailable for new Food Journal entries until restored.
- [x] Tracking refactor: moved `FoodItem`, `Activity`, `FoodLog`, `ActivityLog`, `RecipeIngredient`, `CustomMeal` and `DailyLog` into dedicated `models/tracking_models/` modules, retaining `models/tracking.py` as a compatible import facade.
- [x] UI refactor: reduced `app.py` to the entrypoint/routing and moved Streamlit pages/helpers into `ui/` (`config`, `tables`, `formatters`, `pages`).
- [x] Post-refactor stabilization: added `unittest` coverage in `tests/` for architectural imports, OOP validation (`FoodLog`, `ActivityLog`, `CustomMeal`, `RecipeIngredient`) and `DailyLog` calculations.
- [x] Implemented `WeightLog` as a dedicated OOP weight-history class with `save()`, `update()`, `delete()`, history queries and daily-log recalculation after weight changes.
- [x] Implemented the Streamlit Weight Journal page with adding, editing, controlled deletion, history tables and latest-weight metrics.
- [x] Stabilized `WeightLog`: aligned UI/model validation at 30-300 kg, warned when updating an existing date and limited recalculation to workout days whose weight reference actually changes. Activity Journal warns when MET uses the first available weight for an earlier date.
- [x] Stabilized `DailyLog`: viewing a date in Food/Activity Journal no longer creates empty `daily_logs` rows. A daily row is created only when saving the first real entry and removed automatically when the day's last food/workout entry is deleted.
- [x] Registration stabilization: initial weight is no longer clamped to 30 kg; values outside 30-300 kg produce explicit errors in the UI and `User.register()`.
- [x] Extended the food catalog with provenance metadata (`source`, `source_type`, `external_id`, `source_url`) and a uniqueness constraint for external imports.
- [x] Implemented Administrator-only USDA FoodData Central import: searches non-branded `SR Legacy`, `Foundation` and `Survey (FNDDS)` sources, previews nutrition per 100 g, checks duplicates and saves locally to `food_items`.
- [x] Added `database/seeds/seed_food_items_usda_starter.sql` with more than 170 USDA FoodData Central foods across the main MacroSense categories.
- [x] Food Catalog stabilization: manually added foods display `MacroSense` as their source, tables support search/filters, USDA results use a clear list and local categories are suggested from USDA descriptions.
- [x] Admin Food Catalog validation: manually added foods cannot have an empty name or all-zero nutritional values.
- [x] USDA search stabilization: the UI explains that search terms should be English, and the client requires the USDA description to contain the search terms, reducing irrelevant results and loading time.
- [x] Food Journal selection stabilization: replaced the catalog selectbox with name search, a category filter and a selectable table suitable for large catalogs.
- [x] Food Journal polish: meal-type choices for new food/custom-meal entries use visible radio options; remaining dropdowns have improved CSS contrast.
- [x] Food Catalog/USDA review hardening: table searches treat special characters as plain text, journal table selection resets when filters change, USDA import rejects unsupported API sources and filtering handles common plurals.
- [x] Model/UI/DB review hardening: escaped user text in custom HTML, trimmed email whitespace without lowercasing, tightened `Activity`/`ActivityLog` validation, removed `.0` from sets/repetition display and added integrity constraints to `schema.sql`.
- [x] Registration stabilization: errors identify duplicate email, invalid profile, invalid weight or database connection problems instead of always claiming that the email already exists.
- [x] UI validation stabilization: custom-meal names reject obvious HTML characters (`<`, `>`); Admin MET input is no longer clamped to 0.9 by Streamlit, and values below the minimum produce an explicit error.
- [x] Food Journal/Custom Meals stabilization after USDA import: food choices show sources (`MacroSense`, `USDA SR`, `USDA Foundation`, `USDA FNDDS`), search ignores accents, ingredient selection uses a searchable/filterable table, `FoodLog` validates `meal_type` and daily metrics also appear on workout-only days.
- [x] Catalog/journal validation hardening: `FoodItem` validates names, categories and nutrition; USDA import skips all-zero nutrition; catalog searches ignore accents; `FoodLog` requires a valid time; the schema rejects partially populated `sets`/`reps` pairs.
- [x] Registration stabilization: Streamlit no longer clamps height/age to minimum or maximum values; the UI and `User.register()` reject invalid values explicitly.
- [x] Admin Catalog polish: save buttons use the same green as User flows, food names survive validation errors and obvious HTML characters in food names are blocked by the UI, model and schema.
- [x] Text and nutrition hardening: persistent user, food, activity and custom-meal text rejects obvious HTML characters (`<`, `>`); foods require calories > 0 and at least one macronutrient > 0.
- [x] Admin Food Catalog validation stabilization: nutrition fields no longer use Streamlit clamping, negative inputs produce explicit errors and the form shows only the first validation error at a time.
- [x] Food Journal/Custom Meals quantity validation: gram inputs no longer use Streamlit clamping; values below 1 g or above 5000 g are rejected manually before saving.
- [x] Custom Meals preview stabilization: invalid quantities no longer enter ingredient tables or affect displayed totals/macronutrients.
- [x] Model/DB quantity hardening: `FoodLog`, `RecipeIngredient`, `CustomMeal.create_with_ingredients()`, `CustomMeal.update_with_ingredients()` and `schema.sql` enforce the same 1-5000 g interval as the UI.
- [x] Journal user isolation: `DailyLog.get_food_entries()` and `DailyLog.get_activity_entries()` accept `user_id`, which Food/Activity Journal explicitly supplies when reading entries.
- [x] User navigation stabilization: the sidebar permanently shows all pages, including Home, replacing a scrollable dropdown that hid the first option.
- [x] Extended activity provenance: `Activity` and `activities` support `source`, `source_type`, `external_id`, `source_url`, `met_source_code`, `met_source_description` and `met_estimation_method`, distinguishing official Compendium entries from MacroSense mappings.
- [x] Added `seed_activities_compendium_official.sql` for official 2024 Adult Compendium MET activities and `seed_activities_macrosense_mappings.sql` for practical gym exercises explicitly mapped to general Compendium codes.
- [x] Added optional manual calories to Activity Journal: watch/cardio-machine calories override the MET/TUT formula only for the corresponding entry.
- [x] WeightLog recalculation stabilization: days containing only manually entered activity calories are no longer counted as affected by weight changes.
- [x] Activity Catalog polish: Admin/User tables include search and category/source/MET-method filters, with clear `Compendium` versus `MacroSense` labels.
- [x] Activity Journal stabilization after catalog expansion: replaced the activity selectbox with a filterable selectable table; duration, sets, repetitions and manual calories share manual validation that avoids native Streamlit warnings retaining old values.
- [x] Activity Journal duration update: `duration_min` supports 0.1-600 minutes for very short exercises/sets, with consistent display and UI/model/DB validation.
- [x] Persistent text validation: food/activity names require at least one letter; full names allow only letters, spaces, hyphens and apostrophes. The UI, models and `schema.sql` enforce these rules.
- [x] Daily list polish: Food, Activity and Weight Journal entries use compact rows/cards instead of raw tables, without changing save/edit/delete behavior.
- [x] Custom Meals history stabilization: `food_logs` stores nutrition snapshots per 100 g; `DailyLog.recalculate_totals()` and journal display use them so recipe edits affect future uses only.
- [x] Custom Meals snapshot hardening: `schema.sql` requires a complete snapshot for every custom-meal log entry; recipe edits do not recalculate history, and the UI no longer shows technical messages about recalculated journals.
- [x] Demo Data Foundation: added `database/seeds/seed_demo_users.sql` with five synthetic users, documented test passwords, varied weight-history periods, food logs, estimated/manual activities and custom meals with snapshots.
- [x] Dashboard v1 and Analytics: added `services/analytics` with pure BMI/BMR/estimated TDEE formulas, read-only aggregation, summary cards and charts for weight, intake versus TDEE, estimated balance, macronutrients and activity. Dashboard does not create `daily_logs` and treats days without food as missing data, not 0 kcal intake.
- [x] Dashboard v1.1 hardening: added weight-reference metadata (source, imputation, future fallback, day distance), a past-only helper for future ML use, separate food/workout/weight/overall consistency and average protein per kg. Replaced dashboard cards with more readable local HTML/CSS without labels truncated by `...`.
- [x] Aligned UI/model/DB validation: standardized user goals to `Slabire`, `Mentinere` and `Crestere`; required custom-meal names to start with a letter in `schema.sql`; aligned activity sets/repetition limits across all three layers.
- [x] Centralized local food/activity categories in `ui/catalog_constants.py`; tests verify that seeds do not introduce categories missing from the UI.
- [x] Journal date hardening: Food, Activity and Weight Journal reject future saves in UI/models; `schema.sql` adds triggers for `daily_logs` and `weight_logs`.
- [x] Weight prediction ML v1: added `services/ml` with synthetic generation, feature engineering designed to avoid leakage, Ridge/Random Forest/Gradient Boosting training, artifact persistence and CLI smoke-check/training/prediction utilities.
- [x] ML v1 evaluation: added backtesting on separate synthetic data, comparisons with `no_change`, `trend_projection` and `energy_balance_projection` baselines, and deficit/surplus/activity sanity checks.
- [x] ML training stabilization: added conservative hybrid energy/trend candidates that combine energy estimates with actual weight trends and apply a bounded ML correction for predictions consistent with user history.
- [x] Dashboard v2 weight prediction: Home displays 14- and 30-day ML predictions directly below the current state, with fallback to the latest day with sufficient data.
- [x] Historical demo seed update: `seed_demo_users.sql` extended demo histories through 23 May 2026 and calibrated recent food intake to align ML predictions better with actual weight trends.
- [x] ML/Dashboard v2 stabilization: regenerated artifacts using 50 synthetic users and 150 history days, saved training context in metadata, added controlled fallback for incomplete days and removed the 40-row catalog truncation from Food Journal, Activity Journal and Custom Meals selectors.
- [x] What-if simulator v1: added a read-only food/activity scenario page with session-only changes, real-versus-simulated comparison, theoretical 14/30-day impact, UI/pure-service validation and no database writes.
- [x] Explainable dashboard recommendations: added four cards for food, protein, activity and progress, based on existing metrics and weight predictions when available. Meal-plan and workout-program generation remains in the backlog.
- [x] Shared Food/Activity Journal energy summary: intake, activity calories, estimated TDEE and estimated balance, with missing-data display for days without food.
- [x] EN/RO interface: added English source text, a Romanian translation catalog and a local-flag selector. Language persists in session and after logout; EN is the default, configurable through `MACROSENSE_DEFAULT_LANGUAGE`.
- [x] Language-switch stabilization: added stable Auth/User/Admin navigation IDs, synchronization of translated selections and preservation of unsaved reactive-form values. Switching language preserves canonical database values and catalog names.

## Validation and work in progress

- [x] Earlier full `unittest` validation passed with mocked DB/HTTP connections; PostgreSQL integration remains a separate check. The latest test counts and regression limits are recorded in the current checkpoint above.
- [x] Earlier local visual check without saving covered Dashboard, food preview with EN/RO selection retention, duration validation, weight/meal/catalog navigation, What-if editing/reset and Admin Activities EN→RO→EN without `KeyError`. It did not verify real save/edit/delete operations or the new English demo database.
- [ ] Reproduce and assess the navigation issue: after editing duration and quickly selecting Weight Journal, the menu showed Weight while Activity Journal content remained visible. Separate navigation worked; possible overlapping reruns still need investigation before code changes.
- [x] Translated STATUS and AGENTS into English and updated README demo accounts/setup for the English demo checkpoint, preserving the existing architecture diagram and file guide.
- [x] Reviewed the English documentation and added five real README screenshots: welcome, dashboard predictions, Food Journal, What-if and Admin USDA search/preview. Captures use demo accounts; the USDA example did not import a food.
- [ ] Verify the diagram's GitHub rendering separately. Local documentation checks do not establish its rendered appearance on GitHub.
- [x] Fixed the ML-loader's nullable-strength case in `services/ml/prediction.py`: check `pd.notna()` before converting sets/repetitions to integers. Valid pairs retain TUT; missing pairs use the existing duration-based MET fallback. Regression coverage includes `None`, `NaN`, `pd.NA`, nullable integer columns, manual-calorie precedence, past-only weights and unchanged input frames. The current Strength UI requires positive sets/repetitions; this protects valid nullable DB/model inputs rather than adding a new UI option.
- [x] Stabilized What-if summation with `math.fsum` followed by the existing two-decimal rounding. The earlier muscle-gain scenario's 0.01 g discrepancy no longer occurs in live old/new database comparisons. Regression tests verify all 120 orders of five food contributions and all 120 orders of five activity contributions. No calorie formula, schema, seed or model artifact was changed.
- [x] Post-fix browser smoke test: the weight-loss demo dashboard still shows 75.4/74.4 kg predictions on 27 May. In What-if for that date, changing blueberries from 103.55 g to 150 g gives +0.05/+0.12 kg theoretical impact; Reset restores 103.55 g and zero impact. No real journal entries were edited in this smoke test.
- [ ] Review selected pre-existing food nutrition values against upstream sources. Source mismatches have not yet been confirmed; the English-name update intentionally preserved the numerical values.

## Release follow-up and backlog

- [x] PR 1, `feature/bilingual-ui-pr` → `main`, merged at `530b789`.
- [ ] Prepare the public demo on a disposable synthetic database, with all existing Demo Admin functions enabled. Keep technical database credentials and API secrets private; credential setup and password-hashing hardening remain pending. No additional Demo Admin or account-creation restrictions are planned.
- [ ] Deployment PR: hosted PostgreSQL, secrets, ML artifact delivery, startup checks and a rollback procedure.
- [ ] Personalized meal recommendations.
- [ ] Personalized workout recommendations.
- [ ] Optional database triggers to synchronize `daily_logs` totals after direct changes to `food_logs`/`activity_logs`; deferred to avoid unnecessary complexity in this milestone.
- [ ] Synchronize thesis documentation/diagrams when the `docs/` files become available.
