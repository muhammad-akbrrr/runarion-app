#!/bin/bash

# Function to log messages
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if migrations need to be run
check_migrations() {
    if [ ! -f "storage/migrations_ran" ]; then
        log "Running migrations..."
        php artisan migrate:fresh --seed --force || {
            log "Error: Migrations & Seeding failed"
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

# Function to check if Reverb is running
check_reverb() {
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:${REVERB_PORT:-8080} > /dev/null; then
            log "Reverb server is running"
            return 0
        fi
        log "Waiting for Reverb server... (attempt $attempt/$max_attempts)"
        sleep 1
        attempt=$((attempt + 1))
    done
    log "Error: Reverb server failed to start"
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

# Function to start Vite development server with Windows-specific settings
start_vite() {
    log "Starting Vite development server..."
    # Add specific flags for Windows compatibility
    npm run dev -- --host 0.0.0.0 --port ${VITE_PORT:-5173} --strictPort || {
        log "Error: Vite server failed to start"
        exit 1
    }
}

# Function to start Reverb server
start_reverb() {
    log "Starting Reverb WebSocket server..."
    php artisan reverb:start --host=0.0.0.0 --port=${REVERB_PORT:-8080} --debug || {
        log "Error: Reverb server failed to start"
        exit 1
    }
}

# Function to start queue worker
start_queue_worker() {
    log "Starting queue worker..."
    php artisan queue:work --tries=3 --timeout=90 || {
        log "Error: Queue worker failed to start"
        exit 1
    }
}

# Function to handle shutdown
cleanup() {
    log "Shutting down..."
    pkill -f "php artisan serve"
    pkill -f "php artisan reverb:start"
    pkill -f "php artisan queue:work"
    pkill -f "vite"
    exit 0
}

# Set up trap for cleanup
trap cleanup SIGTERM SIGINT

# Set proper permissions
log "Setting proper permissions..."
chown -R www-data:www-data storage bootstrap/cache
chmod -R 777 storage bootstrap/cache

# Check and run migrations if needed
check_migrations

# Start Vite in development mode (background)
start_vite &
VITE_PID=$!

# Start Reverb WebSocket server (background)
start_reverb &
REVERB_PID=$!

# Start queue worker (background)
start_queue_worker &
QUEUE_PID=$!

# Wait for services to be ready
check_vite || exit 1
check_reverb || exit 1

# Start Laravel development server (foreground)
start_development_server
