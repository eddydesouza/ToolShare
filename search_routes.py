# search_routes.py
from flask import Blueprint, request, render_template
from db import get_db_connection

search_bp = Blueprint('search', __name__)

# Set to True if you only want to show tools that are available
ENFORCE_AVAILABLE = True

@search_bp.route('/search', methods=['GET', 'POST'])
def search_tools():
    search_term = None
    selected_category = None
    tools = []
    categories = []

    # Always load categories for the dropdown
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT DISTINCT category 
        FROM tools 
        WHERE category IS NOT NULL AND category <> ''
        ORDER BY category
    """)
    categories = [row['category'] for row in cursor.fetchall()]

    # Handle search/filter
    if request.method == 'POST':
        search_term = (request.form.get('search_term') or '').strip()
        selected_category = (request.form.get('category') or '').strip()

        where_clauses = []
        params = []

        if search_term:
            # Case-insensitive search across name, description, and category
            where_clauses.append("""(
                LOWER(name) LIKE %s OR
                LOWER(description) LIKE %s OR
                LOWER(category) LIKE %s
            )""")
            like = f"%{search_term.lower()}%"
            params.extend([like, like, like])

        if selected_category:
            where_clauses.append("LOWER(category) = %s")
            params.append(selected_category.lower())

        if ENFORCE_AVAILABLE:
            where_clauses.append("is_available = 1")

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ("WHERE is_available = 1" if ENFORCE_AVAILABLE else "")

        query = f"""
            SELECT id, owner_id, name, description, category, daily_price, deposit_amount, is_available
            FROM tools
            {where_sql}
            ORDER BY name
            LIMIT 200
        """

        cursor.execute(query, params)
        tools = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'search.html',
        tools=tools,
        categories=categories,
        selected_category=selected_category,
        search_term=search_term
    )
