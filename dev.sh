#!/bin/bash

# Function to load environment variables from .env file
load_env() {
    if [ -f .env ]; then
        echo "Loading environment variables from .env file..."
        # Fix line endings for .env file if dos2unix is available
        if command -v dos2unix >/dev/null 2>&1; then
            dos2unix .env
        fi
        # Use a more robust way to read the .env file
        while IFS='=' read -r key value || [ -n "$key" ]; do
            # Skip comments and empty lines
            [[ $key =~ ^#.*$ ]] && continue
            [[ -z $key ]] && continue
            
            # Remove any carriage returns and trim whitespace
            value=$(echo "$value" | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
            
            # Export the variable if it's not empty
            if [ -n "$value" ]; then
                export "$key=$value"
            fi
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
        # Docker Configuration
        "REGISTRY"
        "TAG"
        "DOCKER_STACK_NAME"
        "DOCKER_COMPOSE_FILE"
        
        # Database Configuration
        "DB_CONNECTION"
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
        "SD_SERVICE_URL"
        
        # Service Ports
        "LARAVEL_PORT"
        "PYTHON_PORT"
        "VITE_PORT"
        "SD_API_PORT"
        
        # Resource Limits
        "LARAVEL_MEMORY_LIMIT"
        "LARAVEL_MEMORY_RESERVATION"
        "PYTHON_MEMORY_LIMIT"
        "PYTHON_MEMORY_RESERVATION"
        "POSTGRES_MEMORY_LIMIT"
        "POSTGRES_MEMORY_RESERVATION"
        
        # Logging Configuration
        "LOG_DRIVER"
        "LOG_MAX_SIZE"
        "LOG_MAX_FILE"
        
        # Development Settings
        "VITE_HOST"
        "VITE_APP_NAME"
        
        # PHP Settings
        "PHP_CLI_SERVER_WORKERS"
        "BCRYPT_ROUNDS"
        
        # Locale Settings
        "APP_LOCALE"
        "APP_FALLBACK_LOCALE"
        "APP_FAKER_LOCALE"
        
        # Node.js Settings
        "NODE_OPTIONS"
        "NPM_CONFIG_CACHE"
        "CHOKIDAR_USEPOLLING"
        "WATCHPACK_POLLING"
        
        # Flask Settings
        "FLASK_ENV"
        "FLASK_DEBUG"
        
        # Python Settings
        "PYTHON_PYTHONPATH"
        "PYTHON_PYTHONDONTWRITEBYTECODE"
        "PYTHON_PYTHONUNBUFFERED"
        
        # Stable Diffusion Settings
        "NVIDIA_VISIBLE_DEVICES"
        "NVIDIA_DRIVER_CAPABILITIES"
        "SD_PYTHONPATH"
        "SD_PYTHONDONTWRITEBYTECODE"
        "SD_PYTHONUNBUFFERED"
        "SD_DIR_PERMISSIONS"
        
        # Network Configuration
        "NETWORK_DRIVER"
        "NETWORK_ATTACHABLE"
        
        # Volume Configuration
        "VOLUME_DRIVER"
    )

    # Optional variables that can be empty
    local optional_vars=(
        # PostgreSQL Advanced Configuration
        "POSTGRES_INITDB_WALDIR"
        "POSTGRES_INITDB_ARGS"
        "PG_MAJOR"
        "PG_VERSION"
        "PGDATA"
        "POSTGRES_GID"
        "POSTGRES_UID"
        "GOSU_VERSION"
        "LANG"
    )

    # Check required variables
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            echo "Error: $var is not set. Please set it in your .env file."
            exit 1
        fi
    done

    # Set default values for optional variables if they're not set
    for var in "${optional_vars[@]}"; do
        if [ -z "${!var}" ]; then
            case $var in
                "POSTGRES_INITDB_WALDIR") export POSTGRES_INITDB_WALDIR="" ;;
                "POSTGRES_INITDB_ARGS") export POSTGRES_INITDB_ARGS="" ;;
                "PG_MAJOR") export PG_MAJOR="17" ;;
                "PG_VERSION") export PG_VERSION="17.4-1.pgdg120+2" ;;
                "PGDATA") export PGDATA="/var/lib/postgresql/data" ;;
                "POSTGRES_GID") export POSTGRES_GID="999" ;;
                "POSTGRES_UID") export POSTGRES_UID="999" ;;
                "GOSU_VERSION") export GOSU_VERSION="1.17" ;;
                "LANG") export LANG="en_US.utf8" ;;
            esac
        fi
    done
}

# Function to check if ports are available
check_ports() {
    local ports=("8000" "5000" "5432" "5173" "7860")
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
        dos2unix .env
        dos2unix docker-entrypoint.sh
        dos2unix docker-ensure-initdb.sh
        dos2unix runarion-laravel/docker-entrypoint.sh
        dos2unix runarion-python/docker-entrypoint.sh
        dos2unix runarion-stable-diffusion/docker-entrypoint.sh
    else
        echo "Warning: dos2unix not found. Line endings may not be fixed properly."
    fi
    chmod +x docker-entrypoint.sh
    chmod +x docker-ensure-initdb.sh
    chmod +x runarion-laravel/docker-entrypoint.sh
    chmod +x runarion-python/docker-entrypoint.sh
    chmod +x runarion-stable-diffusion/docker-entrypoint.sh
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

# Function to check if NVIDIA GPU is available
check_gpu() {
    echo "Checking NVIDIA GPU availability..."
    
    # Test CUDA availability using a test container
    if ! docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi &> /dev/null; then
        echo "Error: CUDA is not properly configured in Docker."
        echo "Please ensure the NVIDIA Container Toolkit is properly installed and configured."
        exit 1
    fi
    
    # Get GPU information from the container
    local gpu_info
    gpu_info=$(docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader)
    
    # Extract memory information (assumes memory is in MiB)
    local gpu_memory
    gpu_memory=$(echo "$gpu_info" | awk -F', ' '{print $2}' | sed 's/ MiB//')
    
    if [ -n "$gpu_memory" ] && [ "$gpu_memory" -lt 8000 ]; then
        echo "Warning: GPU memory is less than 8GB. Stable Diffusion may not perform optimally."
        read -p "Do you want to continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    echo "NVIDIA GPU detected and available in Docker."
    echo "GPU Information:"
    echo "$gpu_info"
}

# Function to wait for Stable Diffusion service to be ready
wait_for_sd() {
    echo "Waiting for Stable Diffusion service to be ready..."
    local max_attempts=60
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        local health_response
        health_response=$(curl -s http://localhost:7860/health)
        
        if echo "$health_response" | grep -q '"status":"healthy"'; then
            echo "Stable Diffusion service is ready and initialized!"
            return 0
        else
            echo "Waiting for Stable Diffusion service to respond... (attempt $attempt/$max_attempts)"
        fi
        sleep 5
        attempt=$((attempt + 1))
    done
    echo "Warning: Stable Diffusion service did not become ready in time"
    echo "Last health check response:"
    curl -s http://localhost:7860/health || echo "No response from health endpoint"
    return 1
}

# Function to download Stable Diffusion model
download_sd_model() {
    local model_dir="runarion-stable-diffusion/models/stable-diffusion-v1-5"
    if [ ! -f "$model_dir/model_index.json" ]; then
        echo "Downloading Stable Diffusion model..."
        cd runarion-stable-diffusion && ./download_models.sh && cd ..
    fi
}

# Function to download ControlNet model
download_controlnet_model() {
    local model_dir="runarion-stable-diffusion/models/controlnet"
    if [ ! -f "$model_dir/model_index.json" ]; then
        echo "Downloading ControlNet model..."
        cd runarion-stable-diffusion && ./download_models.sh && cd ..
    fi
}

# Function to setup Stable Diffusion
setup_stable_diffusion() {
    echo "Setting up Stable Diffusion..."
    
    # Ensure model directories exist
    mkdir -p runarion-stable-diffusion/{models,outputs,inputs,cache}
    
    # Set proper permissions
    chmod -R ${SD_DIR_PERMISSIONS:-755} runarion-stable-diffusion/{models,outputs,inputs,cache}
    
    # Create and activate virtual environment if it doesn't exist
    if [ ! -d "runarion-stable-diffusion/venv" ]; then
        echo "Creating virtual environment..."
        cd runarion-stable-diffusion && python3 -m venv venv --clear && cd ..
    fi
    
    # Activate virtual environment and install dependencies
    echo "Installing dependencies in virtual environment..."
    cd runarion-stable-diffusion
    source venv/Scripts/activate
    python -m pip install --no-cache-dir huggingface_hub
    
    # Download models if needed
    ./download_models.sh
    
    cd ..
    
    echo "Stable Diffusion setup complete."
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
check_gpu
make_scripts_executable

# Setup Stable Diffusion
setup_stable_diffusion

# Build and start containers
echo "Building and starting containers..."
docker compose -f docker-compose.dev.yml up -d --build

# Wait for services to be ready
wait_for_db
wait_for_vite
wait_for_sd

# Setup services
setup_laravel
set_permissions

echo "Development environment is ready!"
echo "Laravel frontend: http://localhost:8000"
echo "Python service: http://localhost:5000"
echo "Database: localhost:5432"
echo "Vite HMR: http://localhost:5173"
echo "Stable Diffusion: http://stable-diffusion:7860 (internal network only)"

# Show logs
echo "Showing logs (press Ctrl+C to stop)..."
docker compose -f docker-compose.dev.yml logs -f