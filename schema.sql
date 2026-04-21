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
    goal VARCHAR(50)
);

CREATE TABLE admins (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    registration_date DATE DEFAULT CURRENT_DATE,
    access_level INT
);

CREATE TABLE food_items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    calories_100g DECIMAL(5,2) NOT NULL,
    protein_g DECIMAL(5,2),
    carbs_g DECIMAL(5,2),
    fats_g DECIMAL(5,2),
    category VARCHAR(50)
);

CREATE TABLE activities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    met_multiplier DECIMAL(5,2) NOT NULL,
    category VARCHAR(50)
);

-- ==========================================
-- 2. LEVEL 1 DEPENDENT TABLES
-- ==========================================

CREATE TABLE weight_logs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    weight_kg DECIMAL(5,2),
    CONSTRAINT uq_weight_log UNIQUE (user_id, log_date)
);

CREATE TABLE daily_logs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    total_calories_in DECIMAL(8,2) DEFAULT 0,
    total_calories_burned DECIMAL(8,2) DEFAULT 0,
    CONSTRAINT uq_daily_log UNIQUE (user_id, log_date)
);

CREATE TABLE custom_meals (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    recipe_name VARCHAR(100),
    status VARCHAR(50)
);

-- ==========================================
-- 3. LEVEL 2 DEPENDENT TABLES (Link tables)
-- ==========================================

CREATE TABLE recipe_ingredients (
    id SERIAL PRIMARY KEY,
    meal_id INT REFERENCES custom_meals(id) ON DELETE CASCADE,
    food_id INT REFERENCES food_items(id) ON DELETE CASCADE,
    quantity_g DECIMAL(6,2) NOT NULL
);

CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    log_id INT REFERENCES daily_logs(id) ON DELETE CASCADE,
    activity_id INT REFERENCES activities(id) ON DELETE CASCADE,
    duration_min INT NOT NULL, -- Fix: now NOT NULL to support MET formula
    sets INT,
    reps INT
);

CREATE TABLE food_logs (
    id SERIAL PRIMARY KEY,
    log_id INT REFERENCES daily_logs(id) ON DELETE CASCADE,
    food_id INT REFERENCES food_items(id) ON DELETE CASCADE,
    custom_meal_id INT REFERENCES custom_meals(id) ON DELETE CASCADE,
    quantity_g DECIMAL(6,2) NOT NULL, -- Integration of the previously discussed fix
    meal_type VARCHAR(50),
    meal_time TIME,
    CONSTRAINT chk_xor_food_meal CHECK (
        (food_id IS NOT NULL AND custom_meal_id IS NULL) OR 
        (food_id IS NULL AND custom_meal_id IS NOT NULL)
    )
);

-- Insert default Admin account
INSERT INTO admins (email, password_hash, access_level) 
VALUES (
    'admin@test.com', 
    encode(sha256('parola123'::bytea), 'hex'), 
    1
);