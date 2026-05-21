#!/bin/bash
set -e

# Post-initialization configuration for Apache AGE
echo "=== Configuring PostgreSQL for Apache AGE ==="

# Only configure if AGE is enabled
if [ "${AGE_ENABLED:-true}" != "true" ]; then
    echo "AGE_ENABLED is false, skipping configuration"
    exit 0
fi

# Verify AGE library exists
if [ ! -f "/usr/lib/postgresql/16/lib/age.so" ]; then
    echo "WARNING: AGE library not found, skipping configuration"
    exit 0
fi

# Create configuration directory
mkdir -p "$PGDATA/conf.d"

# Write AGE performance settings
cat > "$PGDATA/conf.d/01-age-performance.conf" <<EOF
# Apache AGE Performance Configuration

# Memory settings for graph operations
work_mem = 256MB
maintenance_work_mem = 512MB
shared_buffers = 256MB

# Query planning
random_page_cost = 1.1
effective_cache_size = 1GB
EOF

# Enable conf.d inclusion
if ! grep -q "^include_dir = 'conf.d'" "$PGDATA/postgresql.conf"; then
    echo "include_dir = 'conf.d'" >> "$PGDATA/postgresql.conf"
    echo "Added include_dir directive to postgresql.conf"
fi

echo "AGE configuration complete"
