#!/usr/bin/env bash
set -Eeo pipefail

# Minimal entrypoint wrapper for PostgreSQL with Apache AGE extension
echo "Starting PostgreSQL with Apache AGE configuration..."

# Check if AGE extension is available
if [ -f "/usr/lib/postgresql/16/lib/age.so" ]; then
    echo "Apache AGE extension found at /usr/lib/postgresql/16/lib/age.so"

    # Set shared_preload_libraries via environment variable
    if [ -z "$POSTGRES_SHARED_PRELOAD_LIBRARIES" ]; then
        export POSTGRES_SHARED_PRELOAD_LIBRARIES="age"
        echo "Set POSTGRES_SHARED_PRELOAD_LIBRARIES='age'"
    else
        # Append AGE if not already present
        if [[ ! "$POSTGRES_SHARED_PRELOAD_LIBRARIES" == *"age"* ]]; then
            export POSTGRES_SHARED_PRELOAD_LIBRARIES="${POSTGRES_SHARED_PRELOAD_LIBRARIES},age"
            echo "Appended 'age' to POSTGRES_SHARED_PRELOAD_LIBRARIES"
        fi
    fi
else
    echo "WARNING: Apache AGE extension not found"
    echo "PostgreSQL will start without AGE extension"
fi

# Delegate to official PostgreSQL entrypoint immediately
# No file creation - let postgres handle initialization
echo "Delegating to official PostgreSQL entrypoint..."
exec docker-entrypoint.sh "$@"
