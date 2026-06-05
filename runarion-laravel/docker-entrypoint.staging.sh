#!/bin/bash
set -euo pipefail

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

sync_frontend_build() {
    local source_dir="/opt/runarion/public-build"
    local target_dir="/srv/public/build"

    if [ ! -f "${source_dir}/manifest.json" ]; then
        log "Missing built frontend manifest at ${source_dir}/manifest.json"
        exit 1
    fi

    mkdir -p "$target_dir"
    find "$target_dir" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    cp -a "${source_dir}/." "$target_dir/"

    if [ ! -f "${target_dir}/manifest.json" ]; then
        log "Failed to publish frontend manifest to ${target_dir}/manifest.json"
        exit 1
    fi
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
sync_frontend_build
warm_laravel_runtime

log "Starting Laravel staging runtime: $*"
exec "$@"
