-- Insert sample users
INSERT INTO users (email, password_hash, first_name, last_name, phone, address_line1, city, state, zip_code, profile_picture_url)
VALUES
  ('john.doe@example.com', '$2a$10$xJwL5v5Jz7t6VhAe1tQZ3.QS4VU5wYb9XjJZ8K1fLmN3vW6pY7zG', 'John', 'Doe', '555-123-4567', '123 Main St', 'Springfield', 'IL', '62704', 'https://randomuser.me/api/portraits/men/1.jpg'),
  ('jane.smith@example.com', '$2a$10$xJwL5v5Jz7t6VhAe1tQZ3.QS4VU5wYb9XjJZ8K1fLmN3vW6pY7zG', 'Jane', 'Smith', '555-234-5678', '456 Oak Ave', 'Springfield', 'IL', '62704', 'https://randomuser.me/api/portraits/women/1.jpg'),
  ('mike.johnson@example.com', '$2a$10$xJwL5v5Jz7t6VhAe1tQZ3.QS4VU5wYb9XjJZ8K1fLmN3vW6pY7zG', 'Mike', 'Johnson', '555-345-6789', '789 Pine Rd', 'Springfield', 'IL', '62704', 'https://randomuser.me/api/portraits/men/2.jpg'),
  ('sarah.williams@example.com', '$2a$10$xJwL5v5Jz7t6VhAe1tQZ3.QS4VU5wYb9XjJZ8K1fLmN3vW6pY7zG', 'Sarah', 'Williams', '555-456-7890', '321 Elm St', 'Springfield', 'IL', '62704', 'https://randomuser.me/api/portraits/women/2.jpg'),
  ('david.brown@example.com', '$2a$10$xJwL5v5Jz7t6VhAe1tQZ3.QS4VU5wYb9XjJZ8K1fLmN3vW6pY7zG', 'David', 'Brown', '555-567-8901', '654 Maple Dr', 'Springfield', 'IL', '62704', 'https://randomuser.me/api/portraits/men/3.jpg');
 
-- Insert sample tools
INSERT INTO tools (owner_id, name, description, category, daily_price, deposit_amount, is_available)
VALUES
  (1, 'Power Drill', 'Cordless 20V MAX lithium-ion drill with 2 batteries', 'Power Tools', 15.00, 50.00, TRUE),
  (1, 'Circular Saw', '7-1/4 inch circular saw with laser guide', 'Power Tools', 20.00, 75.00, TRUE),
  (2, 'Lawn Mower', 'Self-propelled gas mower with bagger', 'Lawn & Garden', 25.00, 100.00, TRUE),
  (2, 'Hedge Trimmer', 'Electric hedge trimmer with 22-inch blade', 'Lawn & Garden', 12.00, 40.00, TRUE),
  (3, 'Pressure Washer', 'Gas-powered 3000 PSI pressure washer', 'Outdoor Equipment', 30.00, 150.00, TRUE),
  (3, 'Ladder', '24-foot extension ladder, fiberglass', 'Ladders', 10.00, 75.00, TRUE),
  (4, 'Tile Saw', 'Wet tile saw with stand and blade', 'Specialty Tools', 35.00, 125.00, TRUE),
  (4, 'Air Compressor', '6-gallon pancake air compressor', 'Air Tools', 18.00, 60.00, TRUE),
  (5, 'Table Saw', '10-inch contractor table saw with stand', 'Power Tools', 40.00, 200.00, TRUE),
  (5, 'Generator', '3500W portable generator with electric start', 'Outdoor Equipment', 50.00, 250.00, TRUE);
 
-- Insert tool images
INSERT INTO tool_images (tool_id, image_url, is_primary)
VALUES
  (1, 'https://example.com/images/drill1.jpg', TRUE),
  (1, 'https://example.com/images/drill2.jpg', FALSE),
  (2, 'https://example.com/images/saw1.jpg', TRUE),
  (3, 'https://example.com/images/mower1.jpg', TRUE),
  (3, 'https://example.com/images/mower2.jpg', FALSE),
  (4, 'https://example.com/images/trimmer1.jpg', TRUE),
  (5, 'https://example.com/images/pressure1.jpg', TRUE),
  (6, 'https://example.com/images/ladder1.jpg', TRUE),
  (7, 'https://example.com/images/tile_saw1.jpg', TRUE),
  (8, 'https://example.com/images/compressor1.jpg', TRUE),
  (9, 'https://example.com/images/table_saw1.jpg', TRUE),
  (10, 'https://example.com/images/generator1.jpg', TRUE);
 
-- Set up tool availability for the next 30 days
INSERT INTO tool_availability (tool_id, date, is_available)
SELECT 
  id, 
  DATE_ADD(CURRENT_DATE, INTERVAL n DAY) AS date,
  TRUE AS is_available
FROM 
  tools,
  (SELECT 0 AS n UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION
   SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION
   SELECT 10 UNION SELECT 11 UNION SELECT 12 UNION SELECT 13 UNION SELECT 14 UNION
   SELECT 15 UNION SELECT 16 UNION SELECT 17 UNION SELECT 18 UNION SELECT 19 UNION
   SELECT 20 UNION SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24 UNION
   SELECT 25 UNION SELECT 26 UNION SELECT 27 UNION SELECT 28 UNION SELECT 29) AS days
WHERE 
  tools.is_available = TRUE;
 
-- Mark some days as unavailable for testing
UPDATE tool_availability 
SET is_available = FALSE 
WHERE (tool_id = 1 AND date IN (DATE_ADD(CURRENT_DATE, INTERVAL 3 DAY), DATE_ADD(CURRENT_DATE, INTERVAL 4 DAY)))
   OR (tool_id = 3 AND date IN (DATE_ADD(CURRENT_DATE, INTERVAL 7 DAY), DATE_ADD(CURRENT_DATE, INTERVAL 8 DAY)))
   OR (tool_id = 5 AND date > DATE_ADD(CURRENT_DATE, INTERVAL 20 DAY));
 
-- Create some rental requests
INSERT INTO rental_requests (tool_id, renter_id, start_date, end_date, status, requested_at, responded_at)
VALUES
  (1, 2, DATE_ADD(CURRENT_DATE, INTERVAL 1 DAY), DATE_ADD(CURRENT_DATE, INTERVAL 2 DAY), 'completed', DATE_SUB(NOW(), INTERVAL 5 DAY), DATE_SUB(NOW(), INTERVAL 4 DAY)),
  (3, 1, DATE_ADD(CURRENT_DATE, INTERVAL 5 DAY), DATE_ADD(CURRENT_DATE, INTERVAL 6 DAY), 'approved', DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY)),
  (5, 4, DATE_ADD(CURRENT_DATE, INTERVAL 10 DAY), DATE_ADD(CURRENT_DATE, INTERVAL 12 DAY), 'pending', DATE_SUB(NOW(), INTERVAL 1 DAY), NULL),
  (2, 3, DATE_ADD(CURRENT_DATE, INTERVAL 3 DAY), DATE_ADD(CURRENT_DATE, INTERVAL 4 DAY), 'rejected', DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY)),
  (4, 5, DATE_ADD(CURRENT_DATE, INTERVAL 7 DAY), DATE_ADD(CURRENT_DATE, INTERVAL 9 DAY), 'approved', DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY));
 
-- Create payments for completed rentals
INSERT INTO payments (rental_id, stripe_payment_id, amount, payment_method, status, created_at, processed_at)
VALUES
  (1, 'pi_1JX9Zt2eZvKYlo2C0XJX9Zt2', 30.00, 'card_1JX9Zt2eZvKYlo2C0XJX9Zt2', 'succeeded', DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 4 DAY)),
  (2, 'pi_2JX9Zt2eZvKYlo2C0XJX9Zt2', 50.00, 'card_2JX9Zt2eZvKYlo2C0XJX9Zt2', 'succeeded', DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY)),
  (5, 'pi_3JX9Zt2eZvKYlo2C0XJX9Zt2', 36.00, 'card_3JX9Zt2eZvKYlo2C0XJX9Zt2', 'succeeded', DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY));
 
-- Create some reviews
INSERT INTO reviews (rental_id, reviewer_id, reviewee_id, rating, comment, created_at)
VALUES
  (1, 2, 1, 5, 'Great drill, worked perfectly! John was very helpful showing me how to use it.', DATE_SUB(NOW(), INTERVAL 3 DAY)),
  (1, 1, 2, 4, 'Jane returned the drill on time and in good condition.', DATE_SUB(NOW(), INTERVAL 3 DAY)),
  (5, 5, 4, 3, 'Hedge trimmer worked well but was a bit dull.', DATE_SUB(NOW(), INTERVAL 1 DAY));
 
-- Create some notifications
INSERT INTO notifications (user_id, message, is_read, related_entity_type, related_entity_id, created_at)
VALUES
  (1, 'Your Power Drill has been rented by Jane Smith for 2 days', TRUE, 'rental', 1, DATE_SUB(NOW(), INTERVAL 5 DAY)),
  (2, 'Your rental request for Power Drill has been approved', TRUE, 'rental', 1, DATE_SUB(NOW(), INTERVAL 4 DAY)),
  (3, 'Your rental request for Circular Saw has been declined', TRUE, 'rental', 4, DATE_SUB(NOW(), INTERVAL 1 DAY)),
  (4, 'You have a new rental request for Pressure Washer', FALSE, 'rental', 3, DATE_SUB(NOW(), INTERVAL 1 DAY)),
  (5, 'Payment received for Hedge Trimmer rental', TRUE, 'payment', 3, DATE_SUB(NOW(), INTERVAL 3 DAY));