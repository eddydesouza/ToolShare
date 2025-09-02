import os
import re
from datetime import datetime, timezone, date, timedelta
from functools import wraps
from typing import Optional
from flask import (Flask, request, redirect, render_template, redirect, url_for, flash, session, jsonify)
from werkzeug.utils import secure_filename
from werkzeug.routing import BuildError
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import mysql.connector
import stripe
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
import click

# =========================================================
# Environment / Config / DB
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path=ENV_PATH)

db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'database': os.getenv('DB_NAME'),
    'ssl_ca': os.getenv('SSL_CA')
}

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))   # default: 587 (TLS)
SMTP_USER = os.getenv("SMTP_USER", "youremail@example.com")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_USE_TLS = (os.getenv("SMTP_USE_TLS", "true").lower() == "true")
FROM_EMAIL = os.getenv("FROM_EMAIL", "youremail@example.com")

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecret')

def get_cart():
    cart = session.get("cart")
    if not isinstance(cart, dict):
        cart = {}
        session["cart"] = cart
        session.modified = True
    return cart

# Stripe (test key expected)
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_your_test_key')

# Uploads
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# =========================================================
# DB helpers
# =========================================================

# Helper: always return a dict for the cart
def get_db_connection():
    return mysql.connector.connect(**db_config)

def dict_query(sql, params=()):
    """Return list of dict rows."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def dict_getone(sql, params=()):
    """Return one dict row or None."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    row = cur.fetchone()
    cur.close(); conn.close()
    return row

def exec_write(sql, params=()):
    """Execute INSERT/UPDATE/DELETE and commit; return lastrowid if available."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()
    last_id = getattr(cur, "lastrowid", None)
    cur.close(); conn.close()
    return last_id

# =========================================================
# Generic helpers
# =========================================================
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def tool_photo_path(photo_path: Optional [str] | None) -> str: 
    if not photo_path:
        return 'images/default-tool.png'
    path = os.path.join("static", photo_path.replace("\\", "/"))
    if not os.path.exists(path):
        return 'images/default-tool.png'

    return photo_path.replace("\\", "/")

def go_cart_or_search():
    """Prefer cart; fall back gracefully to search or index."""
    try:
        return redirect(url_for('view_cart'))
    except BuildError:
        for endpoint in ('search_tools', 'search.search_tools', 'index'):
            try:
                return redirect(url_for(endpoint))
            except BuildError:
                continue
    return redirect('/')

def get_categories():
    rows = dict_query("""
        SELECT DISTINCT category
        FROM tools
        WHERE category IS NOT NULL
          AND daily_price IS NOT NULL
          AND category <> ''
        ORDER BY category
    """)
    return [r['category'] for r in rows]

def get_user_zip_for_search():
    """Use explicit ?zip= first; otherwise user's profile ZIP if logged-in."""
    z = (request.values.get('zip') or '').strip()
    if z:
        return z
    uid = session.get('user_id')
    if not uid:
        return ''
    me = dict_getone("SELECT zip_code FROM users WHERE id = %s", (uid,))
    return (me.get('zip_code') or '').strip() if me else ''

def compute_cart_totals(cart: dict):
    """
    Rent: sum(price * quantity) for every cart line.
    Deposit: charge ONCE per unique tool_id (use the max deposit seen for that tool).
    """
    rent_total = 0.0
    deposit_by_tool = {}  # tool_id -> deposit once

    for _, it in cart.items():
        qty = max(1, int(it.get("quantity", 1)))
        price = float(it.get("price", 0.0))
        deposit = float(it.get("deposit", 0.0) or 0.0)
        rent_total += price * qty

        tool_id = it.get("tool_id")
        if tool_id and deposit > 0:
            if tool_id not in deposit_by_tool:
                deposit_by_tool[tool_id] = deposit
            else:
                # if somehow inconsistent, take the higher
                deposit_by_tool[tool_id] = max(deposit_by_tool[tool_id], deposit)

    deposit_total = sum(deposit_by_tool.values())
    grand_total = rent_total + deposit_total
    return rent_total, deposit_total, grand_total

def ensure_dates_available(cart: dict):
    """
    Guardrail before Stripe: for any cart line with a specific date,
    confirm there's NOT an is_available=0 block for that (tool_id, date).
    Returns list of (tool_name, date) conflicts.
    """
    conflicts = []
    for _, it in cart.items():
        day_str = it.get('date')
        if not day_str:
            continue
        try:
            d = datetime.strptime(day_str, "%Y-%m-%d").date()
        except Exception:
            continue
        row = dict_getone(
            "SELECT 1 FROM tool_availability WHERE tool_id=%s AND `date`=%s AND is_available=0 LIMIT 1",
            (it.get('tool_id'), d)
        )
        if row:
            conflicts.append((it.get('name', 'Tool'), d))
    return conflicts

app.jinja_env.globals.update(tool_photo_path=tool_photo_path)

# =========================================================
# Auth gating (public -> index/login/signup/logout/static)
# =========================================================
def require_login(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            flash("Please log in to continue.", "warning")
            # Preserve next so user returns to the page they wanted
            next_target = (request.full_path or request.path or '/').rstrip('?')
            return redirect(url_for('login', next=next_target))
        return view(*args, **kwargs)
    return wrapper

ANON_OK_ENDPOINTS = {
    'index', 'login', 'signup', 'logout', 'static',
}

@app.before_request
def require_auth_for_most():
    if request.endpoint is None:
        return
    if request.endpoint in ANON_OK_ENDPOINTS:
        return
    if request.endpoint.startswith('auth.'):
        return
    if not session.get('user_id'):
        flash("Please log in to continue.", "warning")
        next_target = (request.full_path or request.path or '/').rstrip('?')
        return redirect(url_for('login', next=next_target))

# =========================================================
# Public & Auth
# =========================================================
@app.route('/')
def index():
    artisans = dict_query("SELECT * FROM artisans")
    categories = get_categories()
    return render_template('index.html', artisans=artisans, categories=categories)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        phone = request.form['phone'].strip()
        address_line1 = request.form['address_line1'].strip()
        city = request.form['city'].strip()
        state = (request.form['state'] or '').strip().upper()
        zip_code = request.form['zip_code'].strip()

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            cur.close(); conn.close()
            flash("Email already registered. Please log in.", "warning")
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password)
        cur.execute("""
            INSERT INTO users
              (email, password_hash, first_name, last_name, phone,
               address_line1, city, state, zip_code, created_at)
            VALUES
              (%s, %s, %s, %s, %s,
               %s, %s, %s, %s, UTC_TIMESTAMP())
        """, (email, hashed_password, first_name, last_name, phone,
              address_line1, city, state, zip_code))
        conn.commit()
        cur.close(); conn.close()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        next_url = request.form.get('next')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close(); conn.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]
            flash("Login successful!", "success")
            return redirect(next_url or url_for('index'))
        else:
            flash("Invalid email or password", "danger")

    next_url = request.args.get('next') or ''
    return render_template('login.html', next_url=next_url)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

# =========================================================
# Profile (user self-service)
# =========================================================
@app.route('/profile', methods=['GET'])
@require_login
def profile():
    user_id = session.get('user_id')
    user = dict_getone("SELECT * FROM users WHERE id = %s", (user_id,))
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('index'))
    return render_template('profile.html', user=user)

@app.route('/update_profile', methods=['POST'])
@require_login
def update_profile():
    session_user_id = session.get('user_id')

    form_user_id = request.form.get('user_id')
    if str(session_user_id) != str(form_user_id):
        flash("You can only update your own profile.", "danger")
        return redirect(url_for('profile'))

    email = request.form.get('email', '').strip()
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    phone = request.form.get('phone', '').strip()
    address_line1 = request.form.get('address_line1', '').strip()
    city = request.form.get('city', '').strip()
    state = (request.form.get('state') or '').strip().upper()
    zip_code = request.form.get('zip_code', '').strip()

    if not email or not first_name or not last_name:
        flash("First name, last name, and email are required.", "danger")
        return redirect(url_for('profile'))

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash("Invalid email format.", "danger")
        return redirect(url_for('profile'))

    if phone and not re.match(r"^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$", phone):
        flash("Invalid phone number format.", "danger")
        return redirect(url_for('profile'))

    if zip_code and not re.match(r"^\d{5}(-\d{4})?$", zip_code):
        flash("Invalid ZIP code format.", "danger")
        return redirect(url_for('profile'))

    if state and not re.match(r"^[A-Z]{2}$", state):
        flash("State must be a 2-letter abbreviation (e.g., MS, CA).", "danger")
        return redirect(url_for('profile'))

    exec_write("""
        UPDATE users
        SET email=%s, first_name=%s, last_name=%s, phone=%s,
            address_line1=%s, city=%s, state=%s, zip_code=%s
        WHERE id=%s
    """, (email, first_name, last_name, phone, address_line1, city, state, zip_code, session_user_id))

    flash("Profile updated successfully!", "success")
    return redirect(url_for('profile'))

# =========================================================
# Tools (create, view, owner public profile)
# =========================================================
@app.route('/tools/new', methods=['GET', 'POST'])
@require_login
def create_tool():
    if request.method == 'POST':
        owner_id = session.get('user_id')
        name = (request.form.get('name') or '').strip()
        description = (request.form.get('description') or '').strip()
        category = (request.form.get('category') or '').strip()
        daily_price_raw = (request.form.get('daily_price') or '').strip()
        deposit_amount_raw = (request.form.get('deposit_amount') or '').strip()
        is_available = 1 if request.form.get('is_available') == 'on' else 0

        if not name or not description or not category:
            flash("Name, description, and category are required.", "danger")
            return redirect(url_for('create_tool'))

        try:
            daily_price = float(daily_price_raw)
            deposit_amount = float(deposit_amount_raw or 0.0)
            if daily_price < 0 or deposit_amount < 0:
                raise ValueError()
        except ValueError:
            flash("Daily price and deposit must be valid non-negative numbers.", "danger")
            return redirect(url_for('create_tool'))

        photo = request.files.get('photo')
        photo_path = None
        if photo and photo.filename:
            if allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                base, ext = os.path.splitext(filename)
                filename = f"{base}_{int(datetime.now(timezone.utc).timestamp())}{ext}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                photo.save(save_path)
                photo_path = f"uploads/{filename}"
            else:
                flash("Please upload a valid image (png, jpg, jpeg, gif).", "danger")
                return redirect(url_for('create_tool'))

        exec_write("""
            INSERT INTO tools
                (owner_id, name, description, photo_path, created_at, category, daily_price, deposit_amount, is_available)
            VALUES
                (%s, %s, %s, %s, NOW(), %s, %s, %s, %s)
        """, (owner_id, name, description, photo_path, category, daily_price, deposit_amount, is_available))

        flash("Tool registered successfully!", "success")
        try:
            return redirect(url_for('search_tools'))
        except BuildError:
            return redirect(url_for('index'))

    return render_template('create_tool.html', default_available=True)

@app.route('/tools/<int:tool_id>', methods=['GET'])
def tool_detail(tool_id):
    tool = dict_getone("""
        SELECT id, owner_id, name, description, category, daily_price, deposit_amount, is_available, photo_path
        FROM tools
        WHERE id = %s
    """, (tool_id,))
    if not tool:
        flash("Tool not found.", "danger")
        return redirect(url_for('search_tools'))

    owner = dict_getone("""
        SELECT id, first_name, last_name, city, state, zip_code
        FROM users
        WHERE id = %s
    """, (tool['owner_id'],))
    return render_template('tool_detail.html', tool=tool, owner=owner)

@app.route('/users/<int:user_id>', methods=['GET'])
def public_profile(user_id):
    owner = dict_getone("""
        SELECT id, first_name, last_name, city, state, zip_code
        FROM users
        WHERE id = %s
    """, (user_id,))
    if not owner:
        flash("User not found.", "danger")
        return redirect(url_for('search_tools'))

    owner_tools = dict_query("""
        SELECT id, name, category, daily_price, deposit_amount, is_available, photo_path
        FROM tools
        WHERE owner_id = %s
        ORDER BY name
    """, (user_id,))
    return render_template('public_profile.html', owner=owner, tools=owner_tools)

# =========================================================
# Availability API (calendar & blocks)
# =========================================================
@app.route('/api/tool_availability/<int:tool_id>')
def api_tool_availability(tool_id):
    def parse_d(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None

    qstart = parse_d(request.args.get("start", ""))
    qend   = parse_d(request.args.get("end", ""))

    today = date.today()
    start = qstart or today
    end   = qend or (today + timedelta(days=90))
    if end < start:
        start, end = end, start

    blocked_rows = dict_query("""
        SELECT `date`
        FROM tool_availability
        WHERE tool_id = %s
          AND is_available = 0
          AND `date` BETWEEN %s AND %s
    """, (tool_id, start, end))
    blocked = {r['date'] for r in blocked_rows}

    events = []
    cur = start
    while cur <= end:
        is_avail = (cur not in blocked)
        events.append({
            'title': 'Available' if is_avail else 'Unavailable',
            'start': cur.isoformat(),
            'allDay': True,
            'color': 'green' if is_avail else 'red'
        })
        cur += timedelta(days=1)

    return jsonify({'events': events})

@app.route('/api/tools/<int:tool_id>/block_dates', methods=['POST'])
@require_login
def api_block_dates(tool_id):
    data = request.get_json(silent=True) or {}
    dates = data.get('dates') or []

    clean_dates = []
    for s in dates:
        try:
            d = datetime.strptime(s, "%Y-%m-%d").date()
            clean_dates.append(d)
        except Exception:
            continue

    if not clean_dates:
        return jsonify({'ok': False, 'error': 'No valid dates provided.'}), 400

    for d in clean_dates:
        exec_write("""
            INSERT INTO tool_availability (tool_id, `date`, is_available)
            VALUES (%s, %s, 0)
            ON DUPLICATE KEY UPDATE is_available = VALUES(is_available)
        """, (tool_id, d))

    return jsonify({'ok': True, 'blocked': [d.isoformat() for d in clean_dates]})

# =========================================================
# Search / Browse
# =========================================================
ENFORCE_AVAILABLE = True

@app.route('/search', methods=['GET', 'POST'])
def search_tools():
    search_term = (request.values.get('search_term') or '').strip()
    selected_category = (request.values.get('category') or '').strip()
    zip_input = get_user_zip_for_search()
    radius_miles = (request.values.get('radius') or '').strip()

    categories = get_categories()

    try:
        radius_val = float(radius_miles) if radius_miles else None
    except ValueError:
        radius_val = None

    where = []
    params = []

    if search_term:
        like = f"%{search_term.lower()}%"
        where.append("LOWER(COALESCE(t.name, '')) LIKE %s")
        params.append(like)

    if selected_category:
        where.append("LOWER(COALESCE(t.category, '')) = %s")
        params.append(selected_category.lower())

    if ENFORCE_AVAILABLE:
        where.append("t.is_available = 1")

    base_where_sql = "WHERE " + " AND ".join(where) if where else ("WHERE t.is_available = 1" if ENFORCE_AVAILABLE else "")

    def query_without_zip():
        sql = f"""
            SELECT t.id, t.owner_id, t.name, t.description, t.category,
                   t.daily_price, t.deposit_amount, t.is_available
            FROM tools t
            {base_where_sql}
            ORDER BY t.name
            LIMIT 200
        """
        return dict_query(sql, params)

    if zip_input:
        spacer = (" AND " if base_where_sql else " WHERE ")
        sql_zip = f"""
            SELECT
              t.id, t.owner_id, t.name, t.description, t.category,
              t.daily_price, t.deposit_amount, t.is_available,
              ROUND(
                3959 * 2 * ASIN(
                  SQRT(
                    POWER(SIN(RADIANS(zt.lat - r.ref_lat) / 2), 2) +
                    COS(RADIANS(r.ref_lat)) * COS(RADIANS(zt.lat)) *
                    POWER(SIN(RADIANS(zt.lon - r.ref_lon) / 2), 2)
                  )
                )
              , 1) AS distance_mi
            FROM tools t
            JOIN users ow ON ow.id = t.owner_id
            JOIN zipcodes zt ON zt.zip = ow.zip_code
            JOIN (
                SELECT lat AS ref_lat, lon AS ref_lon
                FROM zipcodes
                WHERE zip = %s
            ) r ON 1=1
            {base_where_sql}{spacer}(r.ref_lat IS NOT NULL AND r.ref_lon IS NOT NULL)
            HAVING (%s IS NULL OR distance_mi <= %s)
            ORDER BY distance_mi ASC, t.name
            LIMIT 200
        """
        rows = dict_query(sql_zip, [zip_input] + params + [radius_val, radius_val])
        tools = rows if rows else query_without_zip()
    else:
        tools = query_without_zip()

    return render_template(
        'search.html',
        tools=tools,
        categories=categories,
        selected_category=selected_category,
        search_term=search_term,
        zip=zip_input or '',
        radius=radius_val
    )

# =========================================================
# Cart / Checkout
# =========================================================
@app.route('/add_to_cart/<int:tool_id>', methods=['POST'])
def add_to_cart(tool_id):
    tool = dict_getone("""
        SELECT id, name, daily_price, deposit_amount
        FROM tools
        WHERE id = %s
    """, (tool_id,))
    if not tool:
        try:
            return redirect(url_for('search_tools'))
        except BuildError:
            return redirect(url_for('index'))

    quantity = request.form.get('quantity', type=int) or 1
    cart = session.get('cart', {})
    key = str(tool_id)

    line = cart.get(key) or {
        'tool_id': tool_id,
        'name': tool['name'],
        'price': float(tool.get('daily_price') or 0.0),
        'deposit': float(tool.get('deposit_amount') or 0.0),
        'quantity': 0
    }
    line['quantity'] = int(line.get('quantity', 0)) + max(1, quantity)
    cart[key] = line

    session['cart'] = cart
    flash("Added to cart.", "success")
    return redirect(url_for('view_cart'))

@app.route('/search/add_to_cart_date', methods=['POST'])
def add_to_cart_date():
    tool_id = request.form.get('tool_id', type=int)
    selected_date = (request.form.get('selected_date') or '').strip()

    if not tool_id or not selected_date:
        flash("Missing tool or date.", "danger")
        return go_cart_or_search()

    try:
        day = datetime.strptime(selected_date, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format.", "danger")
        return go_cart_or_search()

    tool = dict_getone("""
        SELECT id, name, daily_price, deposit_amount
        FROM tools
        WHERE id = %s
    """, (tool_id,))
    if not tool:
        flash("Tool not found.", "danger")
        return go_cart_or_search()

    cart = session.get('cart', {})
    key = f"{tool_id}:{day.isoformat()}"  # allows same tool on different days

    if key in cart:
        cart[key]['quantity'] = int(cart[key].get('quantity', 1)) + 1
    else:
        cart[key] = {
            'tool_id': tool_id,
            'name': tool['name'],
            'price': float(tool.get('daily_price') or 0.0),
            'deposit': float(tool.get('deposit_amount') or 0.0),
            'quantity': 1,
            'date': day.isoformat()
        }

    session['cart'] = cart
    flash("Added to cart.", "success")
    return redirect(url_for('view_cart'))

@app.route('/search/add_to_cart_dates', methods=['POST'])
def add_to_cart_dates():
    tool_id = request.form.get('tool_id', type=int)
    raw = request.form.getlist('selected_dates')  # multiple hidden inputs

    if not tool_id or not raw:
        flash("Missing tool or dates.", "danger")
        return redirect(url_for('search_tools'))

    tool = dict_getone("""
        SELECT id, name, daily_price, deposit_amount
        FROM tools WHERE id = %s
    """, (tool_id,))
    if not tool:
        flash("Tool not found.", "danger")
        return redirect(url_for('search_tools'))

    dates = []
    for s in raw:
        try:
            d = datetime.strptime(s, "%Y-%m-%d").date()
            dates.append(d)
        except Exception:
            pass

    if not dates:
        flash("No valid dates selected.", "danger")
        return redirect(url_for('search_tools'))

    cart = session.get('cart', {})
    added = 0
    for d in sorted(set(dates)):
        key = f"{tool_id}:{d.isoformat()}"
        if key in cart:
            cart[key]['quantity'] = int(cart[key].get('quantity', 1)) + 1
        else:
            cart[key] = {
                'tool_id': tool_id,
                'name': tool['name'],
                'price': float(tool.get('daily_price') or 0.0),
                'deposit': float(tool.get('deposit_amount') or 0.0),
                'quantity': 1,
                'date': d.isoformat()
            }
        added += 1

    session['cart'] = cart
    flash(f"Added {added} date(s) to cart.", "success")
    return redirect(url_for('view_cart'))

@app.route('/cart')
def view_cart():
    cart = session.get('cart', {})
    rent_total, deposit_total, grand_total = compute_cart_totals(cart)
    return render_template(
        'cart.html',
        cart=cart,
        rent_total=rent_total,
        deposit_total=deposit_total,
        grand_total=grand_total
    )

@app.route('/cart/remove/<path:item_key>', methods=['POST'])
def remove_from_cart(item_key):
    cart = session.get('cart', {})
    item = cart.get(item_key)

    if not item:
        flash("Item not found in cart.", "warning")
        return redirect(url_for('view_cart'))

    qty = int(item.get('quantity', 1))
    if qty > 1:
        item['quantity'] = qty - 1
        cart[item_key] = item
        flash(f"Removed 1 × {item.get('name', 'item')} (remaining: {item['quantity']}).", "success")
    else:
        cart.pop(item_key)
        flash(f"Removed {item.get('name', 'item')} from cart.", "success")

    session['cart'] = cart
    return redirect(url_for('view_cart'))

@app.route('/cart/clear', methods=['POST'])
def cart_clear():
    session.pop('cart', None)
    session.modified = True
    flash('Cart cleared.', 'success')
    return redirect(url_for('view_cart'))

# CREATING STRIPE CHECKOUT SECTION
@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    cart = session.get('cart', {})
    if not cart:
        flash("Your cart is empty.", "warning")
        return go_cart_or_search()

    # Pre-checkout guardrail: ensure requested date(s) are still available
    conflicts = ensure_dates_available(cart)
    if conflicts:
        lines = "\n".join(f"• {name} on {d.isoformat()}" for name, d in conflicts)
        flash(f"Some dates were just blocked or reserved:\n{lines}", "danger")
        return redirect(url_for('view_cart'))

    line_items = []

    # 1) Rent line items: per cart line as before
    for _, item in cart.items():
        name = item.get('name', 'Tool')
        qty = max(1, int(item.get('quantity', 1)))

        rent_cents = max(0, int(round(float(item.get('price', 0.0)) * 100)))
        if rent_cents > 0:
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': name if not item.get('date') else f"{name} – {item['date']}"},
                    'unit_amount': rent_cents,
                },
                'quantity': qty,
            })

    # 2) Deposits: once per unique tool_id
    deposit_by_tool = {}
    name_by_tool = {}
    for _, item in cart.items():
        tid = item.get('tool_id')
        dep = float(item.get('deposit', 0.0) or 0.0)
        if not tid or dep <= 0:
            continue
        name_by_tool.setdefault(tid, item.get('name', 'Tool'))
        if tid not in deposit_by_tool:
            deposit_by_tool[tid] = dep
        else:
            deposit_by_tool[tid] = max(deposit_by_tool[tid], dep)

    for tid, dep in deposit_by_tool.items():
        dep_cents = max(0, int(round(dep * 100)))
        line_items.append({
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': f"{name_by_tool.get(tid, 'Tool')} – Refundable deposit"},
                'unit_amount': dep_cents,
            },
            'quantity': 1,  # deposit once per tool
        })

    if not line_items:
        flash("No payable items found.", "warning")
        return redirect(url_for('view_cart'))

    try:
        checkout_session = stripe.checkout.Session.create(
            mode='payment',
            payment_method_types=['card'],
            line_items=line_items,
            success_url=url_for('checkout_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('checkout_cancel', _external=True),  
        )
    except Exception as e:
        app.logger.exception("Stripe checkout session error")
        flash(f"Stripe error: {e}", "danger")
        return redirect(url_for('view_cart'))

    return redirect(checkout_session.url, code=303)

@app.route('/checkout/success')
def checkout_success():
    session_id = request.args.get('session_id')
    try:
        if session_id:
            s = stripe.checkout.Session.retrieve(session_id)
            if str(s.get('payment_status', '')).lower() != 'paid':
                flash("Payment not completed.", "danger")
                return redirect(url_for('view_cart'))
    except Exception:
        # Don’t block the user if we can’t retrieve (network wobble, etc.)
        pass

    cart = session.get('cart', {})
    if not cart:
        flash("Thanks! Your payment was received.", "success")
        return redirect(url_for('index'))

    # Reserve each tool:date now that payment is complete
    for _, item in cart.items():
        tool_id = item.get('tool_id')
        day_str = item.get('date')
        if not tool_id or not day_str:
            continue
        try:
            d = datetime.strptime(day_str, "%Y-%m-%d").date()
            exec_write("""
                INSERT INTO tool_availability (tool_id, `date`, is_available)
                VALUES (%s, %s, 0)
                ON DUPLICATE KEY UPDATE is_available = VALUES(is_available)
            """, (tool_id, d))
        except Exception:
            pass

    session['cart'] = {}
    flash("Payment successful! Your dates are reserved.", "success")
    return redirect(url_for('index'))

@app.route("/checkout/cancel", methods=['GET']) # Cancel landing from Stripe 
def checkout_cancel():
    flash("Checkout canceled. Your cart is still available.", "warning")
    return redirect(url_for("view_cart"))

# =========================================================
# Rentals (Renter)
# =========================================================
@app.route("/rentals")
@require_login
def rentals():
    uid = session["user_id"]
    rows = dict_query("""
        SELECT rr.id, rr.start_date, rr.end_date, rr.status,
               rr.requested_at, rr.responded_at, rr.refunded_at,
               t.id AS tool_id, t.name AS tool_name, t.photo_path, t.daily_price, t.deposit_amount
        FROM rental_requests rr
        JOIN tools t ON t.id = rr.tool_id
        WHERE rr.renter_id = %s
          AND (rr.status = 'completed' OR rr.end_date < CURDATE()
               OR (rr.status IN ('pending','approved','cancelled') AND rr.end_date >= CURDATE()))
        ORDER BY rr.end_date DESC, rr.id DESC
    """, (uid,))
    return render_template("rentals.html", items=rows, today=date.today())

# =========================================================
# Owner Workflows + Email (unchanged below)
# =========================================================
# ... keep your existing owner routes, email helpers, CLI, and main() unchanged ...
@app.route("/owner/upcoming")
@require_login
def owner_upcoming():
    uid = session["user_id"]
    rows = dict_query("""
        SELECT rr.id, rr.start_date, rr.end_date, rr.status,
               rr.requested_at, rr.responded_at, rr.refunded_at,
               rr.payment_intent_id,
               rr.rental_cents, rr.deposit_cents,
               (IFNULL(rr.rental_cents,0) + IFNULL(rr.deposit_cents,0)) AS total_cents,
               rr.currency,
               t.id AS tool_id, t.name AS tool_name, t.photo_path,
               u.id AS renter_id, u.first_name, u.last_name, u.email
        FROM rental_requests rr
        JOIN tools t ON t.id = rr.tool_id
        JOIN users u ON u.id = rr.renter_id
        WHERE t.owner_id = %s
          AND rr.status IN ('approved','pending','cancelled')
          AND rr.end_date >= CURDATE()
        ORDER BY rr.start_date ASC, rr.id ASC
    """, (uid,))
    return render_template("owner_upcoming.html", items=rows)

@app.route("/owner/active")
@require_login
def owner_active():
    uid = session["user_id"]
    rows = dict_query("""
        SELECT rr.id, rr.start_date, rr.end_date, rr.status,
               rr.requested_at, rr.responded_at, rr.refunded_at, rr.completed_at,
               rr.payment_intent_id, rr.currency,
               rr.rental_cents, rr.deposit_cents,
               (IFNULL(rr.rental_cents,0) + IFNULL(rr.deposit_cents,0)) AS total_cents,
               t.id AS tool_id, t.name AS tool_name, t.photo_path,
               u.id AS renter_id, u.first_name, u.last_name, u.email
        FROM rental_requests rr
        JOIN tools t ON t.id = rr.tool_id
        JOIN users u ON u.id = rr.renter_id
        WHERE t.owner_id = %s
          AND rr.status IN ('approved','completed')
          AND rr.start_date <= CURDATE()
          AND rr.end_date >= DATE_SUB(CURDATE(), INTERVAL 1 DAY)
        ORDER BY rr.start_date ASC, rr.id ASC
    """, (uid,))

    return render_template("owner_active.html", items=rows, today=date.today())

@app.route("/owner/rental_requests/<int:req_id>/return_refund", methods=["POST"])
@require_login
def owner_return_and_refund(req_id):
    # unchanged...
    uid = session["user_id"]
    rr = dict_getone("""
        SELECT rr.id, rr.status, rr.tool_id, rr.start_date, rr.end_date,
               rr.payment_intent_id, rr.rental_cents, rr.deposit_cents, rr.currency,
               rr.refund_id, rr.responded_at, rr.refunded_at, rr.completed_at,
               t.name AS tool_name, t.owner_id
        FROM rental_requests rr
        JOIN tools t ON t.id = rr.tool_id
        WHERE rr.id = %s
    """, (req_id,))
    if not rr or rr["owner_id"] != uid:
        flash("Not authorized for this rental.", "danger")
        return redirect(url_for("owner_active"))
    if rr["status"] not in ("approved", "completed"):
        flash("Rental is not in a returnable state.", "warning")
        return redirect(url_for("owner_active"))
    if rr.get("refunded_at"):
        if not rr.get("completed_at"):
            exec_write("UPDATE rental_requests SET completed_at = NOW() WHERE id = %s", (req_id,))
        flash("Deposit already refunded.", "info")
        return redirect(url_for("owner_active"))
    deposit_cents = int(rr.get("deposit_cents") or 0)
    if deposit_cents <= 0:
        exec_write("UPDATE rental_requests SET completed_at = NOW() WHERE id = %s", (req_id,))
        flash("Marked as returned (no deposit to refund).", "success")
        return redirect(url_for("owner_active"))
    pi = rr.get("payment_intent_id")
    if not pi:
        exec_write("UPDATE rental_requests SET completed_at = NOW() WHERE id = %s", (req_id,))
        flash("Marked returned; no payment on file to auto-refund deposit.", "warning")
        return redirect(url_for("owner_active"))
    try:
        refund = stripe.Refund.create(
            payment_intent=pi,
            amount=deposit_cents,
            metadata={
                "rental_request_id": str(rr["id"]),
                "tool_id": str(rr["tool_id"]),
                "reason": "return_refund_deposit_only"
            },
            idempotency_key=f"rr-{req_id}-deposit-refund-v1"
        )
        exec_write("""
            UPDATE rental_requests
            SET refund_id = %s,
                refunded_at = NOW(),
                completed_at = NOW()
            WHERE id = %s
        """, (refund.id, req_id))
        flash(f"Returned & deposit refunded for {rr['tool_name']}.", "success")
    except stripe.error.StripeError as e:
        exec_write("UPDATE rental_requests SET completed_at = NOW() WHERE id = %s", (req_id,))
        flash(f"Marked returned, but Stripe refund failed: {str(e)}", "danger")
    except Exception as e:
        flash(f"Error processing refund: {str(e)}", "danger")
    return redirect(url_for("owner_active"))

@app.route("/owner/rental_requests/<int:req_id>/approve_cancel", methods=["POST"])
@require_login
def approve_cancel_request(req_id):
    # unchanged...
    uid = session["user_id"]
    rr = dict_getone("""
        SELECT rr.id, rr.status, rr.tool_id, rr.start_date, rr.end_date,
               rr.payment_intent_id, rr.currency,
               rr.rental_cents, rr.deposit_cents,
               rr.refund_id, rr.responded_at, rr.refunded_at,
               t.name AS tool_name, t.owner_id
        FROM rental_requests rr
        JOIN tools t ON t.id = rr.tool_id
        WHERE rr.id = %s
    """, (req_id,))
    if not rr or rr["owner_id"] != uid:
        flash("Not authorized for this rental.", "danger")
        return redirect(url_for("owner_upcoming"))
    if rr["status"] != "cancelled" or rr.get("responded_at"):
        flash("Rental is not awaiting cancellation approval.", "warning")
        return redirect(url_for("owner_upcoming"))
    if rr.get("refund_id") or rr.get("refunded_at"):
        exec_write("UPDATE rental_requests SET responded_at = NOW() WHERE id = %s", (req_id,))
        flash(f"Cancellation approved (refund already processed) for {rr['tool_name']}.", "success")
        return redirect(url_for("owner_upcoming"))
    try:
        pi = rr.get("payment_intent_id")
        if not pi:
            exec_write("UPDATE rental_requests SET responded_at = NOW() WHERE id = %s", (req_id,))
            flash("Cancellation approved, but no payment on file for automatic refund.", "warning")
            return redirect(url_for("owner_upcoming"))
        total_cents = int((rr.get("rental_cents") or 0) + (rr.get("deposit_cents") or 0))
        refund = stripe.Refund.create(
            payment_intent=pi,
            amount=total_cents,
            metadata={
                "rental_request_id": str(rr["id"]),
                "tool_id": str(rr["tool_id"]),
                "reason": "cancellation_approved_by_owner"
            },
            idempotency_key=f"rr-{req_id}-full-refund-v1"
        )
        exec_write("""
            UPDATE rental_requests
            SET responded_at = NOW(),
                refund_id = %s,
                refunded_at = NOW()
            WHERE id = %s
        """, (refund.id, req_id))
        flash(f"Cancellation approved and refunded for {rr['tool_name']}.", "success")
    except stripe.error.StripeError as e:
        flash(f"Stripe refund failed: {str(e)}", "danger")    
    except Exception as e:
        flash(f"Error processing refund: {str(e)}", "danger")
    return redirect(url_for("owner_upcoming"))

# Email notifications & CLI unchanged...
def send_email(to_addr: str, subject: str, body_text: str, from_display: str = None):
    sender = FROM_EMAIL
    if from_display:
        sender = formataddr((from_display, FROM_EMAIL.split("<")[-1].strip(" >"))) if "<" in FROM_EMAIL else formataddr((from_display, FROM_EMAIL))
    msg = MIMEText(body_text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_addr
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
        if SMTP_USE_TLS:
            s.starttls()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

def notification_already_sent(rental_request_id: int, kind: str, start_date):
    row = dict_getone("""
        SELECT id
        FROM notification_log
        WHERE rental_request_id = %s
          AND kind = %s
          AND scheduled_for = %s
        LIMIT 1
    """, (rental_request_id, kind, start_date))
    return bool(row)

def log_notification_sent(rental_request_id: int, kind: str, start_date):
    exec_write("""
        INSERT INTO notification_log (rental_request_id, kind, scheduled_for)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE sent_at = sent_at
    """, (rental_request_id, kind, start_date))

def send_start_reminders_for_tomorrow():
    rows = dict_query("""
        SELECT
            rr.id AS rr_id,
            rr.start_date, rr.end_date, rr.status,
            t.id AS tool_id, t.name AS tool_name,
            ou.id AS owner_id, ou.first_name AS owner_first, ou.last_name AS owner_last, ou.email AS owner_email,
            r.id  AS renter_id, r.first_name  AS renter_first, r.last_name  AS renter_last, r.email  AS renter_email
        FROM rental_requests rr
        JOIN tools t   ON t.id = rr.tool_id
        JOIN users r   ON r.id = rr.renter_id
        JOIN users ou  ON ou.id = t.owner_id
        WHERE rr.status IN ('approved')
          AND rr.start_date = CURDATE() + INTERVAL 1 DAY
    """)
    sent_count = 0
    for row in rows:
        rr_id = row["rr_id"]
        sd = row["start_date"]; ed = row["end_date"]; tool = row["tool_name"]
        if row.get("renter_email") and not notification_already_sent(rr_id, "renter_start", sd):
            renter_name = f'{row.get("renter_first","").strip()} {row.get("renter_last","").strip()}'.strip()
            body = (f"Hi {renter_name or 'there'},\n\n"
                    f"This is a reminder that your rental starts tomorrow.\n\n"
                    f"Tool: {tool}\nStart: {sd}\nEnd:   {ed}\n\n"
                    f"Please coordinate pickup/hand-off with the owner if needed.\n\n— ToolShare")
            try:
                send_email(row["renter_email"], f"Reminder: your {tool} rental starts tomorrow", body, from_display="ToolShare")
                log_notification_sent(rr_id, "renter_start", sd); sent_count += 1
            except Exception as e:
                app.logger.exception(f"Email to renter failed for rr {rr_id}: {e}")
        if row.get("owner_email") and not notification_already_sent(rr_id, "owner_start", sd):
            owner_name = f'{row.get("owner_first","").strip()} {row.get("owner_last","").strip()}'.strip()
            body = (f"Hi {owner_name or 'there'},\n\n"
                    f"Reminder: your tool is scheduled to be rented starting tomorrow.\n\n"
                    f"Tool: {tool}\nStart: {sd}\nEnd:   {ed}\n"
                    f"Renter: {row.get('renter_first','').strip()} {row.get('renter_last','').strip()} ({row.get('renter_email','')})\n\n"
                    f"Ensure the item is ready for pickup/hand-off.\n\n— ToolShare")
            try:
                send_email(row["owner_email"], f"Reminder: {tool} is rented tomorrow", body, from_display="ToolShare")
                log_notification_sent(rr_id, "owner_start", sd); sent_count += 1
            except Exception as e:
                app.logger.exception(f"Email to owner failed for rr {rr_id}: {e}")
    return sent_count

@app.cli.command("send-notifs")
def cli_send_notifs():
    count = send_start_reminders_for_tomorrow()
    click.echo(f"Sent {count} notifications.")

# =========================================================
# Main
# =========================================================
if __name__ == '__main__':
    app.run(debug=True)
