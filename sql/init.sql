-- USERS TABLE
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
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

-- TOOLS TABLE
CREATE TABLE tools (
    id INT AUTO_INCREMENT PRIMARY KEY,
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
    id INT AUTO_INCREMENT PRIMARY KEY,
    tool_id INT NOT NULL,
    image_url VARCHAR(255),
    is_primary BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (tool_id) REFERENCES tools(id)
);

-- TOOL AVAILABILITY TABLE
CREATE TABLE tool_availability (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tool_id INT NOT NULL,
    date DATE NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (tool_id) REFERENCES tools(id)
);

-- RENTAL REQUESTS TABLE
CREATE TABLE rental_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tool_id INT NOT NULL,
    renter_id INT NOT NULL,
    start_date DATE,
    end_date DATE,
    status ENUM('pending', 'approved', 'rejected', 'completed') DEFAULT 'pending',
    requested_at DATETIME,
    responded_at DATETIME,
    FOREIGN KEY (tool_id) REFERENCES tools(id),
    FOREIGN KEY (renter_id) REFERENCES users(id)
);

-- PAYMENTS TABLE
CREATE TABLE payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rental_id INT NOT NULL,
    stripe_payment_id VARCHAR(255),
    amount DECIMAL(10, 2),
    payment_method VARCHAR(255),
    status VARCHAR(50),
    created_at DATETIME,
    processed_at DATETIME,
    FOREIGN KEY (rental_id) REFERENCES rental_requests(id)
);

-- REVIEWS TABLE
CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rental_id INT NOT NULL,
    reviewer_id INT NOT NULL,
    reviewee_id INT NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at DATETIME,
    FOREIGN KEY (rental_id) REFERENCES rental_requests(id),
    FOREIGN KEY (reviewer_id) REFERENCES users(id),
    FOREIGN KEY (reviewee_id) REFERENCES users(id)
);

-- NOTIFICATIONS TABLE
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    related_entity_type VARCHAR(50),
    related_entity_id INT,
    created_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
