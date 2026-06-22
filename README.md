# MacroSense

MacroSense is a Python + Streamlit web application for nutrition, activity, and weight tracking.
It was built as a bachelor's degree project and focuses on turning daily logs into useful health and fitness insights.

The application combines food logging, workout tracking, custom meals, body weight history, dashboard analytics, machine learning weight predictions, and a read-only What-if simulator.

## Main Features

- User and administrator authentication
- Food journal with calories and macronutrient tracking
- Activity journal with MET/TUT-based calorie estimation and optional manual calorie input
- Weight journal with historical body weight tracking
- Custom meals built from catalog ingredients
- Dashboard with BMI, BMR, estimated TDEE, calorie balance, charts, recommendation cards, and 14/30-day weight predictions
- What-if simulator for comparing the real day with a simulated scenario
- Admin pages for managing food and activity catalogs
- Optional USDA FoodData Central import for food items
- PostgreSQL schema with validation constraints for data integrity
- Unit tests for validation logic, analytics, ML helpers, routing, and UI helper functions

## Tech Stack

- Python 3
- Streamlit
- PostgreSQL
- psycopg2
- pandas
- Altair
- scikit-learn
- unittest

## Project Structure

```text
app.py                      Streamlit entrypoint and role-based routing
database.py                 PostgreSQL connection helper
schema.sql                  Main database schema
assets/style.css            Local UI styling
ui/                         Streamlit pages, routes, UI helpers, formatters
models/                     Domain models for authentication and tracking
services/analytics/         BMI, BMR, TDEE and dashboard aggregation logic
services/ml/                Feature engineering, training and prediction helpers
services/what_if/           Read-only scenario simulation logic
services/recommendations/   Explainable dashboard recommendation cards
database/seeds/             Optional seed data for catalogs and demo users
tests/                      Automated unittest suite
```

## Local Setup

1. Create and activate a virtual environment:

```bash
python -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt
```

2. Create a local PostgreSQL database named:

```text
macrosense_db
```

3. Run `schema.sql` manually in pgAdmin or another PostgreSQL client.

4. Optional seed files can be run in this order:

```text
database/seeds/seed_food_items_usda_starter.sql
database/seeds/seed_activities_compendium_official.sql
database/seeds/seed_activities_macrosense_mappings.sql
database/seeds/seed_demo_users.sql
```

5. Configure the local database credentials in `database.py` for your own PostgreSQL setup.

6. Optional, for USDA food import, configure an API key:

```text
.streamlit/secrets.toml

FDC_API_KEY = "your_api_key_here"
```

7. Optional, if ML model artifacts are not present locally, generate them:

```bash
./venv/Scripts/python.exe -m services.ml.train_models --user-count 50 --history-days 150
```

8. Start the application:

```bash
./venv/Scripts/python.exe -m streamlit run app.py
```

## Running Tests

```bash
./venv/Scripts/python.exe -m unittest discover -s tests -v
```

## Notes

- The Streamlit interface is written in Romanian.
- The codebase uses English names for classes, methods, variables, and modules.
- The application uses PostgreSQL directly through `psycopg2`, without an ORM.
- The dashboard is read-only and does not create empty daily logs when users only inspect data.
- The What-if simulator is also read-only and does not write simulated values to the database.

## Before Publishing Publicly

Before making this repository public, make sure that no private data is included:

- no `.streamlit/secrets.toml`
- no `.env`
- no real database dumps
- no API keys
- no personal user data
- no private thesis documents, unless you intentionally want to publish them

## Status

MacroSense is a functional academic project and prototype. The main tracking flows, dashboard analytics, ML prediction flow, What-if simulator, admin catalog management, and validation tests are implemented.
