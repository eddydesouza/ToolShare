from flask import Blueprint, jsonify
from db import get_db_connection

tool_api = Blueprint('tool_api', __name__)

@tool_api.route('/api/tool_availability/<int:tool_id>')
def api_tool_availability(tool_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT date, is_available FROM tool_availability WHERE tool_id = %s
    """, (tool_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    events = []
    for row in rows:
        events.append({
            'title': 'Available' if row['is_available'] else 'Unavailable',
            'start': row['date'].isoformat(),
            'allDay': True,
            'color': 'green' if row['is_available'] else 'red'
        })

    return jsonify({'events': events})