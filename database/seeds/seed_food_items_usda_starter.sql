-- Starter USDA food catalog for MacroSense.
-- Run after schema.sql in pgAdmin.
-- Source: USDA FoodData Central, using SR Legacy and Foundation records.

INSERT INTO food_items (
    name,
    calories_100g,
    protein_g,
    carbs_g,
    fats_g,
    category,
    source,
    source_type,
    external_id,
    source_url
)
VALUES
    (
        'Banane, crude',
        89.00,
        1.09,
        22.80,
        0.33,
        'Fructe',
        'USDA',
        'SR Legacy',
        '173944',
        'https://fdc.nal.usda.gov/fdc-app.html#/food-details/173944/nutrients'
    ),
    (
        'Mere Fuji cu coaja, crude',
        58.20,
        0.15,
        15.40,
        0.16,
        'Fructe',
        'USDA',
        'Foundation',
        '1750340',
        'https://fdc.nal.usda.gov/fdc-app.html#/food-details/1750340/nutrients'
    ),
    (
        'Capsuni, crude',
        32.00,
        0.67,
        7.68,
        0.30,
        'Fructe',
        'USDA',
        'SR Legacy',
        '167762',
        'https://fdc.nal.usda.gov/fdc-app.html#/food-details/167762/nutrients'
    ),
    (
        'Rosii rosii coapte, crude',
        18.00,
        0.88,
        3.89,
        0.20,
        'Legume',
        'USDA',
        'SR Legacy',
        '170457',
        'https://fdc.nal.usda.gov/fdc-app.html#/food-details/170457/nutrients'
    ),
    (
        'Morcovi, cruzi',
        41.00,
        0.93,
        9.58,
        0.24,
        'Legume',
        'USDA',
        'SR Legacy',
        '170393',
        'https://fdc.nal.usda.gov/fdc-app.html#/food-details/170393/nutrients'
    ),
    (
        'Broccoli, crud',
        31.00,
        2.57,
        3.80,
        0.34,
        'Legume',
        'USDA',
        'Foundation',
        '747447',
        'https://fdc.nal.usda.gov/fdc-app.html#/food-details/747447/nutrients'
    ),
    (
        'Cartofi cu coaja, cruzi',
        77.00,
        2.05,
        17.50,
        0.09,
        'Legume',
        'USDA',
        'SR Legacy',
        '170026',
        'https://fdc.nal.usda.gov/fdc-app.html#/food-details/170026/nutrients'
    )
ON CONFLICT ON CONSTRAINT uq_food_source_external DO NOTHING;
