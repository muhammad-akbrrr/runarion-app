from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import logging
import sys
from psycopg2 import pool
from src.api.generation import generate
from src.api.deconstructor import deconstruct
from src.api.style_analyzer import analyze_style
from src.api.novel_writer import rewrite_novel
from src.api.novel_pipeline_orchestrator import novel_pipeline
from src.api.records import records
from src.api.auditor import auditor
from src.api.advisor import advisor

load_dotenv()

# Configure logging for all modules
log_level_name = os.getenv(
    'APP_LOG_LEVEL',
    'DEBUG' if os.getenv('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes'} else 'INFO'
).upper()
log_level = getattr(logging, log_level_name, logging.INFO)

logging.basicConfig(
    level=log_level,
    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    stream=sys.stdout
)
# Ensure all loggers output to stdout
for handler in logging.root.handlers:
    handler.setLevel(log_level)

app = Flask(__name__)

# Configure max content length for file uploads
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# --- CORS Configuration ---


def parse_allowed_origins():
    raw_origins = os.getenv('CORS_ALLOWED_ORIGINS')
    if not raw_origins:
        return ["http://localhost:8000", "http://localhost:5173"]

    origins = [origin.strip() for origin in raw_origins.split(',') if origin.strip()]
    if not origins:
        return ["http://localhost:8000", "http://localhost:5173"]

    if len(origins) == 1 and origins[0] == '*':
        return '*'

    return origins


cors_allowed_origins = parse_allowed_origins()

CORS(app, resources={
    r"/*": {
        "origins": cors_allowed_origins,
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
    raise EnvironmentError(
        f"Missing environment variables: {', '.join(missing_vars)}")

# --- Database Connection Pool ---

try:
    connection_pool = pool.SimpleConnectionPool(
        minconn=int(os.getenv('DB_POOL_MIN_CONN', '2')),
        maxconn=int(os.getenv('DB_POOL_MAX_CONN', '50')),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_DATABASE'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    app.logger.info("Database connection pool initialized.")

    # Make connection pool available to blueprints
    app.config['connection_pool'] = connection_pool

except Exception as e:
    app.logger.error(f"Database connection pool initialization failed: {e}")
    connection_pool = None
app.config['CONNECTION_POOL'] = connection_pool


# --- Upload Location ---
default_upload_path = os.getenv('UPLOAD_PATH', '/app/uploads')
upload_path = os.getenv('UPLOAD_PATH') or default_upload_path

# Create upload directory if it doesn't exist
os.makedirs(upload_path, exist_ok=True)
app.config['UPLOAD_PATH'] = upload_path


# --- Blueprint Registration ---

app.register_blueprint(generate, url_prefix='/api')
app.register_blueprint(deconstruct, url_prefix='/api')
app.register_blueprint(analyze_style, url_prefix='/api')
app.register_blueprint(rewrite_novel, url_prefix='/api')
app.register_blueprint(novel_pipeline, url_prefix='/api')
app.register_blueprint(records, url_prefix='/api')
app.register_blueprint(auditor, url_prefix='/api')
app.register_blueprint(advisor, url_prefix='/api')

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
        "status": "running",
        "endpoints": {
            "generation": "/api/generate",
            "streaming": "/api/stream",
            "story_deconstructor": "/api/deconstruct",
            "style_analysis": "/api/analyze-style",
            "novel_rewrite": "/api/novel-writer/generate",
            "novel_pipeline": "/api/novel-pipeline/start",
            "health": "/health"
        }
    })

# --- Run Server ---


if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes'}
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
