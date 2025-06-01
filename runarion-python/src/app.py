from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2 import pool
from api.generation import generate

# Load environment variables from .env
load_dotenv()

# --- App Initialization ---
app = Flask(__name__)

# --- CORS Configuration ---
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:8000", "http://localhost:5173"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# --- Environment Validation ---
REQUIRED_ENV_VARS = [
    'DB_HOST', 'DB_PORT', 'DB_DATABASE', 'DB_USER', 'DB_PASSWORD',
    'OPENAI_API_KEY', 'OPENAI_MODEL_NAME',
    'GEMINI_API_KEY', 'GEMINI_MODEL_NAME',
    'DEEPSEEK_API_KEY', 'DEEPSEEK_MODEL_NAME'
]

missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Missing environment variables: {', '.join(missing_vars)}")

# --- Database Connection Pool ---
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_DATABASE'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    app.logger.info("Database connection pool initialized.")
except Exception as e:
    app.logger.error(f"Database connection pool initialization failed: {e}")
    connection_pool = None

# --- Blueprint Registration ---
app.register_blueprint(generate, url_prefix='/api')

# --- Health Check ---
@app.route('/health', methods=['GET'])
def health_check():
    db_status = "connected"

    if connection_pool:
        try:
            conn = connection_pool.getconn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            connection_pool.putconn(conn)
        except Exception as e:
            app.logger.error(f"Database health check failed: {e}")
            db_status = f"error: {str(e)}"
    else:
        db_status = "not configured"

    return jsonify({
        "status": "healthy",
        "service": "runarion-python",
        "database": db_status
    })

# --- Root Endpoint ---
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "service": "Runarion Python API",
        "status": "running"
    })

# --- Run Server ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
