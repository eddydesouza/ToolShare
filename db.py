import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'your_username'),
    'password': os.getenv('DB_PASS', 'your_password'),
    'database': os.getenv('DB_NAME', 'artisan_platform'),
    'ssl_ca': os.getenv('SSL_CA')
}

def get_db_connection():
    return mysql.connector.connect(**db_config)
