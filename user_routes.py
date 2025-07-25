from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import get_db_connection
import re

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET'])
def profile():
    user_id = request.args.get('user_id')
    if not user_id:
        flash("User ID not provided.", "danger")
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('index'))

    return render_template('profile.html', user=user)


@user_bp.route('/update_profile', methods=['POST'])
def update_profile():
    user_id = request.form.get('user_id')
    email = request.form.get('email', '').strip()
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    phone = request.form.get('phone', '').strip()
    address_line1 = request.form.get('address_line1', '').strip()
    city = request.form.get('city', '').strip()
    state = request.form.get('state', '').strip()
    zip_code = request.form.get('zip_code', '').strip()

    if not user_id or not email or not first_name or not last_name:
        flash("First name, last name, and email are required.", "danger")
        return redirect(url_for('user.profile', user_id=user_id))

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash("Invalid email format.", "danger")
        return redirect(url_for('user.profile', user_id=user_id))

    if phone and not re.match(r"^\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$", phone):
        flash("Invalid phone number format.", "danger")
        return redirect(url_for('user.profile', user_id=user_id))

    if zip_code and not re.match(r"^\d{5}(-\d{4})?$", zip_code):
        flash("Invalid ZIP code format.", "danger")
        return redirect(url_for('user.profile', user_id=user_id))

    if state and not re.match(r"^[A-Z]{2}$", state.upper()):
        flash("State must be a 2-letter abbreviation (e.g., MS, CA).", "danger")
        return redirect(url_for('user.profile', user_id=user_id))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET email=%s, first_name=%s, last_name=%s, phone=%s,
            address_line1=%s, city=%s, state=%s, zip_code=%s
        WHERE id=%s
    """, (email, first_name, last_name, phone, address_line1, city, state.upper(), zip_code, user_id))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Profile updated successfully!", "success")
    return redirect(url_for('user.profile', user_id=user_id))
