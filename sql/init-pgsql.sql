-- USERS TABLE
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    address_line1 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    profile_picture_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ARTISANS TABLE (needed for insert to work)
CREATE TABLE IF NOT EXISTS artisans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    zip_code VARCHAR(20),
    product_name VARCHAR(100),
    subscription_price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, zip_code, product_name)
);

-- INSERT sample artisans
INSERT INTO artisans (name, zip_code, product_name, subscription_price)
VALUES
  ('John Doe', '12345', 'Cordless Drill', 5.00),
  ('Jane Smith', '23456', 'Circular Saw', 8.50),
  ('Mike Johnson', '34567', 'Pressure Washer', 12.00)
ON CONFLICT (name, zip_code, product_name) DO NOTHING;

-- TOOLS TABLE
CREATE TABLE tools (
    id SERIAL PRIMARY KEY,
    owner_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    daily_price DECIMAL(10, 2),
    deposit_amount DECIMAL(10, 2),
    is_available BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

-- TOOL IMAGES TABLE
CREATE TABLE tool_images (
    id SERIAL PRIMARY KEY,
    tool_id INT NOT NULL,
    image_url VARCHAR(255),
    is_primary BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (tool_id) REFERENCES tools(id)
);

-- TOOL AVAILABILITY TABLE
CREATE TABLE tool_availability (
    id SERIAL PRIMARY KEY,
    tool_id INT NOT NULL,
    date DATE NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (tool_id) REFERENCES tools(id)
);

-- RENTAL REQUEST STATUS ENUM TYPE
CREATE TYPE rental_status AS ENUM ('pending', 'approved', 'rejected', 'completed');

-- RENTAL REQUESTS TABLE
CREATE TABLE rental_requests (
    id SERIAL PRIMARY KEY,
    tool_id INT NOT NULL,
    renter_id INT NOT NULL,
    start_date DATE,
    end_date DATE,
    status rental_status DEFAULT 'pending',
    requested_at TIMESTAMP,
    responded_at TIMESTAMP,
    FOREIGN KEY (tool_id) REFERENCES tools(id),
    FOREIGN KEY (renter_id) REFERENCES users(id)
);

-- PAYMENTS TABLE
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    rental_id INT NOT NULL,
    stripe_payment_id VARCHAR(255),
    amount DECIMAL(10, 2),
    payment_method VARCHAR(255),
    status VARCHAR(50),
    created_at TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (rental_id) REFERENCES rental_requests(id)
);

-- REVIEWS TABLE
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    rental_id INT NOT NULL,
    reviewer_id INT NOT NULL,
    reviewee_id INT NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (rental_id) REFERENCES rental_requests(id),
    FOREIGN KEY (reviewer_id) REFERENCES users(id),
    FOREIGN KEY (reviewee_id) REFERENCES users(id)
);

-- NOTIFICATIONS TABLE
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    related_entity_type VARCHAR(50),
    related_entity_id INT,
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
