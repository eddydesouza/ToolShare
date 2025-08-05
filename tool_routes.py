from flask import Blueprint, render_template, abort
from db import get_db_connection

tool_bp = Blueprint('tool', __name__)

@tool_bp.route('/tool/<int:tool_id>')
def tool_detail(tool_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM tools WHERE id = %s", (tool_id,))
    tool = cursor.fetchone()

    if not tool:
        cursor.close()
        conn.close()
        abort(404)

    cursor.execute("""
        SELECT date, is_available
        FROM tool_availability 
        WHERE tool_id = %s
    """, (tool_id,))
    dates = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('tool_detail.html', tool=tool, dates=dates)
