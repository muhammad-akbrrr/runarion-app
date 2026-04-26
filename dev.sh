#!/bin/bash

COMPOSE_FILE="docker-compose.dev.yml"

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

urlencode_with_python() {
    local raw="$1"
    local py_bin=""

    if command -v python3 >/dev/null 2>&1; then
        py_bin="python3"
    elif command -v python >/dev/null 2>&1; then
        py_bin="python"
    fi

    if [ -n "$py_bin" ]; then
        DB_PASSWORD_RAW="$raw" "$py_bin" -c "import os, urllib.parse; print(urllib.parse.quote_plus(os.getenv('DB_PASSWORD_RAW', '')))"
        return 0
    fi

    echo "$raw"
    return 1
}

# Set TEST_DATABASE_URL if not set, using URL-encoded password when Python is available
if [ -z "$TEST_DATABASE_URL" ]; then
  ENCODED_DB_PASSWORD=$(urlencode_with_python "${DB_PASSWORD:-}")
  if [ $? -ne 0 ]; then
      echo "Warning: python/python3 not found. TEST_DATABASE_URL password may not be URL-encoded."
  fi
  export TEST_DATABASE_URL="postgresql://${DB_USER:-postgres}:${ENCODED_DB_PASSWORD}@${DB_HOST:-postgres-db}:${DB_PORT:-5432}/${DB_DATABASE:-runarion}"
fi

# Compose wrapper
dc() {
    docker compose -f "$COMPOSE_FILE" "$@"
}

# Timeout helper that does not require GNU timeout
run_with_timeout() {
    local timeout_seconds="$1"
    shift

    if command -v timeout >/dev/null 2>&1; then
        timeout "$timeout_seconds" "$@"
        return $?
    fi

    if command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$timeout_seconds" "$@"
        return $?
    fi

    local tmp_out
    local tmp_err
    local pid
    local start
    local now
    local rc

    tmp_out=$(mktemp)
    tmp_err=$(mktemp)

    (
        "$@" >"$tmp_out" 2>"$tmp_err"
    ) &
    pid=$!
    start=$(date +%s)

    while kill -0 "$pid" 2>/dev/null; do
        now=$(date +%s)
        if [ $((now - start)) -ge "$timeout_seconds" ]; then
            kill "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
            cat "$tmp_out"
            cat "$tmp_err" >&2
            rm -f "$tmp_out" "$tmp_err"
            return 124
        fi
        sleep 1
    done

    wait "$pid"
    rc=$?
    cat "$tmp_out"
    cat "$tmp_err" >&2
    rm -f "$tmp_out" "$tmp_err"
    return $rc
}

# Escape string for SQL literal usage
escape_sql_literal() {
    local value="$1"
    echo "${value//\'/\'\'}"
}

# Run SQL query against postgres container with timeout
run_db_query() {
    local sql="$1"
    local timeout_seconds="${2:-8}"
    local postgres_cid

    postgres_cid=$(dc ps -q postgres-db)
    if [ -z "$postgres_cid" ]; then
        echo "postgres-db container not found" >&2
        return 1
    fi

    run_with_timeout "$timeout_seconds" \
        docker exec -e PGPASSWORD="${DB_PASSWORD}" "$postgres_cid" \
        psql -U "${DB_USER:-postgres}" -d "${DB_DATABASE:-runarion}" -Atqc "$sql"
}

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

        # Apache AGE Configuration
        "AGE_ENABLED"
        "AGE_GRAPH_NAME"

        # API Keys
        "GEMINI_API_KEY"
        "OPENAI_API_KEY"
        "DEEPSEEK_API_KEY"

        # Default Model
        "GEMINI_MODEL_NAME"
        "DEEPSEEK_MODEL_NAME"
        "OPENAI_MODEL_NAME"

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
        "PYTHON_UPLOAD_PATH"

        # Python Testing
        "TEST_DATABASE_URL"

        # Stable Diffusion Settings
        "NVIDIA_VISIBLE_DEVICES"
        "NVIDIA_DRIVER_CAPABILITIES"
        "SD_PYTHONPATH"
        "SD_PYTHONDONTWRITEBYTECODE"
        "SD_PYTHONUNBUFFERED"
        "SD_DIR_PERMISSIONS"

        # Reverb Settings
        "BROADCAST_CONNECTION"
        "REVERB_APP_ID"
        "REVERB_APP_KEY"
        "REVERB_APP_SECRET"
        "REVERB_HOST"
        "REVERB_PORT"
        "REVERB_SCHEME"
        "VITE_REVERB_APP_KEY"
        "VITE_REVERB_HOST"
        "VITE_REVERB_CLIENT_HOST"
        "VITE_REVERB_PORT"
        "VITE_REVERB_SCHEME"

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
                "PG_MAJOR") export PG_MAJOR="16" ;;
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
    local ports=("8000" "5000" "5432" "5173" "8080" "7860")
    for port in "${ports[@]}"; do
        if lsof -i :"$port" > /dev/null 2>&1; then
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
        # dos2unix runarion-stable-diffusion/docker-entrypoint.sh
    else
        echo "Warning: dos2unix not found. Line endings may not be fixed properly."
    fi
    chmod +x docker-entrypoint.sh
    chmod +x docker-ensure-initdb.sh
    chmod +x runarion-laravel/docker-entrypoint.sh
    chmod +x runarion-python/docker-entrypoint.sh
    # chmod +x runarion-stable-diffusion/docker-entrypoint.sh
}

print_postgres_diagnostics() {
    echo "=== PostgreSQL diagnostics (postgres-db) ==="
    dc ps postgres-db || true
    echo
    dc logs --tail 120 postgres-db || true
}

# Function to wait for database to be ready
wait_for_db() {
    echo "Waiting for database to be ready..."

    local max_attempts="${DB_READY_MAX_ATTEMPTS:-120}"
    local attempt=1

    while [ "$attempt" -le "$max_attempts" ]; do
        local postgres_cid
        local health_status

        postgres_cid=$(dc ps -q postgres-db)
        if [ -z "$postgres_cid" ]; then
            echo "Database container not found yet (attempt $attempt/$max_attempts)"
            sleep 1
            attempt=$((attempt + 1))
            continue
        fi

        health_status=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$postgres_cid" 2>/dev/null || echo "unknown")
        if [ "$health_status" = "healthy" ]; then
            echo "Database is ready!"
            return 0
        fi

        echo "Database is not ready yet (status: $health_status, attempt $attempt/$max_attempts)"
        sleep 1
        attempt=$((attempt + 1))
    done

    echo "Error: Database did not become ready in time."
    print_postgres_diagnostics
    return 1
}

# Function to verify Apache AGE extension
check_age_extension() {
    if [ "${AGE_ENABLED:-true}" != "true" ]; then
        echo "Apache AGE extension disabled via AGE_ENABLED=false"
        return 0
    fi

    echo "Verifying Apache AGE extension..."

    local max_attempts="${AGE_VERIFY_MAX_ATTEMPTS:-20}"
    local attempt=1
    local graph_name_escaped
    local timeout_seconds="${AGE_VERIFY_TIMEOUT_SECONDS:-8}"

    graph_name_escaped=$(escape_sql_literal "${AGE_GRAPH_NAME:-novel_pipeline_graph}")

    while [ "$attempt" -le "$max_attempts" ]; do
        local availability
        local installed
        local graph_exists
        local cypher_exists
        local raw

        raw=$(run_db_query "SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'age') THEN 1 ELSE 0 END;" "$timeout_seconds" 2>/dev/null)
        local rc_avail=$?
        availability=$(echo "$raw" | tr -d '[:space:]')

        raw=$(run_db_query "SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'age') THEN 1 ELSE 0 END;" "$timeout_seconds" 2>/dev/null)
        local rc_installed=$?
        installed=$(echo "$raw" | tr -d '[:space:]')

        raw=$(run_db_query "SELECT CASE WHEN to_regnamespace('ag_catalog') IS NULL THEN 0 WHEN EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = '${graph_name_escaped}') THEN 1 ELSE 0 END;" "$timeout_seconds" 2>/dev/null)
        local rc_graph=$?
        graph_exists=$(echo "$raw" | tr -d '[:space:]')

        raw=$(run_db_query "SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'ag_catalog' AND p.proname = 'cypher') THEN 1 ELSE 0 END;" "$timeout_seconds" 2>/dev/null)
        local rc_cypher=$?
        cypher_exists=$(echo "$raw" | tr -d '[:space:]')

        if [ "$rc_avail" -eq 0 ] && [ "$rc_installed" -eq 0 ] && [ "$rc_graph" -eq 0 ] && [ "$rc_cypher" -eq 0 ] \
            && [ "$availability" = "1" ] && [ "$installed" = "1" ] && [ "$graph_exists" = "1" ] && [ "$cypher_exists" = "1" ]; then
            echo "Apache AGE extension verified successfully."
            echo "Graph '${AGE_GRAPH_NAME:-novel_pipeline_graph}' is available and ready."
            return 0
        fi

        echo "AGE verification pending (attempt $attempt/$max_attempts): available=${availability:-n/a}, installed=${installed:-n/a}, graph=${graph_exists:-n/a}, cypher=${cypher_exists:-n/a}"
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "Error: Apache AGE verification failed after $max_attempts attempts."
    echo "AGE is enabled and required for startup."
    echo "Troubleshooting commands:"
    echo "  docker compose -f $COMPOSE_FILE logs --tail 200 postgres-db"
    echo "  docker compose -f $COMPOSE_FILE exec -T postgres-db psql -U ${DB_USER:-postgres} -d ${DB_DATABASE:-runarion} -c \"SELECT * FROM pg_extension WHERE extname = 'age';\""
    echo "  docker compose -f $COMPOSE_FILE exec -T postgres-db psql -U ${DB_USER:-postgres} -d ${DB_DATABASE:-runarion} -c \"SELECT * FROM ag_catalog.ag_graph;\""
    print_postgres_diagnostics
    return 1
}

# Function to wait for Vite server to be ready
wait_for_vite() {
    echo "Waiting for Vite server to be ready..."
    local max_attempts="${VITE_READY_MAX_ATTEMPTS:-30}"
    local attempt=1
    local host_port="${VITE_PORT:-5173}"
    local vite_probe_path="/@vite/client"
    local logs_since
    logs_since=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    while [ "$attempt" -le "$max_attempts" ]; do
        if curl -fsS "http://127.0.0.1:${host_port}${vite_probe_path}" > /dev/null 2>&1; then
            echo "Vite server is ready (host probe)."
            return 0
        fi

        local laravel_cid
        laravel_cid=$(dc ps -q laravel-app)
        if [ -n "$laravel_cid" ]; then
            if run_with_timeout 5 docker exec "$laravel_cid" curl -fsS "http://127.0.0.1:${host_port}${vite_probe_path}" > /dev/null 2>&1; then
                echo "Vite server is ready inside laravel-app (host probe not required)."
                return 0
            fi
        fi

        # Fallback readiness signal from laravel entrypoint logs.
        # This is emitted only after its own internal check_vite() succeeds.
        if dc logs --since "$logs_since" laravel-app 2>&1 | grep -qE "Vite server is running|VITE v[[:space:]]+[0-9]"; then
            echo "Vite server readiness confirmed from laravel-app logs."
            return 0
        fi

        echo "Waiting for Vite server... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "Error: Vite server did not become ready in time"
    dc logs --tail 80 laravel-app || true
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
    while [ "$attempt" -le "$max_attempts" ]; do
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
    chmod -R "${SD_DIR_PERMISSIONS:-755}" runarion-stable-diffusion/{models,outputs,inputs,cache}

    # Create and activate virtual environment if it doesn't exist
    if [ ! -d "runarion-stable-diffusion/venv" ]; then
        echo "Creating virtual environment..."
        cd runarion-stable-diffusion
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            python -m venv venv --clear
        else
            python3 -m venv venv --clear
        fi
        cd ..
    fi

    # Activate virtual environment and install dependencies
    echo "Installing dependencies in virtual environment..."
    cd runarion-stable-diffusion

    # OS-specific virtual environment activation
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # shellcheck disable=SC1091
        source venv/Scripts/activate
    else
        # shellcheck disable=SC1091
        source venv/bin/activate
    fi

    python -m pip install --no-cache-dir huggingface_hub

    # Download models if needed
    ./download_models.sh

    cd ..

    echo "Stable Diffusion setup complete."
}

# Function to setup Laravel
setup_laravel() {
    echo "Setting up Laravel..."

    # Key generation is now handled by docker-compose.dev.yml conditionally
    # to avoid triggering Vite restarts. Only generate if truly missing.
    local has_key
    has_key=$(dc exec -T laravel-app grep -c "APP_KEY=base64:" .env 2>/dev/null || echo "0")
    if [ "$has_key" -eq "0" ]; then
        echo "Generating application key..."
        dc exec -T laravel-app php artisan key:generate --force
    else
        echo "Application key already exists, skipping generation to avoid Vite restart"
    fi

    # Migrations are handled by docker-entrypoint.sh via check_migrations()
    # Only run migrate:fresh if explicitly needed (storage/migrations_ran doesn't exist)
    if dc exec -T laravel-app test ! -f storage/migrations_ran; then
        echo "Running fresh migrations..."
        dc exec -T laravel-app php artisan migrate:fresh --seed --force
    else
        echo "Migrations already ran, skipping to avoid data loss"
    fi

    # Skip caching in development - it causes issues with hot reload
    # These commands are only needed in production
    echo "Skipping cache commands in development mode"
}

# Function to install frontend dependencies
# Note: This is now handled automatically by docker-compose.dev.yml startup command
# This function is only needed if you want to force a rebuild
install_frontend_deps() {
    echo "Installing frontend dependencies..."

    # npm install is already handled by docker-compose.dev.yml conditionally
    # Only force install if explicitly needed
    echo "Note: npm install is handled automatically by container startup"
    echo "If you need to force reinstall, run: docker compose -f $COMPOSE_FILE exec -T laravel-app npm install --legacy-peer-deps"

    # Build assets for production
    echo "Building frontend assets..."
    dc exec -T laravel-app npm run build
}

# Function to set proper permissions
set_permissions() {
    echo "Setting proper permissions..."
    dc exec -T laravel-app chown -R www-data:www-data storage bootstrap/cache
}

# Function to fix storage permissions before Docker build
# This prevents "permission denied" errors when Docker tries to read the build context
fix_storage_permissions() {
    echo "Fixing storage directory permissions for Docker build context..."

    local storage_app_dir="runarion-laravel/storage/app"

    # Check if any directories under storage/app have restrictive permissions
    if [ -d "$storage_app_dir" ]; then
        # Find directories owned by root or with restrictive permissions and fix them
        local problem_dirs
        problem_dirs=$(find "$storage_app_dir" -type d ! -perm -o+rx 2>/dev/null || true)

        if [ -n "$problem_dirs" ]; then
            echo "Found directories with restrictive permissions, fixing..."
            # Use sudo to fix permissions on problematic directories
            sudo chown -R "$USER:$USER" "$storage_app_dir" 2>/dev/null || true
            sudo chmod -R 755 "$storage_app_dir" 2>/dev/null || true
            echo "Storage permissions fixed."
        else
            echo "Storage permissions are OK."
        fi
    else
        echo "Creating storage/app directory structure..."
        mkdir -p "$storage_app_dir"
    fi
}

# Function to cleanup development environment
cleanup() {
    echo "Cleaning up development environment..."
    dc down -v
    rm -f runarion-laravel/storage/migrations_ran
    echo "Cleanup complete!"
}

# Function to handle script interruption
handle_interrupt() {
    echo -e "\nInterrupted by user. Exiting..."
    exit 130
}

run_readiness_checks() {
    wait_for_db || return 1
    check_age_extension || return 1
    wait_for_vite || return 1
    return 0
}

run_common_preflight() {
    check_docker
    check_env_vars
}

start_environment() {
    echo "Starting development environment setup..."
    run_common_preflight
    make_scripts_executable
    check_ports
    # check_gpu
    # setup_stable_diffusion
    fix_storage_permissions

    echo "Building and starting containers..."
    dc up -d --build

    if ! run_readiness_checks; then
        echo "Startup failed during readiness checks."
        exit 1
    fi

    setup_laravel
    set_permissions

    echo "Development environment is ready!"
    echo "Laravel frontend: http://localhost:8000"
    echo "Python service: http://python-app:5000"
    echo "Database: localhost:5432"
    echo "Vite HMR: http://localhost:5173"
    # echo "Stable Diffusion: http://stable-diffusion:7860 (internal network only)"

    echo "Showing logs (press Ctrl+C to stop)..."
    dc logs -f
}

restart_environment() {
    echo "Restarting development environment..."
    run_common_preflight

    dc restart

    if ! run_readiness_checks; then
        echo "Restart failed during readiness checks."
        exit 1
    fi

    echo "Restart complete and all readiness checks passed."
    echo "Laravel frontend: http://localhost:8000"
    echo "Database: localhost:5432"
    echo "Vite HMR: http://localhost:5173"
}

doctor_environment() {
    echo "Running development environment diagnostics..."
    run_common_preflight

    dc ps || true

    if ! dc ps --status running -q postgres-db >/dev/null 2>&1 || [ -z "$(dc ps --status running -q postgres-db)" ]; then
        echo "Error: postgres-db is not running. Start or restart the stack first."
        dc ps postgres-db || true
        exit 1
    fi

    run_readiness_checks
    echo "Doctor check complete: DB, AGE, and Vite are healthy."
}

usage() {
    cat <<USAGE
Usage: ./dev.sh [command]

Commands:
  start    Build and start services, then run readiness checks (default)
  restart  Restart services, then run the same readiness checks
  doctor   Run readiness/diagnostic checks without mutating containers
  cleanup  Stop services and remove volumes
  help     Show this help message
USAGE
}

# Set up trap for script interruption
trap handle_interrupt SIGINT SIGTERM

# Main execution
COMMAND="${1:-start}"

case "$COMMAND" in
    start)
        start_environment
        ;;
    restart)
        restart_environment
        ;;
    doctor)
        doctor_environment
        ;;
    cleanup)
        cleanup
        ;;
    help|-h|--help)
        usage
        ;;
    *)
        echo "Unknown command: $COMMAND"
        usage
        exit 1
        ;;
esac
