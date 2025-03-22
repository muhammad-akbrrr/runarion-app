#!/bin/bash

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if migrations need to be run
check_migrations() {
    if [ ! -f "storage/migrations_ran" ]; then
        log "Running migrations..."
        php artisan migrate --force || {
            log "Error: Migrations failed"
            exit 1
        }
        touch storage/migrations_ran
    fi
}

# Function to check if Vite is running
check_vite() {
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:${VITE_PORT:-5173} > /dev/null; then
            log "Vite server is running"
            return 0
        fi
        log "Waiting for Vite server... (attempt $attempt/$max_attempts)"
        sleep 1
        attempt=$((attempt + 1))
    done
    log "Error: Vite server failed to start"
    return 1
}

# Function to start the development server
start_development_server() {
    log "Starting Laravel development server..."
    php artisan serve --host=0.0.0.0 --port=8000 || {
        log "Error: Laravel server failed to start"
        exit 1
    }
}

# Function to start Vite development server
start_vite() {
    log "Starting Vite development server..."
    npm run dev || {
        log "Error: Vite server failed to start"
        exit 1
    }
}

# Function to handle shutdown
cleanup() {
    log "Shutting down..."
    pkill -f "php artisan serve"
    pkill -f "vite"
    exit 0
}

# Set up trap for cleanup
trap cleanup SIGTERM SIGINT

# Set proper permissions
log "Setting proper permissions..."
chown -R www-data:www-data storage bootstrap/cache

# Check and run migrations if needed
check_migrations

# Start Vite in development mode (background)
start_vite &
VITE_PID=$!

# Wait for Vite to be ready
check_vite || exit 1

# Start Laravel development server
start_development_server 