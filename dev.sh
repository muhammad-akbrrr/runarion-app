#!/bin/bash

set -euo pipefail

COMPOSE_FILE="docker-compose.dev.yml"
ENV_FILE=".env"

REQUIRED_ENV_VARS=(
    REGISTRY
    TAG
    DOCKER_STACK_NAME
    DOCKER_COMPOSE_FILE
    DB_CONNECTION
    DB_HOST
    DB_PORT
    DB_DATABASE
    DB_USER
    DB_PASSWORD
    POSTGRES_HOST_AUTH_METHOD
    AGE_ENABLED
    AGE_GRAPH_NAME
    GEMINI_API_KEY
    OPENAI_API_KEY
    DEEPSEEK_API_KEY
    GEMINI_MODEL_NAME
    DEEPSEEK_MODEL_NAME
    OPENAI_MODEL_NAME
    APP_URL
    PYTHON_SERVICE_URL
    VITE_SERVICE_URL
    SD_SERVICE_URL
    LARAVEL_PORT
    PYTHON_PORT
    VITE_PORT
    SD_API_PORT
    LARAVEL_MEMORY_LIMIT
    LARAVEL_MEMORY_RESERVATION
    PYTHON_MEMORY_LIMIT
    PYTHON_MEMORY_RESERVATION
    POSTGRES_MEMORY_LIMIT
    POSTGRES_MEMORY_RESERVATION
    LOG_DRIVER
    LOG_MAX_SIZE
    LOG_MAX_FILE
    VITE_HOST
    VITE_APP_NAME
    PHP_CLI_SERVER_WORKERS
    BCRYPT_ROUNDS
    APP_LOCALE
    APP_FALLBACK_LOCALE
    APP_FAKER_LOCALE
    NODE_OPTIONS
    NPM_CONFIG_CACHE
    CHOKIDAR_USEPOLLING
    WATCHPACK_POLLING
    FLASK_ENV
    FLASK_DEBUG
    PYTHON_PYTHONPATH
    PYTHON_PYTHONDONTWRITEBYTECODE
    PYTHON_PYTHONUNBUFFERED
    PYTHON_UPLOAD_PATH
    TEST_DATABASE_URL
    NVIDIA_VISIBLE_DEVICES
    NVIDIA_DRIVER_CAPABILITIES
    SD_PYTHONPATH
    SD_PYTHONDONTWRITEBYTECODE
    SD_PYTHONUNBUFFERED
    SD_DIR_PERMISSIONS
    BROADCAST_CONNECTION
    REVERB_APP_ID
    REVERB_APP_KEY
    REVERB_APP_SECRET
    REVERB_HOST
    REVERB_PORT
    REVERB_SCHEME
    VITE_REVERB_APP_KEY
    VITE_REVERB_HOST
    VITE_REVERB_CLIENT_HOST
    VITE_REVERB_PORT
    VITE_REVERB_SCHEME
    NETWORK_DRIVER
    NETWORK_ATTACHABLE
    VOLUME_DRIVER
)

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

load_env() {
    if [ ! -f "$ENV_FILE" ]; then
        echo "Error: $ENV_FILE file not found"
        exit 1
    fi

    echo "Loading environment variables from $ENV_FILE..."

    if command_exists dos2unix; then
        dos2unix "$ENV_FILE" >/dev/null 2>&1 || true
    fi

    while IFS='=' read -r key value || [ -n "$key" ]; do
        [[ $key =~ ^#.*$ ]] && continue
        [[ -z $key ]] && continue

        value=$(echo "$value" | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        [ -n "$value" ] && export "$key=$value"
    done < "$ENV_FILE"
}

detect_python_bin() {
    if command_exists python3; then
        echo "python3"
        return 0
    fi

    if command_exists python; then
        echo "python"
        return 0
    fi

    return 1
}

ensure_test_database_url() {
    if [ -n "${TEST_DATABASE_URL:-}" ]; then
        return 0
    fi

    local py_bin encoded_password
    py_bin="$(detect_python_bin || true)"

    if [ -n "$py_bin" ]; then
        encoded_password="$(DB_PASSWORD_RAW="${DB_PASSWORD:-}" "$py_bin" -c "import os, urllib.parse; print(urllib.parse.quote_plus(os.getenv('DB_PASSWORD_RAW', '')))")"
    else
        echo "Warning: python/python3 not found. TEST_DATABASE_URL password may not be URL-encoded."
        encoded_password="${DB_PASSWORD:-}"
    fi

    export TEST_DATABASE_URL="postgresql://${DB_USER:-postgres}:${encoded_password}@${DB_HOST:-postgres-db}:${DB_PORT:-5432}/${DB_DATABASE:-runarion}"
}

dc() {
    docker compose -f "$COMPOSE_FILE" "$@"
}

run_with_timeout() {
    local timeout_seconds="$1"
    shift

    if command_exists timeout; then
        timeout "$timeout_seconds" "$@"
        return $?
    fi

    if command_exists gtimeout; then
        gtimeout "$timeout_seconds" "$@"
        return $?
    fi

    local tmp_out tmp_err pid start now rc

    tmp_out="$(mktemp)"
    tmp_err="$(mktemp)"

    (
        "$@" >"$tmp_out" 2>"$tmp_err"
    ) &
    pid=$!
    start="$(date +%s)"

    while kill -0 "$pid" 2>/dev/null; do
        now="$(date +%s)"
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
    return "$rc"
}

escape_sql_literal() {
    local value="$1"
    echo "${value//\'/\'\'}"
}

get_service_container_id() {
    dc ps -q "$1"
}

run_db_query() {
    local sql="$1"
    local timeout_seconds="${2:-8}"
    local postgres_cid

    postgres_cid="$(get_service_container_id postgres-db)"
    if [ -z "$postgres_cid" ]; then
        echo "postgres-db container not found" >&2
        return 1
    fi

    run_with_timeout "$timeout_seconds" \
        docker exec -e PGPASSWORD="${DB_PASSWORD}" "$postgres_cid" \
        psql -U "${DB_USER:-postgres}" -d "${DB_DATABASE:-runarion}" -Atqc "$sql"
}

check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

check_env_vars() {
    local var

    for var in "${REQUIRED_ENV_VARS[@]}"; do
        if [ -z "${!var:-}" ]; then
            echo "Error: $var is not set. Please set it in your .env file."
            exit 1
        fi
    done

    export POSTGRES_INITDB_WALDIR="${POSTGRES_INITDB_WALDIR:-}"
    export POSTGRES_INITDB_ARGS="${POSTGRES_INITDB_ARGS:-}"
    export PG_MAJOR="${PG_MAJOR:-16}"
    export PGDATA="${PGDATA:-/var/lib/postgresql/data}"
    export POSTGRES_GID="${POSTGRES_GID:-999}"
    export POSTGRES_UID="${POSTGRES_UID:-999}"
    export GOSU_VERSION="${GOSU_VERSION:-1.17}"
    export LANG="${LANG:-en_US.utf8}"
}

port_in_use() {
    local port="$1"

    if command_exists lsof; then
        lsof -i :"$port" >/dev/null 2>&1
        return $?
    fi

    if command_exists ss; then
        ss -ltn "( sport = :$port )" 2>/dev/null | tail -n +2 | grep -q .
        return $?
    fi

    return 1
}

check_ports() {
    local ports=(8000 5000 5432 5173 8080 7860)
    local port

    for port in "${ports[@]}"; do
        if port_in_use "$port"; then
            echo "Warning: Port $port is already in use. Please free up the port and try again."
            exit 1
        fi
    done
}

normalize_dev_files() {
    local files=(
        "$ENV_FILE"
        "docker-entrypoint.sh"
        "docker-ensure-initdb.sh"
        "runarion-laravel/docker-entrypoint.sh"
        "runarion-python/docker-entrypoint.sh"
    )

    echo "Making entrypoint scripts executable..."

    if command_exists dos2unix; then
        echo "Fixing line endings in entrypoint scripts and env file..."
        dos2unix "${files[@]}" >/dev/null 2>&1 || true
    else
        echo "Warning: dos2unix not found. Line endings may not be fixed properly."
    fi

    chmod +x \
        docker-entrypoint.sh \
        docker-ensure-initdb.sh \
        runarion-laravel/docker-entrypoint.sh \
        runarion-python/docker-entrypoint.sh
}

fix_storage_permissions() {
    local storage_app_dir="runarion-laravel/storage/app"
    local problem_dirs=""

    echo "Fixing storage directory permissions for Docker build context..."

    if [ ! -d "$storage_app_dir" ]; then
        echo "Creating storage/app directory structure..."
        mkdir -p "$storage_app_dir"
        return 0
    fi

    problem_dirs="$(find "$storage_app_dir" -type d ! -perm -o+rx 2>/dev/null || true)"
    if [ -z "$problem_dirs" ]; then
        echo "Storage permissions are OK."
        return 0
    fi

    echo "Found directories with restrictive permissions, fixing..."
    sudo chown -R "$USER:$USER" "$storage_app_dir" 2>/dev/null || true
    sudo chmod -R 755 "$storage_app_dir" 2>/dev/null || true
    echo "Storage permissions fixed."
}

set_permissions() {
    echo "Setting proper permissions..."
    dc exec -T laravel-app chown -R www-data:www-data storage bootstrap/cache
}

print_postgres_diagnostics() {
    echo "=== PostgreSQL diagnostics (postgres-db) ==="
    dc ps postgres-db || true
    echo
    dc logs --tail 120 postgres-db || true
}

wait_for_db() {
    local max_attempts="${DB_READY_MAX_ATTEMPTS:-120}"
    local attempt=1

    echo "Waiting for database to be ready..."

    while [ "$attempt" -le "$max_attempts" ]; do
        local postgres_cid health_status

        postgres_cid="$(get_service_container_id postgres-db)"
        if [ -z "$postgres_cid" ]; then
            echo "Database container not found yet (attempt $attempt/$max_attempts)"
            sleep 1
            attempt=$((attempt + 1))
            continue
        fi

        health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$postgres_cid" 2>/dev/null || echo "unknown")"
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

check_age_extension() {
    local max_attempts="${AGE_VERIFY_MAX_ATTEMPTS:-20}"
    local timeout_seconds="${AGE_VERIFY_TIMEOUT_SECONDS:-8}"
    local attempt=1
    local graph_name_escaped

    if [ "${AGE_ENABLED:-true}" != "true" ]; then
        echo "Apache AGE extension disabled via AGE_ENABLED=false"
        return 0
    fi

    echo "Verifying Apache AGE extension..."
    graph_name_escaped="$(escape_sql_literal "${AGE_GRAPH_NAME:-novel_pipeline_graph}")"

    while [ "$attempt" -le "$max_attempts" ]; do
        local raw availability installed graph_exists cypher_exists
        local rc_avail rc_installed rc_graph rc_cypher

        raw="$(run_db_query "SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'age') THEN 1 ELSE 0 END;" "$timeout_seconds" 2>/dev/null || true)"
        rc_avail=$?
        availability="$(echo "$raw" | tr -d '[:space:]')"

        raw="$(run_db_query "SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'age') THEN 1 ELSE 0 END;" "$timeout_seconds" 2>/dev/null || true)"
        rc_installed=$?
        installed="$(echo "$raw" | tr -d '[:space:]')"

        raw="$(run_db_query "SELECT CASE WHEN to_regnamespace('ag_catalog') IS NULL THEN 0 WHEN EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = '${graph_name_escaped}') THEN 1 ELSE 0 END;" "$timeout_seconds" 2>/dev/null || true)"
        rc_graph=$?
        graph_exists="$(echo "$raw" | tr -d '[:space:]')"

        raw="$(run_db_query "SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'ag_catalog' AND p.proname = 'cypher') THEN 1 ELSE 0 END;" "$timeout_seconds" 2>/dev/null || true)"
        rc_cypher=$?
        cypher_exists="$(echo "$raw" | tr -d '[:space:]')"

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

wait_for_vite() {
    local max_attempts="${VITE_READY_MAX_ATTEMPTS:-30}"
    local attempt=1
    local host_port="${VITE_PORT:-5173}"
    local vite_probe_path="/@vite/client"
    local logs_since laravel_cid

    echo "Waiting for Vite server to be ready..."
    logs_since="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

    while [ "$attempt" -le "$max_attempts" ]; do
        if curl -fsS "http://127.0.0.1:${host_port}${vite_probe_path}" >/dev/null 2>&1; then
            echo "Vite server is ready (host probe)."
            return 0
        fi

        laravel_cid="$(get_service_container_id laravel-app)"
        if [ -n "$laravel_cid" ] && run_with_timeout 5 docker exec "$laravel_cid" curl -fsS "http://127.0.0.1:${host_port}${vite_probe_path}" >/dev/null 2>&1; then
            echo "Vite server is ready inside laravel-app (host probe not required)."
            return 0
        fi

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

setup_laravel() {
    local has_key

    echo "Setting up Laravel..."

    has_key="$(dc exec -T laravel-app grep -c "APP_KEY=base64:" .env 2>/dev/null || echo "0")"
    if [ "$has_key" -eq "0" ]; then
        echo "Generating application key..."
        dc exec -T laravel-app php artisan key:generate --force
    else
        echo "Application key already exists, skipping generation to avoid Vite restart"
    fi

    if dc exec -T laravel-app test ! -f storage/migrations_ran; then
        echo "Running fresh migrations..."
        dc exec -T laravel-app php artisan migrate:fresh --seed --force
    else
        echo "Migrations already ran, skipping to avoid data loss"
    fi

    echo "Skipping cache commands in development mode"
}

cleanup_environment() {
    echo "Cleaning up development environment..."
    dc down -v
    rm -f runarion-laravel/storage/migrations_ran
    echo "Cleanup complete!"
}

handle_interrupt() {
    echo
    echo "Interrupted by user. Exiting..."
    exit 130
}

run_readiness_checks() {
    wait_for_db || return 1
    check_age_extension || return 1
    wait_for_vite || return 1
    return 0
}

run_common_preflight() {
    load_env
    ensure_test_database_url
    check_docker
    check_env_vars
}

print_ready_urls() {
    echo "Development environment is ready!"
    echo "Laravel frontend: http://localhost:8000"
    echo "Python service: http://python-app:5000"
    echo "Database: localhost:5432"
    echo "Vite HMR: http://localhost:5173"
}

start_environment() {
    echo "Starting development environment setup..."
    run_common_preflight
    normalize_dev_files
    check_ports
    fix_storage_permissions

    echo "Building and starting containers..."
    dc up -d --build

    if ! run_readiness_checks; then
        echo "Startup failed during readiness checks."
        exit 1
    fi

    setup_laravel
    set_permissions
    print_ready_urls

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

    if [ -z "$(dc ps --status running -q postgres-db)" ]; then
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

trap handle_interrupt SIGINT SIGTERM

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
        run_common_preflight
        cleanup_environment
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
