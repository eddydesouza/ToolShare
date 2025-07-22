-- Insert sample users
INSERT INTO users (
  email, password_hash, first_name, last_name, phone,
  address_line1, city, state, zip_code, profile_picture_url
)
VALUES
  ('john.doe@example.com', '<hash>', 'John', 'Doe', '555-123-4567', '123 Main St', 'Springfield', 'IL', '62704', 'https://randomuser.me/api/portraits/men/1.jpg'),
  ('jane.smith@example.com', '<hash>', 'Jane', 'Smith', '555-234-5678', '456 Oak Ave', 'Springfield', 'IL', '62704', 'https://randomuser.me/api/portraits/women/1.jpg'),
  ('mike.johnson@example.com', '<hash>', 'Mike', 'Johnson', '555-345-6789', '789 Pine Rd', 'Springfield', 'IL', '62704', 'https://randomuser.me/api/portraits/men/2.jpg'),
  ('sarah.williams@example.com', '<hash>', 'Sarah', 'Williams', '555-456-7890', '321 Elm St', 'Springfield', 'IL', '62704', 'https://randomuser.me/api/portraits/women/2.jpg'),
  ('david.brown@example.com', '<hash>', 'David', 'Brown', '555-567-8901', '654 Maple Dr', 'Springfield', 'IL', '62704', 'https://randomuser.me/api/portraits/men/3.jpg')
ON CONFLICT (email) DO NOTHING;


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


-- Tool images
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


-- Tool availability (next 30 days)
DO $$
BEGIN
  FOR i IN 0..29 LOOP
    INSERT INTO tool_availability (tool_id, date, is_available)
    SELECT id, CURRENT_DATE + i, TRUE FROM tools WHERE is_available = TRUE;
  END LOOP;
END
$$;


-- Mark some days unavailable
UPDATE tool_availability
SET is_available = FALSE
WHERE (tool_id = 1 AND date IN (CURRENT_DATE + 3, CURRENT_DATE + 4))
   OR (tool_id = 3 AND date IN (CURRENT_DATE + 7, CURRENT_DATE + 8))
   OR (tool_id = 5 AND date > CURRENT_DATE + 20);


-- Rental requests
INSERT INTO rental_requests (tool_id, renter_id, start_date, end_date, status, requested_at, responded_at)
VALUES
  (1, 2, CURRENT_DATE + 1, CURRENT_DATE + 2, 'completed', CURRENT_TIMESTAMP - INTERVAL '5 days', CURRENT_TIMESTAMP - INTERVAL '4 days'),
  (3, 1, CURRENT_DATE + 5, CURRENT_DATE + 6, 'approved', CURRENT_TIMESTAMP - INTERVAL '3 days', CURRENT_TIMESTAMP - INTERVAL '2 days'),
  (5, 4, CURRENT_DATE + 10, CURRENT_DATE + 12, 'pending', CURRENT_TIMESTAMP - INTERVAL '1 day', NULL),
  (2, 3, CURRENT_DATE + 3, CURRENT_DATE + 4, 'rejected', CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP - INTERVAL '1 day'),
  (4, 5, CURRENT_DATE + 7, CURRENT_DATE + 9, 'approved', CURRENT_TIMESTAMP - INTERVAL '4 days', CURRENT_TIMESTAMP - INTERVAL '3 days');


-- Payments
INSERT INTO payments (rental_id, stripe_payment_id, amount, payment_method, status, created_at, processed_at)
VALUES
  (1, 'pi_1JX9Zt2eZvKYlo2C0XJX9Zt2', 30.00, 'card_1JX9Zt2eZvKYlo2C0XJX9Zt2', 'succeeded', CURRENT_TIMESTAMP - INTERVAL '4 days', CURRENT_TIMESTAMP - INTERVAL '4 days'),
  (2, 'pi_2JX9Zt2eZvKYlo2C0XJX9Zt2', 50.00, 'card_2JX9Zt2eZvKYlo2C0XJX9Zt2', 'succeeded', CURRENT_TIMESTAMP - INTERVAL '2 days', CURRENT_TIMESTAMP - INTERVAL '2 days'),
  (5, 'pi_3JX9Zt2eZvKYlo2C0XJX9Zt2', 36.00, 'card_3JX9Zt2eZvKYlo2C0XJX9Zt2', 'succeeded', CURRENT_TIMESTAMP - INTERVAL '3 days', CURRENT_TIMESTAMP - INTERVAL '3 days');


-- Reviews
INSERT INTO reviews (rental_id, reviewer_id, reviewee_id, rating, comment, created_at)
VALUES
  (1, 2, 1, 5, 'Great drill, worked perfectly! John was very helpful showing me how to use it.', CURRENT_TIMESTAMP - INTERVAL '3 days'),
  (1, 1, 2, 4, 'Jane returned the drill on time and in good condition.', CURRENT_TIMESTAMP - INTERVAL '3 days'),
  (5, 5, 4, 3, 'Hedge trimmer worked well but was a bit dull.', CURRENT_TIMESTAMP - INTERVAL '1 day');


-- Notifications
INSERT INTO notifications (user_id, message, is_read, related_entity_type, related_entity_id, created_at)
VALUES
  (1, 'Your Power Drill has been rented by Jane Smith for 2 days', TRUE, 'rental', 1, CURRENT_TIMESTAMP - INTERVAL '5 days'),
  (2, 'Your rental request for Power Drill has been approved', TRUE, 'rental', 1, CURRENT_TIMESTAMP - INTERVAL '4 days'),
  (3, 'Your rental request for Circular Saw has been declined', TRUE, 'rental', 4, CURRENT_TIMESTAMP - INTERVAL '1 day'),
  (4, 'You have a new rental request for Pressure Washer', FALSE, 'rental', 3, CURRENT_TIMESTAMP - INTERVAL '1 day'),
  (5, 'Payment received for Hedge Trimmer rental', TRUE, 'payment', 3, CURRENT_TIMESTAMP - INTERVAL '3 days');
