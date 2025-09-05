from flask import Flask, request, render_template, redirect, url_for, flash
import mysql.connector
import stripe
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecret')

db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'toolshare_user'),
    'password': os.getenv('DB_PASS', 'StrongPassword123!'),
    'database': os.getenv('DB_NAME', 'toolshare')
}

stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_your_test_key')

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM artisans")
    artisans = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', artisans=artisans)

@app.route('/register_artisan', methods=['GET', 'POST'])
def register_artisan():
    if request.method == 'POST':
        name = request.form.get('name')
        zip_code = request.form.get('zip_code')
        product_name = request.form.get('product_name')
        subscription_price = request.form.get('subscription_price')

        if not name or not zip_code or not product_name or not subscription_price:
            flash("All fields are required.", "danger")
            return redirect(url_for('register_artisan'))

        try:
            subscription_price = float(subscription_price)
        except ValueError:
            flash("Invalid price format.", "danger")
            return redirect(url_for('register_artisan'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO artisans (name, zip_code, product_name, subscription_price) VALUES (%s, %s, %s, %s)",
            (name, zip_code, product_name, subscription_price)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash("Artisan registered successfully!", "success")
        return redirect(url_for('index'))

    return render_template('register_artisan.html')

@app.route('/subscribe/<int:artisan_id>', methods=['GET', 'POST'])
def subscribe(artisan_id):
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        email = request.form.get('email')
        zip_code = request.form.get('zip_code')
        product_name = request.form.get('product_name')
        subscription_price = request.form.get('subscription_price')

        if not customer_name or not email or not zip_code:
            flash("All fields are required.", "danger")
            return redirect(url_for('subscribe', artisan_id=artisan_id))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO customers (name, email, zip_code) VALUES (%s, %s, %s)",
                (customer_name, email, zip_code)
            )
            customer_id = cursor.lastrowid

            stripe_customer = stripe.Customer.create(
                email=email,
                name=customer_name
            )

            subscription = stripe.Subscription.create(
                customer=stripe_customer.id,
                items=[{
                    'price_data': {
                        'unit_amount': int(float(subscription_price) * 100),
                        'currency': 'usd',
                        'product_data': {'name': product_name},
                        'recurring': {'interval': 'month'}
                    }
                }]
            )

            cursor.execute(
                "INSERT INTO subscriptions (customer_id, artisan_id, stripe_subscription_id, status) VALUES (%s, %s, %s, %s)",
                (customer_id, artisan_id, subscription.id, subscription.status)
            )

            conn.commit()
            cursor.close()
            conn.close()
            flash("Subscription successful!", "success")
            return redirect(url_for('index'))

        except stripe.error.StripeError as e:
            flash(f"Stripe Error: {str(e)}", "danger")
            return redirect(url_for('subscribe', artisan_id=artisan_id))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM artisans WHERE id = %s", (artisan_id,))
    artisan = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('subscribe.html', artisan=artisan)

if __name__ == '__main__':
    app.run(debug=True)

