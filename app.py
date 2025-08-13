from flask import Flask, request, render_template, redirect, url_for, flash
import stripe
import os
from dotenv import load_dotenv
from user_routes import user_bp
from search_routes import search_bp
from tool_routes import tool_bp
from db import get_db_connection
from tool_api import tool_api
from werkzeug.utils import secure_filename
from datetime import datetime, timezone

# Load environment variables from .env file (optional but helpful for dev)
load_dotenv()

# Flask app setup
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecret')  # Needed for flash messages
app.register_blueprint(user_bp)
app.register_blueprint(search_bp)
app.register_blueprint(tool_bp)
app.register_blueprint(tool_api)

# Stripe Test Mode key
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_your_test_key')

# Upload configs for flask/Bootstrap to prevent malicious entries
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
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

        # Basic validation
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

        # Basic validation
        if not customer_name or not email or not zip_code:
            flash("All fields are required.", "danger")
            return redirect(url_for('subscribe', artisan_id=artisan_id))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Insert customer into database
            cursor.execute(
                "INSERT INTO customers (name, email, zip_code) VALUES (%s, %s, %s)",
                (customer_name, email, zip_code)
            )
            customer_id = cursor.lastrowid

            # Create Stripe Customer
            stripe_customer = stripe.Customer.create(
                email=email,
                name=customer_name
            )

            # Create Stripe Subscription
            subscription = stripe.Subscription.create(
                customer=stripe_customer.id,
                items=[{
                    'price_data': {
                        'unit_amount': int(float(subscription_price) * 100),
                        'currency': 'usd',
                        'product_data': {
                            'name': product_name
                        },
                        'recurring': {
                            'interval': 'month'
                        }
                    }
                }]
            )

            # Store subscription record in database
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

    # Fetch artisan details to show in the form
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM artisans WHERE id = %s", (artisan_id,))
    artisan = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('subscribe.html', artisan=artisan)
@app.route('/tools', methods=['GET'])
def list_tools():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, name, description, photo_path, created_at
        FROM tools
        ORDER BY created_at DESC
    """)
    tools = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('tools.html', tools=tools)

@app.route('/tools/new', methods=['GET', 'POST'])
def create_tool():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        owner_id = request.form.get('owner_id', '').strip() or '1'  # fallback to 1

        if not name or not description:
            flash("Please fill in the name and description.", "danger")
            return redirect(url_for('create_tool'))

        photo = request.files.get('photo')
        photo_path = None
        if photo and photo.filename:
            if allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                base, ext = os.path.splitext(filename)
                # fix deprecation warning (use timezone-aware now)
                filename = f"{base}_{int(datetime.now(timezone.utc).timestamp())}{ext}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(save_path)
                photo_path = f"uploads/{filename}"
            else:
                flash("Please upload a valid image (png, jpg, jpeg, gif).", "danger")
                return redirect(url_for('create_tool'))

        conn = get_db_connection()
        cursor = conn.cursor()
        # INSERT now includes owner_id
        cursor.execute(
            "INSERT INTO tools (name, description, photo_path, owner_id, created_at) VALUES (%s, %s, %s, %s, NOW())",
            (name, description, photo_path, owner_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Tool listing created!", "success")
        return redirect(url_for('list_tools'))

    # GET
    return render_template('create_tool.html')


# Run the app
if __name__ == '__main__':
    app.run(debug=True)
