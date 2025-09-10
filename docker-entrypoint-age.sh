#!/usr/bin/env bash
set -Eeo pipefail

# Custom entrypoint for PostgreSQL with Apache AGE extension
# This script configures AGE extension before starting PostgreSQL

echo "Starting PostgreSQL with Apache AGE configuration..."

# Check if AGE extension is available
if [ -f "/usr/lib/postgresql/16/lib/age.so" ]; then
    echo "Apache AGE extension found, configuring shared_preload_libraries..."
    
    # Set environment variable to include AGE in shared_preload_libraries
    # This will be picked up by PostgreSQL during initialization
    if [ -z "$POSTGRES_SHARED_PRELOAD_LIBRARIES" ]; then
        export POSTGRES_SHARED_PRELOAD_LIBRARIES="age"
        echo "Set shared_preload_libraries to 'age'"
    else
        # If already set, append AGE to existing libraries
        if [[ ! "$POSTGRES_SHARED_PRELOAD_LIBRARIES" == *"age"* ]]; then
            export POSTGRES_SHARED_PRELOAD_LIBRARIES="${POSTGRES_SHARED_PRELOAD_LIBRARIES},age"
            echo "Added 'age' to existing shared_preload_libraries: $POSTGRES_SHARED_PRELOAD_LIBRARIES"
        fi
    fi
    
    # Create persistent AGE configuration
    if [ "$1" = 'postgres' ]; then
        # Create configuration directory if it doesn't exist
        mkdir -p /var/lib/postgresql/data/conf.d
        
        # Write AGE configuration that will be loaded by PostgreSQL
        cat > /var/lib/postgresql/data/conf.d/01-age.conf << EOF
# Apache AGE Extension Configuration
shared_preload_libraries = '${POSTGRES_SHARED_PRELOAD_LIBRARIES}'

# AGE-specific settings for better performance
max_connections = 200
work_mem = 256MB
maintenance_work_mem = 512MB

# Logging for troubleshooting AGE issues
log_statement = 'ddl'
log_min_duration_statement = 1000
EOF
        
        echo "Apache AGE configuration written to /var/lib/postgresql/data/conf.d/01-age.conf"
        
        # Ensure PostgreSQL will load our configuration
        echo "include_dir = 'conf.d'" >> /var/lib/postgresql/data/postgresql.conf || true
        
        # Set environment variable for the init script
        export POSTGRES_SHARED_PRELOAD_LIBRARIES="${POSTGRES_SHARED_PRELOAD_LIBRARIES}"
        
        echo "AGE configuration will be loaded at PostgreSQL startup"
    fi
else
    echo "Apache AGE extension not found at /usr/lib/postgresql/16/lib/age.so"
    echo "PostgreSQL will start without AGE extension"
fi

# Create AGE health check script
cat > /usr/local/bin/age-health-check.sh << 'EOF'
#!/bin/bash
# AGE Health Check Script

echo "Checking Apache AGE availability..."

# Wait for PostgreSQL to be ready
until pg_isready -U postgres; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
done

# Check if AGE extension exists and is loadable
psql -U postgres -d postgres -c "
DO \$\$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'age') THEN
        RAISE NOTICE 'AGE extension is available';
        CREATE EXTENSION IF NOT EXISTS age;
        LOAD 'age';
        SELECT ag_catalog.create_graph('age_health_test');
        SELECT ag_catalog.drop_graph('age_health_test', true);
        RAISE NOTICE 'AGE health check: PASSED';
    ELSE
        RAISE WARNING 'AGE extension not available - running in fallback mode';
    END IF;
EXCEPTION 
    WHEN OTHERS THEN
        RAISE WARNING 'AGE health check failed: %, running in fallback mode', SQLERRM;
END
\$\$;
" 2>/dev/null || echo "AGE health check failed, but PostgreSQL is running"

echo "AGE health check completed"
EOF

chmod +x /usr/local/bin/age-health-check.sh

# Debug: Show what we're about to execute
echo "Executing: docker-entrypoint.sh $@"

# Call the original PostgreSQL entrypoint with all arguments
exec docker-entrypoint.sh "$@"