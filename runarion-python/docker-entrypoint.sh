#!/bin/bash

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if Flask is running
check_flask() {
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:5000/health > /dev/null; then
            log "Flask server is running"
            return 0
        fi
        log "Waiting for Flask server... (attempt $attempt/$max_attempts)"
        sleep 1
        attempt=$((attempt + 1))
    done
    log "Error: Flask server failed to start"
    return 1
}

# Function to start the Flask application
start_flask() {
    log "Starting Flask application..."
    # Set Flask environment variables
    export FLASK_APP=src/app.py
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    export PYTHONUNBUFFERED=1
    export PYTHONDONTWRITEBYTECODE=1
    
    # Run Flask directly with python instead of using flask CLI
    python src/app.py || {
        log "Error: Flask application failed to start"
        exit 1
    }
}

# Function to handle shutdown
cleanup() {
    log "Shutting down..."
    pkill -f "python -m flask run" 2>/dev/null
    exit 0
}

# Set up trap for cleanup
trap cleanup SIGTERM SIGINT

# Main execution
log "Starting development environment setup..."

# Start the Flask application
start_flask 