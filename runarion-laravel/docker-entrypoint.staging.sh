#!/bin/bash
set -euo pipefail

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

fail_if_missing_env() {
    local missing=()

    for var in APP_KEY APP_URL DB_HOST DB_PORT DB_DATABASE DB_USERNAME DB_PASSWORD REDIS_HOST REDIS_PORT REDIS_PASSWORD; do
        if [ -z "${!var:-}" ]; then
            missing+=("$var")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log "Missing required environment variables: ${missing[*]}"
        exit 1
    fi
}

prepare_runtime_dirs() {
    mkdir -p \
        /srv/storage/app/public \
        /srv/storage/framework/cache \
        /srv/storage/framework/sessions \
        /srv/storage/framework/views \
        /srv/storage/logs \
        /srv/bootstrap/cache

    chown -R www-data:www-data /srv/storage /srv/bootstrap/cache
    chmod -R ug+rwx /srv/storage /srv/bootstrap/cache
    ln -sfn ../storage/app/public /srv/public/storage
}

warm_laravel_runtime() {
    find /srv/bootstrap/cache -maxdepth 1 -type f ! -name '.gitignore' -delete
    log "Refreshing Laravel package manifest..."
    php /srv/artisan package:discover --ansi >/dev/null
}

fail_if_missing_env
prepare_runtime_dirs
warm_laravel_runtime

log "Starting Laravel staging runtime: $*"
exec "$@"
