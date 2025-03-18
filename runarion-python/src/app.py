from flask import Flask, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import pool

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:8000", "http://localhost:5173"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST', 'postgres-db'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'runarion'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '@kb4r123')
}

# Create connection pool
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )
    app.logger.info("Database connection pool created successfully")
except Exception as e:
    app.logger.error(f"Error creating database connection pool: {e}")
    connection_pool = None


@app.route('/health', methods=['GET'])
def health_check():
    db_status = "connected"

    # Check database connection
    if connection_pool:
        try:
            conn = connection_pool.getconn()
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            connection_pool.putconn(conn)
        except Exception as e:
            app.logger.error(f"Database connection error: {e}")
            db_status = f"error: {str(e)}"
    else:
        db_status = "not configured"

    return jsonify({
        "status": "healthy",
        "service": "runarion-python",
        "database": db_status
    })


@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "Runarion Python API",
        "status": "running"
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
