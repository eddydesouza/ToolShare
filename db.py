import mysql.connector
import os
from dotenv import load_dotenv

# Get base dir of the script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, '.env')

# Load .env file
load_dotenv(dotenv_path=ENV_PATH)

# Build DB config
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'database': os.getenv('DB_NAME'),
    'ssl_ca': os.getenv('SSL_CA')
}

def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as err:
        print("MySQL Error:", err)
        raise
