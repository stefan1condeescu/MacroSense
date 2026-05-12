-- ==========================================
-- 1. INDEPENDENT TABLES (No foreign keys)
-- ==========================================

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    registration_date DATE DEFAULT CURRENT_DATE,
    full_name VARCHAR(100),
    height_cm DECIMAL(5,2),
    age INT,
    gender CHAR(1),
    goal VARCHAR(50),
    CONSTRAINT chk_user_email_trimmed CHECK (email = BTRIM(email)),
    CONSTRAINT chk_user_email_no_html CHECK (POSITION('<' IN email) = 0 AND POSITION('>' IN email) = 0),
    CONSTRAINT chk_user_full_name_no_html CHECK (full_name IS NULL OR (POSITION('<' IN full_name) = 0 AND POSITION('>' IN full_name) = 0)),
    CONSTRAINT chk_user_full_name_chars CHECK (full_name IS NULL OR full_name ~ '^[[:alpha:][:space:]''-]+$'),
    CONSTRAINT chk_user_full_name_has_letter CHECK (full_name IS NULL OR full_name ~ '[[:alpha:]]'),
    CONSTRAINT chk_user_height CHECK (height_cm IS NULL OR height_cm BETWEEN 100 AND 250),
    CONSTRAINT chk_user_age CHECK (age IS NULL OR age BETWEEN 10 AND 120),
    CONSTRAINT chk_user_gender CHECK (gender IS NULL OR gender IN ('M', 'F')),
    CONSTRAINT chk_user_goal CHECK (goal IS NULL OR goal IN ('Slabire', 'Mentinere', 'Crestere'))
);

CREATE TABLE admins (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    registration_date DATE DEFAULT CURRENT_DATE,
    access_level INT,
    CONSTRAINT chk_admin_email_trimmed CHECK (email = BTRIM(email)),
    CONSTRAINT chk_admin_email_no_html CHECK (POSITION('<' IN email) = 0 AND POSITION('>' IN email) = 0),
    CONSTRAINT chk_admin_access_level CHECK (access_level IS NULL OR access_level >= 1)
);

CREATE TABLE food_items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    calories_100g DECIMAL(5,2) NOT NULL,
    protein_g DECIMAL(5,2),
    carbs_g DECIMAL(5,2),
    fats_g DECIMAL(5,2),
    category VARCHAR(50) NOT NULL,
    source VARCHAR(50),
    source_type VARCHAR(50),
    external_id VARCHAR(100),
    source_url TEXT,
    CONSTRAINT uq_food_source_external UNIQUE (source, external_id),
    CONSTRAINT chk_food_name_not_empty CHECK (BTRIM(name) <> ''),
    CONSTRAINT chk_food_name_no_html CHECK (POSITION('<' IN name) = 0 AND POSITION('>' IN name) = 0),
    CONSTRAINT chk_food_name_has_letter CHECK (name ~ '[[:alpha:]]'),
    CONSTRAINT chk_food_nutrition_non_negative CHECK (
        calories_100g >= 0
        AND COALESCE(protein_g, 0) >= 0
        AND COALESCE(carbs_g, 0) >= 0
        AND COALESCE(fats_g, 0) >= 0
    ),
    CONSTRAINT chk_food_calories_positive CHECK (calories_100g > 0),
    CONSTRAINT chk_food_has_macro CHECK (
        COALESCE(protein_g, 0) > 0
        OR COALESCE(carbs_g, 0) > 0
        OR COALESCE(fats_g, 0) > 0
    ),
    CONSTRAINT chk_food_category_not_empty CHECK (BTRIM(category) <> '')
);

CREATE TABLE activities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    met_multiplier DECIMAL(5,2) NOT NULL,
    category VARCHAR(50),
    source VARCHAR(50),
    source_type VARCHAR(100),
    external_id VARCHAR(100),
    source_url TEXT,
    met_source_code VARCHAR(100),
    met_source_description TEXT,
    met_estimation_method VARCHAR(50) NOT NULL DEFAULT 'manual_admin',
    CONSTRAINT uq_activity_source_external UNIQUE (source, external_id),
    CONSTRAINT chk_activity_name_not_empty CHECK (BTRIM(name) <> ''),
    CONSTRAINT chk_activity_name_no_html CHECK (POSITION('<' IN name) = 0 AND POSITION('>' IN name) = 0),
    CONSTRAINT chk_activity_name_has_letter CHECK (name ~ '[[:alpha:]]'),
    CONSTRAINT chk_activity_met_supported CHECK (met_multiplier >= 0.9),
    CONSTRAINT chk_activity_category_not_empty CHECK (category IS NOT NULL AND BTRIM(category) <> ''),
    CONSTRAINT chk_activity_met_estimation_method CHECK (
        met_estimation_method IN ('official_compendium', 'compendium_mapping', 'manual_admin')
    )
);

-- ==========================================
-- 2. LEVEL 1 DEPENDENT TABLES
-- ==========================================

CREATE TABLE weight_logs (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    weight_kg DECIMAL(5,2) NOT NULL,
    CONSTRAINT chk_weight_range CHECK (weight_kg BETWEEN 30 AND 300),
    CONSTRAINT uq_weight_log UNIQUE (user_id, log_date)
);

CREATE TABLE daily_logs (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    total_calories_in DECIMAL(8,2) DEFAULT 0,
    total_calories_burned DECIMAL(8,2) DEFAULT 0,
    CONSTRAINT chk_daily_totals_non_negative CHECK (
        total_calories_in >= 0 AND total_calories_burned >= 0
    ),
    CONSTRAINT uq_daily_log UNIQUE (user_id, log_date)
);

CREATE OR REPLACE FUNCTION prevent_future_log_date()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.log_date > CURRENT_DATE THEN
        RAISE EXCEPTION 'Log date cannot be in the future.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_weight_logs_no_future_date
BEFORE INSERT OR UPDATE OF log_date ON weight_logs
FOR EACH ROW
EXECUTE FUNCTION prevent_future_log_date();

CREATE TRIGGER trg_daily_logs_no_future_date
BEFORE INSERT OR UPDATE OF log_date ON daily_logs
FOR EACH ROW
EXECUTE FUNCTION prevent_future_log_date();

CREATE TABLE custom_meals (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipe_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Salvată',
    CONSTRAINT chk_custom_meal_name_not_empty CHECK (BTRIM(recipe_name) <> ''),
    CONSTRAINT chk_custom_meal_name_no_html CHECK (POSITION('<' IN recipe_name) = 0 AND POSITION('>' IN recipe_name) = 0),
    CONSTRAINT chk_custom_meal_name_starts_letter CHECK (recipe_name ~ '^[[:alpha:]]'),
    CONSTRAINT chk_custom_meal_status CHECK (status IN ('Salvată', 'Arhivată'))
);

-- ==========================================
-- 3. LEVEL 2 DEPENDENT TABLES (Link tables)
-- ==========================================

CREATE TABLE recipe_ingredients (
    id SERIAL PRIMARY KEY,
    meal_id INT NOT NULL REFERENCES custom_meals(id) ON DELETE CASCADE,
    food_id INT NOT NULL REFERENCES food_items(id) ON DELETE CASCADE,
    quantity_g DECIMAL(6,2) NOT NULL,
    CONSTRAINT chk_recipe_ingredient_quantity_range CHECK (quantity_g BETWEEN 1 AND 5000)
);

CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    log_id INT NOT NULL REFERENCES daily_logs(id) ON DELETE CASCADE,
    activity_id INT NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    duration_min DECIMAL(6,2) NOT NULL,
    sets INT,
    reps INT,
    manual_calories_burned DECIMAL(8,2),
    CONSTRAINT chk_activity_log_duration_range CHECK (duration_min BETWEEN 0.1 AND 600),
    CONSTRAINT chk_activity_log_sets_reps CHECK (
        (sets IS NULL AND reps IS NULL)
        OR (
            sets IS NOT NULL
            AND reps IS NOT NULL
            AND sets BETWEEN 1 AND 50
            AND reps BETWEEN 1 AND 200
        )
    ),
    CONSTRAINT chk_activity_log_manual_calories CHECK (
        manual_calories_burned IS NULL OR manual_calories_burned BETWEEN 1 AND 5000
    )
);

CREATE TABLE food_logs (
    id SERIAL PRIMARY KEY,
    log_id INT NOT NULL REFERENCES daily_logs(id) ON DELETE CASCADE,
    food_id INT REFERENCES food_items(id) ON DELETE CASCADE,
    custom_meal_id INT REFERENCES custom_meals(id) ON DELETE CASCADE,
    quantity_g DECIMAL(6,2) NOT NULL, -- Integration of the previously discussed fix
    meal_type VARCHAR(50) NOT NULL,
    meal_time TIME NOT NULL,
    snapshot_name VARCHAR(100),
    snapshot_calories_100g DECIMAL(8,2),
    snapshot_protein_100g DECIMAL(8,2),
    snapshot_carbs_100g DECIMAL(8,2),
    snapshot_fats_100g DECIMAL(8,2),
    CONSTRAINT chk_xor_food_meal CHECK (
        (food_id IS NOT NULL AND custom_meal_id IS NULL) OR 
        (food_id IS NULL AND custom_meal_id IS NOT NULL)
    ),
    CONSTRAINT chk_food_log_quantity_range CHECK (quantity_g BETWEEN 1 AND 5000),
    CONSTRAINT chk_food_log_meal_type CHECK (
        meal_type IN ('Mic dejun', 'Prânz', 'Cină', 'Gustare')
    ),
    CONSTRAINT chk_food_log_snapshot_complete CHECK (
        (
            snapshot_name IS NULL AND
            snapshot_calories_100g IS NULL AND
            snapshot_protein_100g IS NULL AND
            snapshot_carbs_100g IS NULL AND
            snapshot_fats_100g IS NULL
        ) OR (
            snapshot_name IS NOT NULL AND
            snapshot_calories_100g IS NOT NULL AND
            snapshot_protein_100g IS NOT NULL AND
            snapshot_carbs_100g IS NOT NULL AND
            snapshot_fats_100g IS NOT NULL
        )
    ),
    CONSTRAINT chk_food_log_catalog_snapshot_null CHECK (
        food_id IS NULL OR (
            snapshot_name IS NULL AND
            snapshot_calories_100g IS NULL AND
            snapshot_protein_100g IS NULL AND
            snapshot_carbs_100g IS NULL AND
            snapshot_fats_100g IS NULL
        )
    ),
    CONSTRAINT chk_food_log_custom_meal_snapshot_required CHECK (
        custom_meal_id IS NULL OR (
            snapshot_name IS NOT NULL AND
            snapshot_calories_100g IS NOT NULL AND
            snapshot_protein_100g IS NOT NULL AND
            snapshot_carbs_100g IS NOT NULL AND
            snapshot_fats_100g IS NOT NULL
        )
    ),
    CONSTRAINT chk_food_log_snapshot_name_valid CHECK (
        snapshot_name IS NULL OR (
            BTRIM(snapshot_name) <> '' AND
            POSITION('<' IN snapshot_name) = 0 AND
            POSITION('>' IN snapshot_name) = 0
        )
    ),
    CONSTRAINT chk_food_log_snapshot_nutrition CHECK (
        (snapshot_calories_100g IS NULL OR snapshot_calories_100g > 0) AND
        (snapshot_protein_100g IS NULL OR snapshot_protein_100g >= 0) AND
        (snapshot_carbs_100g IS NULL OR snapshot_carbs_100g >= 0) AND
        (snapshot_fats_100g IS NULL OR snapshot_fats_100g >= 0)
    )
);

-- Insert default Admin account
INSERT INTO admins (email, password_hash, access_level) 
VALUES (
    'admin@test.com', 
    encode(sha256('parola123'::bytea), 'hex'), 
    1
);
