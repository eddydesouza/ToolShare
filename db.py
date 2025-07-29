import mysql.connector
import os
from dotenv import load_dotenv

# Get base dir of the script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')

# Load .env file
load_dotenv(dotenv_path=ENV_PATH)

# Resolve SSL_CA path
ssl_ca_path = os.getenv('SSL_CA')
if ssl_ca_path and not os.path.isabs(ssl_ca_path):
    ssl_ca_path = os.path.join(BASE_DIR, ssl_ca_path)

# Validate the file exists
if ssl_ca_path and not os.path.isfile(ssl_ca_path):
    raise FileNotFoundError(f"SSL CA file not found at: {ssl_ca_path}")

# Build DB config
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'your_username'),
    'password': os.getenv('DB_PASS', 'your_password'),
    'database': os.getenv('DB_NAME', 'artisan_platform'),
    'ssl_ca': ssl_ca_path
}

def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print("MySQL Error:", err)
        raise
