-- Demo users and synthetic tracking history for MacroSense dashboards and ML flows.
-- Run after schema.sql, seed_food_items_usda_starter.sql and activity seeds.
-- All demo accounts use password: test123
-- The data is deterministic: it uses profile plans, meal patterns and activity schedules
-- instead of random values, so every run produces the same presentation dataset.

BEGIN;

DELETE FROM users WHERE email IN (
    'demo.slabire@test.com',
    'demo.masa@test.com',
    'demo.mentinere@test.com',
    'demo.activ@test.com',
    'demo.rar@test.com'
);

CREATE TEMP TABLE demo_profiles (
    email TEXT,
    full_name TEXT,
    registration_date DATE,
    height_cm NUMERIC(5,2),
    age INT,
    gender CHAR(1),
    goal TEXT,
    start_date DATE,
    end_date DATE,
    start_weight_kg NUMERIC(5,2),
    end_weight_kg NUMERIC(5,2),
    food_scale NUMERIC(5,2),
    food_pattern_count INT
) ON COMMIT DROP;

INSERT INTO demo_profiles (
    email,
    full_name,
    registration_date,
    height_cm,
    age,
    gender,
    goal,
    start_date,
    end_date,
    start_weight_kg,
    end_weight_kg,
    food_scale,
    food_pattern_count
) VALUES
    ('demo.slabire@test.com', 'Ana Demo', DATE '2026-02-06', 168, 29, 'F', 'Slabire', DATE '2026-02-07', DATE '2026-05-27', 82.32, 75.98, 1.18, 4),
    ('demo.masa@test.com', 'Mihai Demo', DATE '2026-02-23', 181, 25, 'M', 'Crestere', DATE '2026-02-23', DATE '2026-05-27', 70.98, 76.55, 1.20, 4),
    ('demo.mentinere@test.com', 'Ioana Demo', DATE '2026-02-23', 165, 34, 'F', 'Mentinere', DATE '2026-02-23', DATE '2026-05-27', 61.82, 62.50, 1.12, 4),
    ('demo.activ@test.com', 'Andrei Demo', DATE '2026-02-23', 178, 31, 'M', 'Mentinere', DATE '2026-02-23', DATE '2026-05-27', 78.36, 77.70, 1.28, 4),
    ('demo.rar@test.com', 'Radu Demo', DATE '2026-02-23', 175, 40, 'M', 'Slabire', DATE '2026-02-23', DATE '2026-05-27', 96.42, 93.05, 1.08, 3);

INSERT INTO users (
    email,
    password_hash,
    registration_date,
    full_name,
    height_cm,
    age,
    gender,
    goal
)
SELECT
    email,
    encode(sha256('test123'::bytea), 'hex'),
    registration_date,
    full_name,
    height_cm,
    age,
    gender,
    goal
FROM demo_profiles;

CREATE TEMP TABLE demo_days ON COMMIT DROP AS
SELECT
    p.email,
    generated.day_value::date AS log_date,
    (generated.day_value::date - p.start_date) AS day_index
FROM demo_profiles p
CROSS JOIN LATERAL generate_series(p.start_date, p.end_date, INTERVAL '1 day') AS generated(day_value);

CREATE TEMP TABLE demo_custom_meals (
    email TEXT,
    recipe_name TEXT
) ON COMMIT DROP;

INSERT INTO demo_custom_meals (email, recipe_name) VALUES
    ('demo.slabire@test.com', 'Bol proteic demo'),
    ('demo.masa@test.com', 'Pui cu orez demo'),
    ('demo.mentinere@test.com', 'Omleta verde demo'),
    ('demo.activ@test.com', 'Curcan demo');

INSERT INTO custom_meals (user_id, recipe_name, status)
SELECT
    u.id,
    m.recipe_name,
    'Salvată'
FROM demo_custom_meals m
JOIN users u ON u.email = m.email;

CREATE TEMP TABLE demo_recipe_ingredients (
    email TEXT,
    recipe_name TEXT,
    food_external_id TEXT,
    quantity_g NUMERIC(6,2)
) ON COMMIT DROP;

INSERT INTO demo_recipe_ingredients (email, recipe_name, food_external_id, quantity_g) VALUES
    ('demo.slabire@test.com', 'Bol proteic demo', '2705424', 180.00),
    ('demo.slabire@test.com', 'Bol proteic demo', '2709224', 80.00),
    ('demo.slabire@test.com', 'Bol proteic demo', '2707590', 12.00),
    ('demo.masa@test.com', 'Pui cu orez demo', '2646170', 220.00),
    ('demo.masa@test.com', 'Pui cu orez demo', '2710788', 260.00),
    ('demo.masa@test.com', 'Pui cu orez demo', '2709643', 120.00),
    ('demo.mentinere@test.com', 'Omleta verde demo', '172189', 120.00),
    ('demo.mentinere@test.com', 'Omleta verde demo', '168438', 70.00),
    ('demo.mentinere@test.com', 'Omleta verde demo', '173420', 35.00),
    ('demo.activ@test.com', 'Curcan demo', '171501', 180.00),
    ('demo.activ@test.com', 'Curcan demo', '2710789', 220.00),
    ('demo.activ@test.com', 'Curcan demo', '2710186', 10.00);

INSERT INTO recipe_ingredients (meal_id, food_id, quantity_g)
SELECT
    cm.id,
    fi.id,
    ri.quantity_g
FROM demo_recipe_ingredients ri
JOIN users u ON u.email = ri.email
JOIN custom_meals cm ON cm.user_id = u.id AND cm.recipe_name = ri.recipe_name
JOIN food_items fi ON fi.source = 'USDA' AND fi.external_id = ri.food_external_id;

CREATE TEMP TABLE demo_meal_snapshots ON COMMIT DROP AS
SELECT
    u.email,
    cm.id AS custom_meal_id,
    cm.recipe_name,
    ROUND((SUM(fi.calories_100g * ri.quantity_g) / NULLIF(SUM(ri.quantity_g), 0))::numeric, 2) AS calories_100g,
    ROUND((SUM(fi.protein_g * ri.quantity_g) / NULLIF(SUM(ri.quantity_g), 0))::numeric, 2) AS protein_100g,
    ROUND((SUM(fi.carbs_g * ri.quantity_g) / NULLIF(SUM(ri.quantity_g), 0))::numeric, 2) AS carbs_100g,
    ROUND((SUM(fi.fats_g * ri.quantity_g) / NULLIF(SUM(ri.quantity_g), 0))::numeric, 2) AS fats_100g
FROM custom_meals cm
JOIN users u ON u.id = cm.user_id
JOIN recipe_ingredients ri ON ri.meal_id = cm.id
JOIN food_items fi ON fi.id = ri.food_id
WHERE u.email IN (SELECT email FROM demo_profiles)
GROUP BY u.email, cm.id, cm.recipe_name;

INSERT INTO daily_logs (user_id, log_date, total_calories_in, total_calories_burned)
SELECT
    u.id,
    d.log_date,
    0.00,
    0.00
FROM demo_days d
JOIN users u ON u.email = d.email
ON CONFLICT ON CONSTRAINT uq_daily_log DO NOTHING;

CREATE TEMP TABLE demo_weight_days ON COMMIT DROP AS
SELECT
    d.email,
    d.log_date,
    d.day_index
FROM demo_days d
WHERE EXTRACT(ISODOW FROM d.log_date)::int = 1
   OR d.day_index = 0
   OR d.log_date IN (DATE '2026-05-12', DATE '2026-05-18', DATE '2026-05-23', DATE '2026-05-27');

INSERT INTO weight_logs (user_id, log_date, weight_kg)
SELECT
    u.id,
    wd.log_date,
    ROUND((
        p.start_weight_kg
        + (p.end_weight_kg - p.start_weight_kg)
          * (wd.day_index::numeric / NULLIF((p.end_date - p.start_date)::numeric, 0))
        + CASE MOD(wd.day_index, 6)
            WHEN 0 THEN 0.00
            WHEN 1 THEN 0.04
            WHEN 2 THEN -0.03
            WHEN 3 THEN 0.02
            WHEN 4 THEN -0.05
            ELSE 0.01
          END
    )::numeric, 2)
FROM demo_weight_days wd
JOIN demo_profiles p ON p.email = wd.email
JOIN users u ON u.email = wd.email
ON CONFLICT ON CONSTRAINT uq_weight_log DO UPDATE
SET weight_kg = EXCLUDED.weight_kg;

CREATE TEMP TABLE demo_food_patterns (
    email TEXT,
    pattern_no INT,
    meal_sequence INT,
    food_external_id TEXT,
    custom_meal_name TEXT,
    base_quantity_g NUMERIC(6,2),
    meal_type TEXT,
    meal_time TIME
) ON COMMIT DROP;

INSERT INTO demo_food_patterns (
    email,
    pattern_no,
    meal_sequence,
    food_external_id,
    custom_meal_name,
    base_quantity_g,
    meal_type,
    meal_time
) VALUES
    ('demo.slabire@test.com', 0, 1, NULL, 'Bol proteic demo', 230.00, 'Mic dejun', TIME '08:10'),
    ('demo.slabire@test.com', 0, 2, '2646170', NULL, 160.00, 'Prânz', TIME '13:00'),
    ('demo.slabire@test.com', 0, 3, '2710789', NULL, 130.00, 'Prânz', TIME '13:00'),
    ('demo.slabire@test.com', 0, 4, '2709643', NULL, 180.00, 'Prânz', TIME '13:00'),
    ('demo.slabire@test.com', 0, 5, '173688', NULL, 130.00, 'Cină', TIME '19:30'),
    ('demo.slabire@test.com', 0, 6, '169303', NULL, 180.00, 'Cină', TIME '19:30'),
    ('demo.slabire@test.com', 0, 7, '168438', NULL, 90.00, 'Cină', TIME '19:30'),
    ('demo.slabire@test.com', 0, 8, '2709215', NULL, 180.00, 'Gustare', TIME '16:30'),
    ('demo.slabire@test.com', 0, 9, '2707533', NULL, 14.00, 'Gustare', TIME '16:30'),

    ('demo.slabire@test.com', 1, 1, '2705424', NULL, 210.00, 'Mic dejun', TIME '08:00'),
    ('demo.slabire@test.com', 1, 2, '2709275', NULL, 90.00, 'Mic dejun', TIME '08:00'),
    ('demo.slabire@test.com', 1, 3, '2707590', NULL, 12.00, 'Mic dejun', TIME '08:00'),
    ('demo.slabire@test.com', 1, 4, '171501', NULL, 155.00, 'Prânz', TIME '13:10'),
    ('demo.slabire@test.com', 1, 5, '2710788', NULL, 120.00, 'Prânz', TIME '13:10'),
    ('demo.slabire@test.com', 1, 6, '321360', NULL, 150.00, 'Prânz', TIME '13:10'),
    ('demo.slabire@test.com', 1, 7, '172189', NULL, 110.00, 'Cină', TIME '19:15'),
    ('demo.slabire@test.com', 1, 8, '168438', NULL, 120.00, 'Cină', TIME '19:15'),
    ('demo.slabire@test.com', 1, 9, '173420', NULL, 25.00, 'Cină', TIME '19:15'),

    ('demo.slabire@test.com', 2, 1, '172187', NULL, 160.00, 'Mic dejun', TIME '08:20'),
    ('demo.slabire@test.com', 2, 2, '2707598', NULL, 70.00, 'Mic dejun', TIME '08:20'),
    ('demo.slabire@test.com', 2, 3, '2646170', NULL, 150.00, 'Prânz', TIME '13:00'),
    ('demo.slabire@test.com', 2, 4, '2707616', NULL, 95.00, 'Prânz', TIME '13:00'),
    ('demo.slabire@test.com', 2, 5, '174289', NULL, 100.00, 'Prânz', TIME '13:00'),
    ('demo.slabire@test.com', 2, 6, '173688', NULL, 125.00, 'Cină', TIME '19:40'),
    ('demo.slabire@test.com', 2, 7, '2709643', NULL, 190.00, 'Cină', TIME '19:40'),
    ('demo.slabire@test.com', 2, 8, '2709283', NULL, 180.00, 'Gustare', TIME '16:20'),

    ('demo.slabire@test.com', 3, 1, '2705424', NULL, 180.00, 'Mic dejun', TIME '08:05'),
    ('demo.slabire@test.com', 3, 2, '2709224', NULL, 80.00, 'Mic dejun', TIME '08:05'),
    ('demo.slabire@test.com', 3, 3, '2707590', NULL, 10.00, 'Mic dejun', TIME '08:05'),
    ('demo.slabire@test.com', 3, 4, '2646170', NULL, 165.00, 'Prânz', TIME '13:20'),
    ('demo.slabire@test.com', 3, 5, '169303', NULL, 200.00, 'Prânz', TIME '13:20'),
    ('demo.slabire@test.com', 3, 6, '321360', NULL, 140.00, 'Prânz', TIME '13:20'),
    ('demo.slabire@test.com', 3, 7, '172189', NULL, 105.00, 'Cină', TIME '19:10'),
    ('demo.slabire@test.com', 3, 8, '168438', NULL, 110.00, 'Cină', TIME '19:10'),
    ('demo.slabire@test.com', 3, 9, '2709215', NULL, 170.00, 'Gustare', TIME '16:45'),

    ('demo.masa@test.com', 0, 1, '172187', NULL, 220.00, 'Mic dejun', TIME '08:00'),
    ('demo.masa@test.com', 0, 2, '2707598', NULL, 120.00, 'Mic dejun', TIME '08:00'),
    ('demo.masa@test.com', 0, 3, '2709224', NULL, 120.00, 'Mic dejun', TIME '08:00'),
    ('demo.masa@test.com', 0, 4, NULL, 'Pui cu orez demo', 420.00, 'Prânz', TIME '13:00'),
    ('demo.masa@test.com', 0, 5, '173688', NULL, 180.00, 'Cină', TIME '20:00'),
    ('demo.masa@test.com', 0, 6, '169303', NULL, 260.00, 'Cină', TIME '20:00'),
    ('demo.masa@test.com', 0, 7, '2707533', NULL, 30.00, 'Gustare', TIME '17:00'),

    ('demo.masa@test.com', 1, 1, '2705424', NULL, 260.00, 'Mic dejun', TIME '08:15'),
    ('demo.masa@test.com', 1, 2, '2709275', NULL, 120.00, 'Mic dejun', TIME '08:15'),
    ('demo.masa@test.com', 1, 3, '2707590', NULL, 18.00, 'Mic dejun', TIME '08:15'),
    ('demo.masa@test.com', 1, 4, '2646170', NULL, 240.00, 'Prânz', TIME '13:10'),
    ('demo.masa@test.com', 1, 5, '2710788', NULL, 310.00, 'Prânz', TIME '13:10'),
    ('demo.masa@test.com', 1, 6, '2709643', NULL, 140.00, 'Prânz', TIME '13:10'),
    ('demo.masa@test.com', 1, 7, '171501', NULL, 210.00, 'Cină', TIME '20:15'),
    ('demo.masa@test.com', 1, 8, '2707616', NULL, 130.00, 'Cină', TIME '20:15'),
    ('demo.masa@test.com', 1, 9, '174289', NULL, 120.00, 'Cină', TIME '20:15'),

    ('demo.masa@test.com', 2, 1, '172189', NULL, 150.00, 'Mic dejun', TIME '08:05'),
    ('demo.masa@test.com', 2, 2, '2707598', NULL, 130.00, 'Mic dejun', TIME '08:05'),
    ('demo.masa@test.com', 2, 3, '2646170', NULL, 230.00, 'Prânz', TIME '13:00'),
    ('demo.masa@test.com', 2, 4, '2710789', NULL, 320.00, 'Prânz', TIME '13:00'),
    ('demo.masa@test.com', 2, 5, '321360', NULL, 150.00, 'Prânz', TIME '13:00'),
    ('demo.masa@test.com', 2, 6, '173688', NULL, 190.00, 'Cină', TIME '20:00'),
    ('demo.masa@test.com', 2, 7, '169303', NULL, 280.00, 'Cină', TIME '20:00'),
    ('demo.masa@test.com', 2, 8, '2709255', NULL, 180.00, 'Gustare', TIME '17:30'),

    ('demo.masa@test.com', 3, 1, '2705424', NULL, 250.00, 'Mic dejun', TIME '08:10'),
    ('demo.masa@test.com', 3, 2, '2709224', NULL, 140.00, 'Mic dejun', TIME '08:10'),
    ('demo.masa@test.com', 3, 3, '2707590', NULL, 16.00, 'Mic dejun', TIME '08:10'),
    ('demo.masa@test.com', 3, 4, NULL, 'Pui cu orez demo', 460.00, 'Prânz', TIME '13:20'),
    ('demo.masa@test.com', 3, 5, '171501', NULL, 220.00, 'Cină', TIME '20:10'),
    ('demo.masa@test.com', 3, 6, '2707616', NULL, 120.00, 'Cină', TIME '20:10'),
    ('demo.masa@test.com', 3, 7, '174289', NULL, 110.00, 'Cină', TIME '20:10'),
    ('demo.masa@test.com', 3, 8, '2707533', NULL, 35.00, 'Gustare', TIME '17:00'),

    ('demo.mentinere@test.com', 0, 1, NULL, 'Omleta verde demo', 210.00, 'Mic dejun', TIME '08:20'),
    ('demo.mentinere@test.com', 0, 2, '2707598', NULL, 70.00, 'Mic dejun', TIME '08:20'),
    ('demo.mentinere@test.com', 0, 3, '2646170', NULL, 155.00, 'Prânz', TIME '13:00'),
    ('demo.mentinere@test.com', 0, 4, '2710789', NULL, 160.00, 'Prânz', TIME '13:00'),
    ('demo.mentinere@test.com', 0, 5, '321360', NULL, 140.00, 'Prânz', TIME '13:00'),
    ('demo.mentinere@test.com', 0, 6, '173688', NULL, 130.00, 'Cină', TIME '19:30'),
    ('demo.mentinere@test.com', 0, 7, '2709643', NULL, 160.00, 'Cină', TIME '19:30'),
    ('demo.mentinere@test.com', 0, 8, '2709215', NULL, 160.00, 'Gustare', TIME '16:30'),

    ('demo.mentinere@test.com', 1, 1, '2705424', NULL, 220.00, 'Mic dejun', TIME '08:00'),
    ('demo.mentinere@test.com', 1, 2, '2709275', NULL, 100.00, 'Mic dejun', TIME '08:00'),
    ('demo.mentinere@test.com', 1, 3, '2707590', NULL, 12.00, 'Mic dejun', TIME '08:00'),
    ('demo.mentinere@test.com', 1, 4, '171501', NULL, 160.00, 'Prânz', TIME '13:15'),
    ('demo.mentinere@test.com', 1, 5, '2707616', NULL, 90.00, 'Prânz', TIME '13:15'),
    ('demo.mentinere@test.com', 1, 6, '174289', NULL, 90.00, 'Prânz', TIME '13:15'),
    ('demo.mentinere@test.com', 1, 7, '172189', NULL, 110.00, 'Cină', TIME '19:15'),
    ('demo.mentinere@test.com', 1, 8, '168438', NULL, 110.00, 'Cină', TIME '19:15'),
    ('demo.mentinere@test.com', 1, 9, '173420', NULL, 30.00, 'Cină', TIME '19:15'),

    ('demo.mentinere@test.com', 2, 1, '172187', NULL, 170.00, 'Mic dejun', TIME '08:10'),
    ('demo.mentinere@test.com', 2, 2, '2707598', NULL, 80.00, 'Mic dejun', TIME '08:10'),
    ('demo.mentinere@test.com', 2, 3, '2646170', NULL, 150.00, 'Prânz', TIME '13:00'),
    ('demo.mentinere@test.com', 2, 4, '169303', NULL, 200.00, 'Prânz', TIME '13:00'),
    ('demo.mentinere@test.com', 2, 5, '2709643', NULL, 150.00, 'Prânz', TIME '13:00'),
    ('demo.mentinere@test.com', 2, 6, '173688', NULL, 125.00, 'Cină', TIME '19:45'),
    ('demo.mentinere@test.com', 2, 7, '321360', NULL, 160.00, 'Cină', TIME '19:45'),
    ('demo.mentinere@test.com', 2, 8, '2709283', NULL, 160.00, 'Gustare', TIME '16:15'),

    ('demo.mentinere@test.com', 3, 1, '2705424', NULL, 200.00, 'Mic dejun', TIME '08:05'),
    ('demo.mentinere@test.com', 3, 2, '2709224', NULL, 90.00, 'Mic dejun', TIME '08:05'),
    ('demo.mentinere@test.com', 3, 3, '2707590', NULL, 11.00, 'Mic dejun', TIME '08:05'),
    ('demo.mentinere@test.com', 3, 4, '171501', NULL, 165.00, 'Prânz', TIME '13:20'),
    ('demo.mentinere@test.com', 3, 5, '2710788', NULL, 160.00, 'Prânz', TIME '13:20'),
    ('demo.mentinere@test.com', 3, 6, '2709643', NULL, 140.00, 'Prânz', TIME '13:20'),
    ('demo.mentinere@test.com', 3, 7, NULL, 'Omleta verde demo', 190.00, 'Cină', TIME '19:10'),
    ('demo.mentinere@test.com', 3, 8, '2709215', NULL, 150.00, 'Gustare', TIME '16:40'),

    ('demo.activ@test.com', 0, 1, NULL, 'Curcan demo', 430.00, 'Prânz', TIME '13:00'),
    ('demo.activ@test.com', 0, 2, '2705424', NULL, 260.00, 'Mic dejun', TIME '07:45'),
    ('demo.activ@test.com', 0, 3, '2709224', NULL, 130.00, 'Mic dejun', TIME '07:45'),
    ('demo.activ@test.com', 0, 4, '173688', NULL, 190.00, 'Cină', TIME '20:00'),
    ('demo.activ@test.com', 0, 5, '169303', NULL, 280.00, 'Cină', TIME '20:00'),
    ('demo.activ@test.com', 0, 6, '2707533', NULL, 30.00, 'Gustare', TIME '17:00'),

    ('demo.activ@test.com', 1, 1, '172187', NULL, 220.00, 'Mic dejun', TIME '07:50'),
    ('demo.activ@test.com', 1, 2, '2707598', NULL, 120.00, 'Mic dejun', TIME '07:50'),
    ('demo.activ@test.com', 1, 3, '2646170', NULL, 230.00, 'Prânz', TIME '13:10'),
    ('demo.activ@test.com', 1, 4, '2710789', NULL, 300.00, 'Prânz', TIME '13:10'),
    ('demo.activ@test.com', 1, 5, '2709643', NULL, 160.00, 'Prânz', TIME '13:10'),
    ('demo.activ@test.com', 1, 6, '171501', NULL, 220.00, 'Cină', TIME '20:15'),
    ('demo.activ@test.com', 1, 7, '2707616', NULL, 130.00, 'Cină', TIME '20:15'),
    ('demo.activ@test.com', 1, 8, '174289', NULL, 120.00, 'Cină', TIME '20:15'),

    ('demo.activ@test.com', 2, 1, '2705424', NULL, 250.00, 'Mic dejun', TIME '08:00'),
    ('demo.activ@test.com', 2, 2, '2709275', NULL, 120.00, 'Mic dejun', TIME '08:00'),
    ('demo.activ@test.com', 2, 3, '2707590', NULL, 18.00, 'Mic dejun', TIME '08:00'),
    ('demo.activ@test.com', 2, 4, NULL, 'Curcan demo', 460.00, 'Prânz', TIME '13:00'),
    ('demo.activ@test.com', 2, 5, '2646170', NULL, 220.00, 'Cină', TIME '20:00'),
    ('demo.activ@test.com', 2, 6, '169303', NULL, 270.00, 'Cină', TIME '20:00'),
    ('demo.activ@test.com', 2, 7, '2709255', NULL, 180.00, 'Gustare', TIME '17:30'),

    ('demo.activ@test.com', 3, 1, '172189', NULL, 150.00, 'Mic dejun', TIME '08:05'),
    ('demo.activ@test.com', 3, 2, '2707598', NULL, 130.00, 'Mic dejun', TIME '08:05'),
    ('demo.activ@test.com', 3, 3, '171501', NULL, 220.00, 'Prânz', TIME '13:15'),
    ('demo.activ@test.com', 3, 4, '2710788', NULL, 280.00, 'Prânz', TIME '13:15'),
    ('demo.activ@test.com', 3, 5, '321360', NULL, 150.00, 'Prânz', TIME '13:15'),
    ('demo.activ@test.com', 3, 6, '173688', NULL, 180.00, 'Cină', TIME '20:10'),
    ('demo.activ@test.com', 3, 7, '2709643', NULL, 180.00, 'Cină', TIME '20:10'),
    ('demo.activ@test.com', 3, 8, '2707533', NULL, 32.00, 'Gustare', TIME '17:00'),

    ('demo.rar@test.com', 0, 1, '172187', NULL, 160.00, 'Mic dejun', TIME '09:00'),
    ('demo.rar@test.com', 0, 2, '2707598', NULL, 70.00, 'Mic dejun', TIME '09:00'),
    ('demo.rar@test.com', 0, 3, '174289', NULL, 120.00, 'Prânz', TIME '14:00'),
    ('demo.rar@test.com', 0, 4, '2707616', NULL, 90.00, 'Prânz', TIME '14:00'),
    ('demo.rar@test.com', 0, 5, '2646170', NULL, 150.00, 'Cină', TIME '20:00'),
    ('demo.rar@test.com', 0, 6, '2709643', NULL, 200.00, 'Cină', TIME '20:00'),

    ('demo.rar@test.com', 1, 1, '2705424', NULL, 210.00, 'Mic dejun', TIME '09:15'),
    ('demo.rar@test.com', 1, 2, '2709224', NULL, 100.00, 'Mic dejun', TIME '09:15'),
    ('demo.rar@test.com', 1, 3, '171501', NULL, 160.00, 'Prânz', TIME '14:00'),
    ('demo.rar@test.com', 1, 4, '2710789', NULL, 170.00, 'Prânz', TIME '14:00'),
    ('demo.rar@test.com', 1, 5, '321360', NULL, 120.00, 'Prânz', TIME '14:00'),
    ('demo.rar@test.com', 1, 6, '173688', NULL, 135.00, 'Cină', TIME '20:15'),
    ('demo.rar@test.com', 1, 7, '168438', NULL, 100.00, 'Cină', TIME '20:15'),

    ('demo.rar@test.com', 2, 1, '172189', NULL, 120.00, 'Mic dejun', TIME '09:05'),
    ('demo.rar@test.com', 2, 2, '2707598', NULL, 80.00, 'Mic dejun', TIME '09:05'),
    ('demo.rar@test.com', 2, 3, '2646170', NULL, 160.00, 'Prânz', TIME '14:10'),
    ('demo.rar@test.com', 2, 4, '169303', NULL, 190.00, 'Prânz', TIME '14:10'),
    ('demo.rar@test.com', 2, 5, '2709643', NULL, 160.00, 'Prânz', TIME '14:10'),
    ('demo.rar@test.com', 2, 6, '2709215', NULL, 160.00, 'Gustare', TIME '17:00');

INSERT INTO food_logs (
    log_id,
    food_id,
    custom_meal_id,
    quantity_g,
    meal_type,
    meal_time,
    snapshot_name,
    snapshot_calories_100g,
    snapshot_protein_100g,
    snapshot_carbs_100g,
    snapshot_fats_100g
)
SELECT
    dl.id,
    fi.id,
    ms.custom_meal_id,
    ROUND(LEAST(
        5000.00,
        GREATEST(
            1.00,
            fp.base_quantity_g
            * p.food_scale
            * (1.0 + ((MOD(d.day_index + fp.meal_sequence, 5) - 2) * 0.025))
        )
    )::numeric, 2),
    fp.meal_type,
    fp.meal_time,
    ms.recipe_name,
    ms.calories_100g,
    ms.protein_100g,
    ms.carbs_100g,
    ms.fats_100g
FROM demo_days d
JOIN demo_profiles p ON p.email = d.email
JOIN users u ON u.email = d.email
JOIN daily_logs dl ON dl.user_id = u.id AND dl.log_date = d.log_date
JOIN demo_food_patterns fp
  ON fp.email = d.email
 AND fp.pattern_no = MOD(d.day_index, p.food_pattern_count)
LEFT JOIN food_items fi
  ON fi.source = 'USDA'
 AND fi.external_id = fp.food_external_id
LEFT JOIN demo_meal_snapshots ms
  ON ms.email = d.email
 AND ms.recipe_name = fp.custom_meal_name
WHERE (fp.food_external_id IS NOT NULL OR fp.custom_meal_name IS NOT NULL)
  AND (d.email <> 'demo.rar@test.com' OR MOD(d.day_index, 3) <> 1 OR d.log_date >= DATE '2026-05-20');

CREATE TEMP TABLE demo_activity_schedule (
    email TEXT,
    iso_weekday INT,
    activity_sequence INT,
    activity_source TEXT,
    activity_external_id TEXT,
    base_duration_min NUMERIC(6,2),
    sets INT,
    reps INT,
    base_manual_calories NUMERIC(8,2)
) ON COMMIT DROP;

INSERT INTO demo_activity_schedule (
    email,
    iso_weekday,
    activity_sequence,
    activity_source,
    activity_external_id,
    base_duration_min,
    sets,
    reps,
    base_manual_calories
) VALUES
    ('demo.slabire@test.com', 1, 1, 'MacroSense', 'MS-MAP-STR-004', 34.00, 4, 12, NULL),
    ('demo.slabire@test.com', 3, 1, 'Compendium', '17200', 42.00, NULL, NULL, NULL),
    ('demo.slabire@test.com', 5, 1, 'Compendium', '02035', 35.00, 4, 12, NULL),
    ('demo.slabire@test.com', 7, 1, 'Compendium', '17190', 50.00, NULL, NULL, NULL),

    ('demo.masa@test.com', 1, 1, 'MacroSense', 'MS-MAP-STR-001', 55.00, 4, 10, NULL),
    ('demo.masa@test.com', 3, 1, 'MacroSense', 'MS-MAP-STR-018', 58.00, 4, 8, NULL),
    ('demo.masa@test.com', 5, 1, 'MacroSense', 'MS-MAP-STR-007', 52.00, 4, 10, NULL),
    ('demo.masa@test.com', 6, 1, 'Compendium', '01020', 35.00, NULL, NULL, NULL),

    ('demo.mentinere@test.com', 2, 1, 'Compendium', '02150', 35.00, NULL, NULL, NULL),
    ('demo.mentinere@test.com', 4, 1, 'Compendium', '17200', 36.00, NULL, NULL, NULL),
    ('demo.mentinere@test.com', 6, 1, 'Compendium', '02054', 32.00, 3, 12, NULL),

    ('demo.activ@test.com', 1, 1, 'Compendium', '02040', 45.00, 5, 10, NULL),
    ('demo.activ@test.com', 2, 1, 'Compendium', '12030', 35.00, NULL, NULL, NULL),
    ('demo.activ@test.com', 4, 1, 'MacroSense', 'MS-MAP-STR-020', 50.00, 4, 10, NULL),
    ('demo.activ@test.com', 5, 1, 'Compendium', '01030', 45.00, NULL, NULL, 430.00),
    ('demo.activ@test.com', 7, 1, 'Compendium', '18240', 40.00, NULL, NULL, NULL),

    ('demo.rar@test.com', 1, 1, 'Compendium', '17200', 30.00, NULL, NULL, NULL),
    ('demo.rar@test.com', 4, 1, 'Compendium', '17190', 35.00, NULL, NULL, NULL);

INSERT INTO activity_logs (
    log_id,
    activity_id,
    duration_min,
    sets,
    reps,
    manual_calories_burned
)
SELECT
    dl.id,
    a.id,
    ROUND((
        s.base_duration_min
        * (1.0 + ((MOD(d.day_index + s.activity_sequence, 5) - 2) * 0.03))
    )::numeric, 2),
    s.sets,
    s.reps,
    CASE
        WHEN s.base_manual_calories IS NULL THEN NULL
        ELSE ROUND((
            s.base_manual_calories
            * (1.0 + ((MOD(d.day_index + s.activity_sequence, 4) - 1) * 0.03))
        )::numeric, 2)
    END
FROM demo_days d
JOIN users u ON u.email = d.email
JOIN daily_logs dl ON dl.user_id = u.id AND dl.log_date = d.log_date
JOIN demo_activity_schedule s
  ON s.email = d.email
 AND s.iso_weekday = EXTRACT(ISODOW FROM d.log_date)::int
JOIN activities a
  ON a.source = s.activity_source
 AND a.external_id = s.activity_external_id
WHERE (d.email <> 'demo.rar@test.com' OR MOD(d.day_index, 6) IN (0, 3));

-- Final total recalculation keeps daily_logs aligned with food and activity rows.
WITH demo_daily_logs AS (
    SELECT dl.id AS log_id
    FROM daily_logs dl
    JOIN users u ON u.id = dl.user_id
    WHERE u.email IN (SELECT email FROM demo_profiles)
),
food_totals AS (
    SELECT
        ddl.log_id,
        ROUND(COALESCE(SUM(CASE
            WHEN fl.food_id IS NOT NULL THEN fi.calories_100g * fl.quantity_g / 100.0
            WHEN fl.custom_meal_id IS NOT NULL THEN fl.snapshot_calories_100g * fl.quantity_g / 100.0
            ELSE 0
        END), 0), 2) AS total_calories_in
    FROM demo_daily_logs ddl
    LEFT JOIN food_logs fl ON fl.log_id = ddl.log_id
    LEFT JOIN food_items fi ON fi.id = fl.food_id
    GROUP BY ddl.log_id
)
UPDATE daily_logs dl
SET total_calories_in = food_totals.total_calories_in
FROM food_totals
WHERE dl.id = food_totals.log_id;

WITH demo_daily_logs AS (
    SELECT
        dl.id AS log_id,
        dl.user_id,
        dl.log_date,
        COALESCE(past_weight.weight_kg, future_weight.weight_kg, 70.0) AS reference_weight_kg
    FROM daily_logs dl
    JOIN users u ON u.id = dl.user_id
    LEFT JOIN LATERAL (
        SELECT wl.weight_kg
        FROM weight_logs wl
        WHERE wl.user_id = dl.user_id
          AND wl.log_date <= dl.log_date
        ORDER BY wl.log_date DESC
        LIMIT 1
    ) past_weight ON TRUE
    LEFT JOIN LATERAL (
        SELECT wl.weight_kg
        FROM weight_logs wl
        WHERE wl.user_id = dl.user_id
          AND wl.log_date > dl.log_date
        ORDER BY wl.log_date ASC
        LIMIT 1
    ) future_weight ON TRUE
    WHERE u.email IN (SELECT email FROM demo_profiles)
),
activity_totals AS (
    SELECT
        ddl.log_id,
        ROUND(COALESCE(SUM(CASE
            WHEN al.manual_calories_burned IS NOT NULL THEN
                al.manual_calories_burned
            WHEN a.category = 'Forță' AND al.sets IS NOT NULL AND al.reps IS NOT NULL THEN
                (a.met_multiplier * ddl.reference_weight_kg * (LEAST(al.duration_min, (al.sets * al.reps * 3.0) / 60.0) / 60.0))
                + (1.5 * ddl.reference_weight_kg * (GREATEST(0, al.duration_min - ((al.sets * al.reps * 3.0) / 60.0)) / 60.0))
            ELSE
                a.met_multiplier * ddl.reference_weight_kg * (al.duration_min / 60.0)
        END), 0), 2) AS total_calories_burned
    FROM demo_daily_logs ddl
    LEFT JOIN activity_logs al ON al.log_id = ddl.log_id
    LEFT JOIN activities a ON a.id = al.activity_id
    GROUP BY ddl.log_id
)
UPDATE daily_logs dl
SET total_calories_burned = activity_totals.total_calories_burned
FROM activity_totals
WHERE dl.id = activity_totals.log_id;

COMMIT;
