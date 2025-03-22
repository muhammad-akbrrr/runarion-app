#!/bin/bash

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
        "DB_PASSWORD"
        "GEMINI_API_KEY"
        "GOOGLE_API_KEY"
        "OPENAI_API_KEY"
    )

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "Warning: $var is not set. Using default development value."
            case $var in
                "DB_PASSWORD")
                    export DB_PASSWORD="@kb4r123"
                    ;;
                "GEMINI_API_KEY")
                    export GEMINI_API_KEY="your-gemini-api-key-here"
                    ;;
                "GOOGLE_API_KEY")
                    export GOOGLE_API_KEY="your-google-api-key-here"
                    ;;
                "OPENAI_API_KEY")
                    export OPENAI_API_KEY="your-openai-api-key-here"
                    ;;
            esac
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
    # Fix line endings for entrypoint scripts
    if command -v dos2unix >/dev/null 2>&1; then
        echo "Fixing line endings in entrypoint scripts..."
        dos2unix runarion-laravel/docker-entrypoint-dev.sh
        dos2unix runarion-python/docker-entrypoint-dev.sh
    else
        echo "Warning: dos2unix not found. Line endings may not be fixed properly."
    fi
    chmod +x runarion-laravel/docker-entrypoint-dev.sh
    chmod +x runarion-python/docker-entrypoint-dev.sh
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

# Function to setup Laravel
setup_laravel() {
    echo "Setting up Laravel..."
    docker compose -f docker-compose.dev.yml exec laravel-app php artisan key:generate --force
    docker compose -f docker-compose.dev.yml exec laravel-app php artisan migrate --force
    docker compose -f docker-compose.dev.yml exec laravel-app php artisan config:cache
    docker compose -f docker-compose.dev.yml exec laravel-app php artisan route:cache
    docker compose -f docker-compose.dev.yml exec laravel-app php artisan view:cache
}

# Function to install frontend dependencies
install_frontend_deps() {
    echo "Installing frontend dependencies..."
    docker compose -f docker-compose.dev.yml exec laravel-app npm install
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

# Wait for database and setup services
wait_for_db
setup_laravel
install_frontend_deps
set_permissions

echo "Development environment is ready!"
echo "Laravel frontend: http://localhost:8000"
echo "Python service: http://localhost:5000"
echo "Database: localhost:5432"
echo "Vite HMR: http://localhost:5173"

# Show logs
echo "Showing logs (press Ctrl+C to stop)..."
docker compose -f docker-compose.dev.yml logs -f 