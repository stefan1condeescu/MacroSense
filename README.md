# MacroSense

MacroSense is a Python and Streamlit web application for nutrition tracking, physical activity tracking, body weight monitoring, dashboard analytics, and machine-learning-assisted fitness insight.

It was developed as a bachelor's degree project and is designed to show how a daily health journal can become more than a place where users enter numbers. The application connects food intake, exercise, body weight history, user goals, data validation, analytics, and prediction into one coherent local system.

The interface is written in Romanian for the target users, while the codebase, database objects, and project structure use English names.

## What The Application Does

MacroSense supports two main roles:

- Administrators manage the food and activity catalogs, including optional imports from USDA FoodData Central.
- Users track meals, workouts, body weight, custom meals, dashboard progress, ML predictions, and What-if scenarios.

The application includes:

- Role-based authentication for users and administrators.
- Food logging with calories, protein, carbohydrates, fats, meal type, quantity, time, edit, and delete flows.
- Activity logging with MET-based calorie estimation, TUT-inspired strength estimation, optional manual calorie override, edit, and delete flows.
- Body weight history with add, update, delete, reference-weight logic, and automatic recalculation of affected activity days.
- Custom meals built from catalog ingredients, with macro preview, archive/reactivate behavior, and historical nutrition snapshots.
- A read-only dashboard with BMI, BMR, estimated TDEE, calorie balance, consistency indicators, charts, recommendation cards, and 14/30-day weight predictions.
- A read-only What-if simulator that compares the real day with a simulated food and activity scenario.
- Admin catalog pages for foods and activities, with search, filters, source metadata, validation, and USDA import.
- PostgreSQL data integrity rules, constraints, triggers, and seed scripts.
- A structured OOP codebase with separate models, services, UI pages, analytics helpers, ML helpers, and tests.

## Tech Stack

- Python 3.12.
- Streamlit for the web interface.
- PostgreSQL for persistence.
- psycopg2 for direct database access.
- pandas for tabular transformations and analytics.
- Altair for dashboard visualizations.
- scikit-learn for model training and prediction.
- unittest for automated regression tests.
- pgAdmin for optional database inspection and SQL script execution.
- USDA FoodData Central API for optional live food import.

## Main User Workflows

### Authentication And Roles

MacroSense separates regular users from administrators.

Administrators can:

- Add and inspect food catalog items.
- Add and inspect activity catalog items.
- Import food items from USDA FoodData Central when an API key is configured.
- Manage catalog data used by the user-facing journals.

Users can:

- Register and log in.
- Track food, activities, weight, and custom meals.
- Inspect dashboard analytics and predictions.
- Run What-if simulations without changing saved data.

### Food Journal

The food journal allows users to record daily intake from either individual catalog foods or saved custom meals.

Implemented behavior includes:

- Quantity-based calorie and macronutrient calculation.
- Meal type selection.
- Time of consumption.
- Live preview before saving.
- Edit and delete operations.
- Automatic recalculation of daily totals after every change.
- Searchable and filterable catalog selection.
- Source labels that distinguish MacroSense foods from USDA foods.
- Validation across UI, model layer, and database.

### Activity Journal

The activity journal tracks workouts and daily movement.

The application supports:

- Activity selection from a catalog with category, source, and MET-method filters.
- MET-based calorie estimation for cardio, flexibility, sports, and general activities.
- TUT-style estimation for strength activities using sets and repetitions.
- Optional manual calorie input when the user wants to use a value from a watch, treadmill, bike, or other device.
- Decimal durations for short activity segments.
- Edit and delete flows.
- Automatic daily total recalculation.
- Weight-aware calorie estimation using the most relevant available weight log.

### Weight Journal

The weight journal records the user's body weight over time.

It is used by:

- Dashboard progress charts.
- Activity calorie calculations.
- ML feature engineering.
- Future weight prediction.

When a weight entry changes, MacroSense recalculates only the affected daily logs instead of blindly recalculating everything.

### Custom Meals

Users can build reusable meals from catalog ingredients.

Custom meal functionality includes:

- Ingredient selection from the food catalog.
- Quantity per ingredient.
- Live calorie and macronutrient preview.
- Atomic save/update behavior.
- Archive and reactivate support.
- Historical snapshots, so editing a recipe later does not rewrite old food journal entries.

This is important because a meal logged last month should keep the nutrition values it had when it was consumed, even if the saved recipe changes later.

### Dashboard

The dashboard is read-only. It analyzes existing data without creating empty daily logs.

It includes:

- BMI calculation.
- BMR calculation.
- Estimated TDEE.
- Daily and interval calorie balance.
- Weight evolution.
- Calories consumed versus estimated expenditure.
- Macronutrient charts.
- Activity summaries.
- Food, activity, weight, and general consistency indicators.
- Protein per kilogram body weight.
- Recommendation cards based on the user's goal and recent behavior.
- ML-based weight predictions for 14 and 30 days.

The dashboard treats missing food data as missing data, not as zero calories. This avoids misleading analytics when a user simply did not log food for a day.

### Machine Learning Weight Prediction

MacroSense includes a local ML pipeline for future weight-change prediction.

The ML module contains:

- Synthetic history generation for training and validation.
- Leakage-safe feature engineering, using only data available up to the analysis date.
- Training for 14-day and 30-day horizons.
- Model comparison between simple regressors, tree models, and conservative hybrid energy-trend models.
- Evaluation utilities with baselines and sanity checks.
- Saved model artifacts with metadata.
- Live prediction helpers used by the dashboard.

The locally generated artifacts are saved in:

```text
artifacts/ml/
```

The training command used for the current local setup was:

```bash
.venv/bin/python -m services.ml.train_models --user-count 50 --history-days 150
```

This generated:

```text
artifacts/ml/weight_prediction_14d.joblib
artifacts/ml/weight_prediction_14d_metadata.json
artifacts/ml/weight_prediction_30d.joblib
artifacts/ml/weight_prediction_30d_metadata.json
```

### What-if Simulator

The What-if simulator lets the user compare the real selected day with a temporary simulated scenario.

It supports:

- Editing simulated food quantities.
- Adding simulated foods.
- Editing simulated activities.
- Adding simulated activities.
- Comparing real totals with simulated totals.
- Estimating a theoretical 14/30-day impact from repeated calorie differences.
- Keeping all changes in session state only.

The simulator is intentionally read-only at the database level. It does not write simulated values to PostgreSQL.

## Administrator Features

### Food Catalog

The administrator can manage foods manually and import foods from USDA FoodData Central.

Food items store:

- Name.
- Category.
- Calories per 100g.
- Protein, carbohydrates, and fats per 100g.
- Source metadata.
- External USDA id and source URL when imported.

The USDA import supports the following non-branded data types:

- SR Legacy.
- Foundation.
- Survey (FNDDS).

The import panel searches in English, filters unsupported USDA data types, removes duplicate imports, rejects incomplete nutrition data, and suggests a local MacroSense category.

To enable USDA import, create:

```text
.streamlit/secrets.toml
```

with:

```toml
FDC_API_KEY = "your_usda_fooddata_central_key"
```

The secrets file is intentionally ignored by git.

### Activity Catalog

The administrator can manage activity definitions used by the activity journal.

Activity items include:

- Name.
- Category.
- MET value.
- Source.
- Source type.
- External id.
- Source URL.
- Compendium code and description when applicable.
- MET estimation method.

The project includes seed data from the 2024 Adult Compendium and additional MacroSense gym mappings for practical strength-training activities.

## Database

MacroSense uses PostgreSQL directly through `psycopg2`, without an ORM.

The main database is:

```text
macrosense_db
```

The default local connection used by `database.py` is:

```text
Host: localhost
Port: 5432
Database: macrosense_db
User: postgres
Password: 9999
```

Main tables:

```text
users
admins
food_items
activities
weight_logs
daily_logs
custom_meals
recipe_ingredients
activity_logs
food_logs
```

The schema includes constraints for:

- Valid email and text input.
- Supported gender and goal values.
- Food nutrition rules.
- Activity duration and MET rules.
- Weight range.
- Quantity range.
- Future-date prevention.
- Custom meal snapshot integrity.
- Consistent food-log source selection.
- Consistent sets/reps pairs.

## Seed Data

The project includes SQL seed files that make the application presentation-ready.

Recommended order:

```text
schema.sql
database/seeds/seed_food_items_usda_starter.sql
database/seeds/seed_activities_compendium_official.sql
database/seeds/seed_activities_macrosense_mappings.sql
database/seeds/seed_demo_users.sql
```

The seed data adds:

- A default administrator account.
- More than 170 USDA-based starter food items.
- Official Compendium activity entries.
- Practical MacroSense activity mappings.
- Five synthetic demo users.
- Weight history.
- Food logs.
- Activity logs.
- Custom meals and historical snapshots.

## Demo Accounts

After running the schema and seed files, the following accounts are available.

Administrator:

```text
Email: admin@test.com
Password: parola123
```

Demo users:

```text
demo.slabire@test.com
demo.masa@test.com
demo.mentinere@test.com
demo.activ@test.com
demo.rar@test.com
```

All demo users use:

```text
Password: test123
```

## Local Setup

The commands below are written for macOS/Linux-style terminals.

### 1. Create A Virtual Environment

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 2. Start PostgreSQL

On macOS with Homebrew:

```bash
brew services start postgresql@16
```

### 3. Create And Initialize The Database

Create a PostgreSQL database named:

```text
macrosense_db
```

Then run the SQL files in the seed order shown above. This can be done from pgAdmin Query Tool or from `psql`.

### 4. Optional USDA API Key

Create:

```text
.streamlit/secrets.toml
```

and add:

```toml
FDC_API_KEY = "your_usda_fooddata_central_key"
```

### 5. Optional ML Artifact Generation

If `artifacts/ml/` is missing, generate the local model artifacts:

```bash
.venv/bin/python -m services.ml.train_models --user-count 50 --history-days 150
```

### 6. Start The Application

```bash
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Open:

```text
http://127.0.0.1:8501
```

## pgAdmin Configuration

pgAdmin is optional, but useful for presenting the database and showing the SQL seed files.

Create a new server with:

```text
Name: MacroSense Local
Host name/address: 127.0.0.1
Port: 5432
Maintenance database: postgres
Username: postgres
Password: 9999
```

Then open:

```text
Servers
  MacroSense Local
    Databases
      macrosense_db
        Schemas
          public
            Tables
```

To run SQL files manually, right-click `macrosense_db`, open Query Tool, paste or open the SQL file, and execute it.

## Running Tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The test suite covers:

- Model validation.
- Authentication helper behavior.
- Food, activity, weight, and custom meal logic.
- Dashboard analytics.
- ML feature engineering, artifacts, training, evaluation, and prediction helpers.
- What-if simulation.
- USDA client parsing and filtering.
- UI helper functions and routing behavior.
- SQL seed consistency.

The local setup used for presentation passed 304 automated tests.

## Project Structure

```text
app.py                      Streamlit entrypoint and role-based routing
database.py                 PostgreSQL connection helper
schema.sql                  Main PostgreSQL schema
assets/style.css            Shared local UI styling
ui/                         Streamlit pages, routes, UI helpers, tables, formatting
models/                     Authentication and domain models
models/tracking_models/     Food, activity, daily log, custom meal, and weight classes
services/analytics/         BMI, BMR, TDEE, dashboard aggregation, and summary logic
services/ml/                Synthetic data, feature engineering, training, artifacts, prediction
services/what_if/           Read-only What-if simulation and loaders
services/recommendations/   Explainable dashboard recommendation cards
database/seeds/             SQL seed files for foods, activities, and demo users
tests/                      Automated unittest suite
```

## Engineering Highlights

MacroSense was built with several implementation goals in mind:

- Keep domain logic in Python model and service layers, not only inside Streamlit pages.
- Keep database writes explicit and controlled.
- Apply validation consistently in UI, models, and PostgreSQL constraints.
- Prevent future-date writes for journals.
- Preserve historical custom-meal nutrition snapshots.
- Keep dashboard and What-if pages read-only.
- Avoid ML leakage by using only historical data available at the analysis date.
- Keep external USDA imports traceable through source metadata.
- Make seed data realistic enough for a live academic presentation.

## Suggested Presentation Flow

One possible walkthrough for a thesis presentation:

1. Open pgAdmin and show `macrosense_db`, the schema tables, and the seed files.
2. Start MacroSense and log in as the administrator.
3. Show the food and activity catalogs, including source labels and USDA import.
4. Log in as a demo user.
5. Open the dashboard and explain BMI, BMR, TDEE, calorie balance, charts, recommendations, and ML predictions.
6. Add or edit a food log entry and show automatic daily recalculation.
7. Add or edit an activity log entry and explain MET, TUT, and optional manual calories.
8. Show the weight journal and explain how weight history affects calculations.
9. Open custom meals and explain ingredient-based macro calculation plus historical snapshots.
10. Open the What-if simulator and compare a real day with a simulated scenario.
11. Mention the automated test suite and validation layers.

## Privacy And Publishing Notes

Before making the repository public, make sure the following files or data are not included:

- `.streamlit/secrets.toml`
- `.env`
- real database dumps
- API keys
- real personal user data
- private thesis documents, unless intentionally published

The included demo data is synthetic and intended for local presentation and testing.

## Current Status

MacroSense is a functional academic prototype with complete local workflows for:

- User and administrator authentication.
- Food, activity, weight, and custom meal tracking.
- Admin catalog management.
- USDA-backed food import.
- Dashboard analytics.
- ML-based weight prediction.
- Read-only What-if simulation.
- PostgreSQL-backed persistence.
- Automated validation and regression tests.

It is ready to be demonstrated locally with seeded data, pgAdmin, and Streamlit.
