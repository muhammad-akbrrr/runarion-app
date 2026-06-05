#!/bin/bash

set -euo pipefail

COMPOSE_FILE="docker-compose.staging.yml"
ENV_FILE="${STAGING_ENV_FILE:-.env.staging}"
OPS_PROFILE="ops"
STACK_SERVICES=(postgres-db redis laravel-php laravel-queue laravel-reverb python-app caddy)
BUILD_SERVICES=(postgres-db laravel-php python-app caddy)

trim_whitespace() {
    echo "$1" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//'
}

public_origin() {
    local https_port="${STAGING_HTTPS_PORT:-443}"
    local origin="https://${STAGING_DOMAIN}"

    if [ "$https_port" != "443" ]; then
        origin="${origin}:${https_port}"
    fi

    echo "$origin"
}

load_env() {
    if [ ! -f "$ENV_FILE" ]; then
        echo "Error: staging env file '$ENV_FILE' was not found."
        echo "Create it first, for example:"
        echo "  cp .env.staging.example .env.staging"
        exit 1
    fi

    while IFS='=' read -r key value || [ -n "$key" ]; do
        [[ $key =~ ^#.*$ ]] && continue
        [[ -z $key ]] && continue

        value=$(echo "$value" | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        export "$key=$value"
    done < "$ENV_FILE"
}

dc() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

dc_ops() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" --profile "$OPS_PROFILE" "$@"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
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

    "$@"
}

check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo "Docker is not running. Start Docker and try again."
        exit 1
    fi
}

check_env_vars() {
    local required_vars=(
        REGISTRY
        TAG
        STAGING_HTTP_PORT
        STAGING_HTTPS_PORT
        STAGING_DOMAIN
        APP_ENV
        APP_DEBUG
        APP_KEY
        DB_CONNECTION
        DB_PORT
        DB_DATABASE
        DB_USER
        DB_PASSWORD
        AGE_REF
        AGE_ENABLED
        AGE_GRAPH_NAME
        REDIS_PORT
        REDIS_PASSWORD
        SESSION_DOMAIN
        SESSION_SECURE_COOKIE
        REVERB_APP_ID
        REVERB_APP_KEY
        REVERB_APP_SECRET
        REVERB_HOSTNAME
        VITE_REVERB_APP_KEY
        VITE_REVERB_CLIENT_HOST
        VITE_REVERB_SCHEME
        PYTHON_SERVICE_URL
        OPENAI_API_KEY
        OPENAI_MODEL_NAME
        GEMINI_API_KEY
        GEMINI_MODEL_NAME
        DEEPSEEK_API_KEY
        DEEPSEEK_MODEL_NAME
    )

    local var
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            echo "Error: $var is not set in $ENV_FILE."
            exit 1
        fi
    done
}

normalize_origin_csv() {
    local csv="$1"
    local derived_origin="$2"
    local base_origin="https://${STAGING_DOMAIN}"
    local value
    local normalized=()

    IFS=',' read -ra values <<< "$csv"
    for value in "${values[@]}"; do
        value="$(trim_whitespace "$value")"
        [ -z "$value" ] && continue

        case "$value" in
            "$base_origin")
                normalized+=("$derived_origin")
                ;;
            *)
                normalized+=("$value")
                ;;
        esac
    done

    local joined=""
    for value in "${normalized[@]}"; do
        if [ -n "$joined" ]; then
            joined="${joined},${value}"
        else
            joined="$value"
        fi
    done

    echo "$joined"
}

derive_runtime_env() {
    local derived_origin
    derived_origin="$(public_origin)"

    export APP_URL="$derived_origin"
    export VITE_REVERB_PORT="${STAGING_HTTPS_PORT}"

    if [ -n "${CORS_ALLOWED_ORIGINS:-}" ]; then
        export CORS_ALLOWED_ORIGINS
        CORS_ALLOWED_ORIGINS="$(normalize_origin_csv "${CORS_ALLOWED_ORIGINS}" "$derived_origin")"
    else
        export CORS_ALLOWED_ORIGINS="$derived_origin"
    fi

    if [ -n "${REVERB_ALLOWED_ORIGINS:-}" ]; then
        export REVERB_ALLOWED_ORIGINS
        REVERB_ALLOWED_ORIGINS="$(normalize_origin_csv "${REVERB_ALLOWED_ORIGINS}" "$derived_origin")"
    else
        export REVERB_ALLOWED_ORIGINS="$derived_origin"
    fi
}

contains_csv_value() {
    local csv="$1"
    local expected="$2"
    local value

    IFS=',' read -ra values <<< "$csv"
    for value in "${values[@]}"; do
        value="$(trim_whitespace "$value")"
        if [ "$value" = "$expected" ]; then
            return 0
        fi
    done

    return 1
}

assert_real_staging_values() {
    local critical_vars=(
        STAGING_DOMAIN
        APP_URL
        APP_KEY
        DB_PASSWORD
        AGE_REF
        REDIS_PASSWORD
        REVERB_APP_ID
        REVERB_APP_KEY
        REVERB_APP_SECRET
        VITE_REVERB_APP_KEY
        OPENAI_API_KEY
        GEMINI_API_KEY
        DEEPSEEK_API_KEY
    )

    local var
    for var in "${critical_vars[@]}"; do
        case "${!var:-}" in
            ""|replace-me|replace-with-*|*runarion.example.com*|*example.com*)
                echo "Error: $var still looks like a placeholder in $ENV_FILE."
                exit 1
                ;;
        esac
    done
}

assert_staging_contract() {
    local expected_public_origin
    expected_public_origin="$(public_origin)"

    if [ "${APP_ENV}" != "staging" ]; then
        echo "Error: APP_ENV must be 'staging' in $ENV_FILE."
        exit 1
    fi

    case "${APP_DEBUG,,}" in
        false|0|no)
            ;;
        *)
            echo "Error: APP_DEBUG must be false in $ENV_FILE."
            exit 1
            ;;
    esac

    if [ "${APP_URL}" != "${expected_public_origin}" ]; then
        echo "Error: APP_URL must match ${expected_public_origin} in $ENV_FILE."
        exit 1
    fi

    if [ "${SESSION_DOMAIN}" != "${STAGING_DOMAIN}" ]; then
        echo "Error: SESSION_DOMAIN must match STAGING_DOMAIN in $ENV_FILE."
        exit 1
    fi

    case "${SESSION_SECURE_COOKIE,,}" in
        true|1|yes)
            ;;
        *)
            echo "Error: SESSION_SECURE_COOKIE must be true in $ENV_FILE."
            exit 1
            ;;
    esac

    if [ "${REVERB_HOSTNAME}" != "${STAGING_DOMAIN}" ]; then
        echo "Error: REVERB_HOSTNAME must match STAGING_DOMAIN in $ENV_FILE."
        exit 1
    fi

    if [ "${VITE_REVERB_CLIENT_HOST}" != "${STAGING_DOMAIN}" ]; then
        echo "Error: VITE_REVERB_CLIENT_HOST must match STAGING_DOMAIN in $ENV_FILE."
        exit 1
    fi

    if [ "${VITE_REVERB_PORT}" != "${STAGING_HTTPS_PORT}" ]; then
        echo "Error: VITE_REVERB_PORT must match STAGING_HTTPS_PORT in $ENV_FILE."
        exit 1
    fi

    if [ "${VITE_REVERB_SCHEME}" != "https" ]; then
        echo "Error: VITE_REVERB_SCHEME must be https in $ENV_FILE."
        exit 1
    fi

    if [ "${PYTHON_SERVICE_URL}" != "http://python-app:5000" ]; then
        echo "Error: PYTHON_SERVICE_URL must point to the internal python-app service in $ENV_FILE."
        exit 1
    fi

    if [ "${STAGING_HTTP_PORT}" = "${STAGING_HTTPS_PORT}" ]; then
        echo "Error: STAGING_HTTP_PORT and STAGING_HTTPS_PORT must be different values in $ENV_FILE."
        exit 1
    fi

    case "${REVERB_ALLOWED_ORIGINS}" in
        *'*'*|*localhost*)
            echo "Error: REVERB_ALLOWED_ORIGINS must not use wildcard or localhost values in $ENV_FILE."
            exit 1
            ;;
    esac

    if ! contains_csv_value "${REVERB_ALLOWED_ORIGINS}" "${expected_public_origin}"; then
        echo "Error: REVERB_ALLOWED_ORIGINS must include ${expected_public_origin} in $ENV_FILE."
        exit 1
    fi

    case "${CORS_ALLOWED_ORIGINS}" in
        *'*'*|*localhost*)
            echo "Error: CORS_ALLOWED_ORIGINS must not use wildcard or localhost values in $ENV_FILE."
            exit 1
            ;;
    esac

    if ! contains_csv_value "${CORS_ALLOWED_ORIGINS}" "${expected_public_origin}"; then
        echo "Error: CORS_ALLOWED_ORIGINS must include ${expected_public_origin} in $ENV_FILE."
        exit 1
    fi
}

normalize_line_endings() {
    if ! command_exists dos2unix; then
        return 0
    fi

    dos2unix "$ENV_FILE" >/dev/null 2>&1 || true
    dos2unix staging.sh >/dev/null 2>&1 || true
    dos2unix runarion-laravel/docker-entrypoint.staging.sh >/dev/null 2>&1 || true
    dos2unix runarion-python/docker-entrypoint.staging.sh >/dev/null 2>&1 || true
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
    local caddy_cid
    caddy_cid="$(dc ps -q caddy 2>/dev/null || true)"

    if [ -n "$caddy_cid" ]; then
        return 0
    fi

    local ports=("${STAGING_HTTP_PORT}" "${STAGING_HTTPS_PORT}")
    local port
    for port in "${ports[@]}"; do
        if port_in_use "$port"; then
            echo "Error: port $port is already in use."
            exit 1
        fi
    done
}

run_static_preflight() {
    load_env
    derive_runtime_env
    check_env_vars
    assert_staging_contract
    normalize_line_endings
    dc config >/dev/null
}

run_common_preflight() {
    run_static_preflight
    check_docker
}

get_container_id() {
    dc ps -q "$1"
}

wait_for_service_healthy() {
    local service="$1"
    local max_attempts="${2:-60}"
    local attempt=1

    echo "Waiting for $service to become healthy..."

    while [ "$attempt" -le "$max_attempts" ]; do
        local cid
        local status

        cid="$(get_container_id "$service")"
        if [ -z "$cid" ]; then
            echo "$service container not found yet (attempt $attempt/$max_attempts)"
            sleep 2
            attempt=$((attempt + 1))
            continue
        fi

        status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || echo "unknown")"
        if [ "$status" = "healthy" ]; then
            echo "$service is healthy."
            return 0
        fi

        echo "$service is not ready yet (status: $status, attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "Error: $service did not become healthy in time."
    dc logs --tail 80 "$service" || true
    return 1
}

run_db_query() {
    local sql="$1"
    local timeout_seconds="${2:-8}"
    local postgres_cid

    postgres_cid="$(get_container_id postgres-db)"
    if [ -z "$postgres_cid" ]; then
        echo "postgres-db container not found" >&2
        return 1
    fi

    run_with_timeout "$timeout_seconds" \
        docker exec -e PGPASSWORD="${DB_PASSWORD}" "$postgres_cid" \
        psql -U "${DB_USER}" -d "${DB_DATABASE}" -Atqc "$sql"
}

check_age_extension() {
    if [ "${AGE_ENABLED:-true}" != "true" ]; then
        echo "Apache AGE is disabled via AGE_ENABLED=false"
        return 0
    fi

    echo "Verifying Apache AGE..."

    local graph_name_escaped
    graph_name_escaped="${AGE_GRAPH_NAME//\'/\'\'}"

    local availability
    local installed
    local graph_exists
    local cypher_exists

    availability="$(run_db_query "SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'age') THEN 1 ELSE 0 END;" 8 2>/dev/null | tr -d '[:space:]')"
    installed="$(run_db_query "SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'age') THEN 1 ELSE 0 END;" 8 2>/dev/null | tr -d '[:space:]')"
    graph_exists="$(run_db_query "SELECT CASE WHEN to_regnamespace('ag_catalog') IS NULL THEN 0 WHEN EXISTS (SELECT 1 FROM ag_catalog.ag_graph WHERE name = '${graph_name_escaped}') THEN 1 ELSE 0 END;" 8 2>/dev/null | tr -d '[:space:]')"
    cypher_exists="$(run_db_query "SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE n.nspname = 'ag_catalog' AND p.proname = 'cypher') THEN 1 ELSE 0 END;" 8 2>/dev/null | tr -d '[:space:]')"

    if [ "$availability" = "1" ] && [ "$installed" = "1" ] && [ "$graph_exists" = "1" ] && [ "$cypher_exists" = "1" ]; then
        echo "Apache AGE is installed and graph '${AGE_GRAPH_NAME}' is ready."
        return 0
    fi

    echo "Error: AGE verification failed."
    echo "available=${availability:-n/a} installed=${installed:-n/a} graph=${graph_exists:-n/a} cypher=${cypher_exists:-n/a}"
    dc logs --tail 120 postgres-db || true
    return 1
}

run_migrations() {
    echo "Running staging migrations..."
    dc_ops run --build --rm laravel-migrate
}

build_environment_images() {
    echo "Building staging images..."
    dc build "${BUILD_SERVICES[@]}"
}

wait_for_python() {
    wait_for_service_healthy python-app 60
}

wait_for_laravel_php() {
    wait_for_service_healthy laravel-php 60
}

wait_for_edge_http_redirect() {
    local max_attempts="${1:-40}"
    local attempt=1

    echo "Waiting for HTTP to HTTPS redirect on ${STAGING_DOMAIN}:${STAGING_HTTP_PORT}..."

    while [ "$attempt" -le "$max_attempts" ]; do
        local headers
        headers="$(curl -sSI --resolve "${STAGING_DOMAIN}:${STAGING_HTTP_PORT}:127.0.0.1" "http://${STAGING_DOMAIN}:${STAGING_HTTP_PORT}/up" || true)"

        if echo "$headers" | grep -qiE '^location: https://'; then
            echo "HTTP redirect is working."
            return 0
        fi

        echo "HTTP redirect not ready yet (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "Error: HTTP redirect did not become ready."
    dc logs --tail 80 caddy || true
    return 1
}

wait_for_https_up() {
    local max_attempts="${1:-60}"
    local attempt=1

    echo "Waiting for HTTPS health endpoint on ${STAGING_DOMAIN}:${STAGING_HTTPS_PORT}..."

    while [ "$attempt" -le "$max_attempts" ]; do
        if curl -kfsS --resolve "${STAGING_DOMAIN}:${STAGING_HTTPS_PORT}:127.0.0.1" "https://${STAGING_DOMAIN}:${STAGING_HTTPS_PORT}/up" >/dev/null 2>&1; then
            echo "HTTPS health endpoint is reachable."
            return 0
        fi

        echo "HTTPS endpoint not ready yet (attempt $attempt/$max_attempts)"
        sleep 3
        attempt=$((attempt + 1))
    done

    echo "Error: HTTPS health endpoint did not become ready."
    dc logs --tail 120 caddy laravel-php || true
    return 1
}

verify_frontend_assets() {
    local homepage
    local asset_path
    local asset_headers
    local asset_status
    local asset_type

    echo "Verifying staged frontend assets..."

    homepage="$(curl -kfsS --resolve "${STAGING_DOMAIN}:${STAGING_HTTPS_PORT}:127.0.0.1" "https://${STAGING_DOMAIN}:${STAGING_HTTPS_PORT}/" || true)"
    if [ -z "$homepage" ]; then
        echo "Error: Failed to fetch staging homepage."
        dc logs --tail 120 caddy laravel-php || true
        return 1
    fi

    asset_path="$(printf '%s' "$homepage" | grep -oE '/build/assets/[^"]+\.js' | head -n 1 || true)"
    if [ -z "$asset_path" ]; then
        echo "Error: No built JavaScript asset reference was found in the staging homepage."
        dc logs --tail 120 caddy laravel-php || true
        return 1
    fi

    asset_headers="$(curl -ksSI --resolve "${STAGING_DOMAIN}:${STAGING_HTTPS_PORT}:127.0.0.1" "https://${STAGING_DOMAIN}:${STAGING_HTTPS_PORT}${asset_path}" || true)"
    asset_status="$(printf '%s\n' "$asset_headers" | awk 'toupper($1) ~ /^HTTP\// {code=$2} END {print code}')"
    asset_type="$(printf '%s\n' "$asset_headers" | awk -F': ' 'tolower($1) == "content-type" {print tolower($2)}' | tail -n 1 | tr -d '\r')"

    if [ "$asset_status" != "200" ]; then
        echo "Error: Frontend asset ${asset_path} returned HTTP ${asset_status:-unknown}."
        dc logs --tail 120 caddy laravel-php || true
        return 1
    fi

    if ! printf '%s' "$asset_type" | grep -q "javascript"; then
        echo "Error: Frontend asset ${asset_path} returned unexpected Content-Type '${asset_type:-missing}'."
        dc logs --tail 120 caddy laravel-php || true
        return 1
    fi

    echo "Frontend assets are reachable with a JavaScript MIME type."
}

run_readiness_checks() {
    wait_for_service_healthy postgres-db 60 || return 1
    wait_for_service_healthy redis 60 || return 1
    check_age_extension || return 1
    wait_for_laravel_php || return 1
    wait_for_python || return 1
    wait_for_edge_http_redirect 40 || return 1
    wait_for_https_up 60 || return 1
    verify_frontend_assets || return 1
    return 0
}

start_environment() {
    echo "Starting staging environment..."
    run_common_preflight
    assert_real_staging_values
    check_ports

    build_environment_images
    dc up -d --no-build "${STACK_SERVICES[@]}"
    run_migrations

    if ! run_readiness_checks; then
        echo "Staging startup failed during readiness checks."
        exit 1
    fi

    echo "Staging environment is ready."
    echo "App URL: ${APP_URL}"
    echo "Use './staging.sh logs' to follow logs."
}

restart_environment() {
    echo "Restarting staging environment..."
    run_common_preflight
    assert_real_staging_values

    dc restart "${STACK_SERVICES[@]}"
    run_migrations

    if ! run_readiness_checks; then
        echo "Staging restart failed during readiness checks."
        exit 1
    fi

    echo "Staging restart complete."
}

doctor_environment() {
    echo "Running staging diagnostics..."
    run_common_preflight
    assert_real_staging_values

    dc ps || true
    run_readiness_checks
    echo "Doctor check complete: Postgres, Redis, AGE, Laravel, Python, and edge routing are healthy."
}

status_environment() {
    run_common_preflight
    dc ps
}

logs_environment() {
    run_common_preflight

    if [ $# -gt 0 ]; then
        dc logs -f "$1"
        return 0
    fi

    dc logs -f
}

stop_environment() {
    echo "Stopping staging environment..."
    run_common_preflight
    dc stop
}

cleanup_environment() {
    echo "Cleaning up staging containers and networks (preserving volumes)..."
    run_common_preflight
    dc down --remove-orphans
}

config_environment() {
    run_static_preflight
    dc config
}

usage() {
    cat <<USAGE
Usage: ./staging.sh [command] [service]

Commands:
  start    Build and start staging services, run migrations, then run readiness checks
  restart  Restart existing staging containers without rebuilding images, rerun migrations, then rerun readiness checks
  doctor   Run readiness and diagnostic checks without changing containers
  migrate  Run 'php artisan migrate --force' via the staging ops profile
  status   Show container status for the staging stack
  logs     Follow logs for the whole stack or one service
  stop     Stop staging services
  cleanup  Remove staging containers and networks but keep volumes
  config   Render the resolved Docker Compose config for staging
  help     Show this help message

Environment:
  STAGING_ENV_FILE  Override the env file path (default: .env.staging)

Examples:
  ./staging.sh start
  ./staging.sh doctor
  ./staging.sh logs caddy
  STAGING_ENV_FILE=.env.staging.example ./staging.sh config
USAGE
}

handle_interrupt() {
    echo
    echo "Interrupted. Exiting."
    exit 130
}

trap handle_interrupt SIGINT SIGTERM

COMMAND="${1:-start}"
SERVICE="${2:-}"

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
    migrate)
        run_common_preflight
        assert_real_staging_values
        run_migrations
        ;;
    status)
        status_environment
        ;;
    logs)
        logs_environment "$SERVICE"
        ;;
    stop)
        stop_environment
        ;;
    cleanup)
        cleanup_environment
        ;;
    config)
        config_environment
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
