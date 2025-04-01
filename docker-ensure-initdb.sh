#!/usr/bin/env bash
set -Eeuo pipefail

#=============================================================================
# Script Information
#=============================================================================
#
# This script serves three main purposes:
#
# 1. Example of how to use "docker-entrypoint.sh" to extend/reuse initialization behavior
# 2. Kubernetes "init container" to ensure database directory is initialized
# 3. CI tool to ensure database is fully initialized before use
#

#=============================================================================
# Security Checks
#=============================================================================

# Verify script is not running as root
if [ "$(id -u)" = '0' ]; then
	echo >&2 'Error: This script should not be run as root.'
	echo >&2 'Please run it as the postgres user.'
	exit 1
fi

#=============================================================================
# Source Dependencies
#=============================================================================
source /usr/local/bin/docker-entrypoint.sh

#=============================================================================
# Main Execution
#=============================================================================

# Ensure postgres is the first argument
if [ "$#" -eq 0 ] || [ "$1" != 'postgres' ]; then
	set -- postgres "$@"
fi

# Setup environment and directories
docker_setup_env
docker_create_db_directories

# Initialize database if needed
if [ -z "$DATABASE_ALREADY_EXISTS" ]; then
	# Verify environment variables
	if [ -z "$POSTGRES_PASSWORD" ]; then
		echo >&2 'Error: POSTGRES_PASSWORD is not set. Please set DB_PASSWORD in your .env file.'
		exit 1
	fi
	
	if [ -z "$POSTGRES_USER" ]; then
		echo >&2 'Error: POSTGRES_USER is not set. Please set DB_USER in your .env file.'
		exit 1
	fi
	
	if [ -z "$POSTGRES_DB" ]; then
		echo >&2 'Error: POSTGRES_DB is not set. Please set DB_DATABASE in your .env file.'
		exit 1
	fi
	
	# Verify minimum environment requirements
	docker_verify_minimum_env
	
	# Check initialization directory permissions
	ls /docker-entrypoint-initdb.d/ > /dev/null
	
	# Initialize database with secure defaults
	docker_init_database_dir
	pg_setup_hba_conf "$@"
	
	# Set password for local connections
	export PGPASSWORD="${PGPASSWORD:-$POSTGRES_PASSWORD}"
	
	# Start temporary server
	docker_temp_server_start "$@"
	
	# Setup database and process initialization files
	docker_setup_db
	docker_process_init_files /docker-entrypoint-initdb.d/*
	
	# Stop temporary server
	docker_temp_server_stop
	unset PGPASSWORD
else
	# Handle different script names for different use cases
	self="$(basename "$0")"
	case "$self" in
		docker-ensure-initdb.sh)
			echo >&2 "$self: note: database already initialized in '$PGDATA'!"
			exit 0
			;;
		docker-enforce-initdb.sh)
			echo >&2 "$self: error: (unexpected) database found in '$PGDATA'!"
			exit 1
			;;
		*)
			echo >&2 "$self: error: unknown file name: $self"
			exit 99
			;;
	esac
fi 