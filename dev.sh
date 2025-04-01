#!/bin/bash

# Function to load environment variables from .env file
load_env() {
    if [ -f .env ]; then
        echo "Loading environment variables from .env file..."
        while IFS= read -r line; do
            # Skip comments and empty lines
            [[ $line =~ ^#.*$ ]] && continue
            [[ -z $line ]] && continue
            
            # Export the variable
            export "$line"
        done < .env
    else
        echo "Error: .env file not found"
        exit 1
    fi
}

# Load environment variables
load_env

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to check if required environment variables are set
check_env_vars() {
    local required_vars=(
        # Database Configuration
        "DB_HOST"
        "DB_PORT"
        "DB_DATABASE"
        "DB_USER"
        "DB_PASSWORD"
        "POSTGRES_HOST_AUTH_METHOD"
        
        # API Keys
        "GEMINI_API_KEY"
        "GOOGLE_API_KEY"
        "OPENAI_API_KEY"
        
        # Application URLs
        "APP_URL"
        "PYTHON_SERVICE_URL"
        "VITE_SERVICE_URL"
        
        # Service Ports
        "LARAVEL_PORT"
        "PYTHON_PORT"
        "VITE_PORT"
        "VITE_HOST"
        
        # PHP Configuration
        "PHP_CLI_SERVER_WORKERS"
        "BCRYPT_ROUNDS"
        
        # Logging Configuration
        "LOG_DRIVER"
        "LOG_MAX_SIZE"
        "LOG_MAX_FILE"
        
        # Resource Limits
        "LARAVEL_MEMORY_LIMIT"
        "LARAVEL_MEMORY_RESERVATION"
        "PYTHON_MEMORY_LIMIT"
        "PYTHON_MEMORY_RESERVATION"
        "POSTGRES_MEMORY_LIMIT"
        "POSTGRES_MEMORY_RESERVATION"
    )

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "Error: $var is not set. Please set it in your .env file."
            exit 1
        fi
    done
}

# Function to check if ports are available
check_ports() {
    local ports=("8000" "5000" "5432" "5173")
    for port in "${ports[@]}"; do
        if lsof -i :$port > /dev/null 2>&1; then
            echo "Warning: Port $port is already in use. Please free up the port and try again."
            exit 1
        fi
    done
}

# Function to ensure entrypoint scripts are executable
make_scripts_executable() {
    echo "Making entrypoint scripts executable..."
    # Fix line endings for entrypoint scripts and env file
    if command -v dos2unix >/dev/null 2>&1; then
        echo "Fixing line endings in entrypoint scripts and env file..."
        dos2unix docker-entrypoint.sh
        dos2unix docker-ensure-initdb.sh
        dos2unix runarion-laravel/docker-entrypoint.sh
        dos2unix runarion-python/docker-entrypoint.sh
        dos2unix .env
    else
        echo "Warning: dos2unix not found. Line endings may not be fixed properly."
    fi
    chmod +x docker-entrypoint.sh
    chmod +x docker-ensure-initdb.sh
    chmod +x runarion-laravel/docker-entrypoint.sh
    chmod +x runarion-python/docker-entrypoint.sh
}

# Function to wait for database to be ready
wait_for_db() {
    echo "Waiting for database to be ready..."
    until docker compose -f docker-compose.dev.yml exec postgres-db pg_isready -U postgres; do
        echo "Database is unavailable - sleeping"
        sleep 1
    done
    echo "Database is ready!"
}

# Function to wait for Vite server to be ready
wait_for_vite() {
    echo "Waiting for Vite server to be ready..."
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:5173 > /dev/null; then
            echo "Vite server is ready!"
            return 0
        fi
        echo "Waiting for Vite server... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "Warning: Vite server did not become ready in time"
    return 1
}

# Function to setup Laravel
setup_laravel() {
    echo "Setting up Laravel..."
    docker compose -f docker-compose.dev.yml exec laravel-app php artisan key:generate --force
    docker compose -f docker-compose.dev.yml exec laravel-app php artisan migrate:fresh --seed --force
    docker compose -f docker-compose.dev.yml exec laravel-app php artisan config:cache
    docker compose -f docker-compose.dev.yml exec laravel-app php artisan route:cache
    docker compose -f docker-compose.dev.yml exec laravel-app php artisan view:cache
}

# Function to install frontend dependencies
install_frontend_deps() {
    echo "Installing frontend dependencies..."
    docker compose -f docker-compose.dev.yml exec laravel-app npm install --verbose --legacy-peer-deps
    docker compose -f docker-compose.dev.yml exec laravel-app npm run build
}

# Function to set proper permissions
set_permissions() {
    echo "Setting proper permissions..."
    docker compose -f docker-compose.dev.yml exec laravel-app chown -R www-data:www-data storage bootstrap/cache
}

# Function to cleanup development environment
cleanup() {
    echo "Cleaning up development environment..."
    docker compose -f docker-compose.dev.yml down -v
    rm -f runarion-laravel/storage/migrations_ran
    echo "Cleanup complete!"
}

# Function to handle script interruption
handle_interrupt() {
    echo -e "\nInterrupted by user. Cleaning up..."
    cleanup
    exit 1
}

# Set up trap for script interruption
trap handle_interrupt SIGINT SIGTERM

# Main execution
echo "Starting development environment setup..."

# Check prerequisites
check_docker
check_env_vars
check_ports
make_scripts_executable

# Build and start containers
echo "Building and starting containers..."
docker compose -f docker-compose.dev.yml up -d --build

# Wait for services to be ready
wait_for_db
wait_for_vite

# Setup services
setup_laravel
set_permissions

echo "Development environment is ready!"
echo "Laravel frontend: http://localhost:8000"
echo "Python service: http://localhost:5000"
echo "Database: localhost:5432"
echo "Vite HMR: http://localhost:5173"

# Show logs
echo "Showing logs (press Ctrl+C to stop)..."
docker compose -f docker-compose.dev.yml logs -f