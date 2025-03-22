#!/bin/bash

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to start the Flask application
start_flask() {
    log "Starting Flask application..."
    python src/app.py || {
        log "Error: Flask application failed to start"
        exit 1
    }
}

# Function to handle file changes
handle_changes() {
    log "Changes detected, restarting Flask application..."
    if pkill -f "python src/app.py"; then
        log "Successfully stopped previous Flask instance"
    else
        log "No previous Flask instance found"
    fi
    start_flask
}

# Function to check if watchdog is installed
check_watchdog() {
    if ! command -v watchdog &> /dev/null; then
        log "Installing watchdog..."
        pip install watchdog || {
            log "Error: Failed to install watchdog"
            exit 1
        }
    fi
}

# Main execution
log "Starting development environment setup..."

# Check for watchdog
check_watchdog

# Start the initial Flask application
start_flask

# Start watchdog in the background with error handling
watchdog -p "src/**/*.py" -e "*.pyc,__pycache__" -r handle_changes &
WATCHDOG_PID=$!

# Function to handle shutdown
cleanup() {
    log "Shutting down..."
    kill $WATCHDOG_PID 2>/dev/null
    pkill -f "python src/app.py" 2>/dev/null
    exit 0
}

# Set up trap for cleanup
trap cleanup SIGTERM SIGINT

# Keep the container running and monitor watchdog
while kill -0 $WATCHDOG_PID 2>/dev/null; do
    sleep 1
done

log "Watchdog process died unexpectedly"
exit 1 