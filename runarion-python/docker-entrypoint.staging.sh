#!/bin/bash
set -euo pipefail

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

prepare_runtime_dirs() {
    mkdir -p /app/uploads
}

prepare_runtime_dirs

log "Starting Python staging runtime: $*"
exec "$@"

