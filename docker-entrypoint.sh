#!/usr/bin/env bash
set -Eeo pipefail
# TODO swap to -Eeuo pipefail above (after handling all potentially-unset variables)

#=============================================================================
# Helper Functions
#=============================================================================

# Load environment variables from files
# Usage: file_env VAR [DEFAULT]
# Example: file_env 'XYZ_DB_PASSWORD' 'example'
file_env() {
	local var="$1"
	local fileVar="${var}_FILE"
	local def="${2:-}"
	
	if [ "${!var:-}" ] && [ "${!fileVar:-}" ]; then
		printf >&2 'error: both %s and %s are set (but are exclusive)\n' "$var" "$fileVar"
		exit 1
	fi
	
	local val="$def"
	if [ "${!var:-}" ]; then
		val="${!var}"
	elif [ "${!fileVar:-}" ]; then
		val="$(< "${!fileVar}")"
	fi
	
	export "$var"="$val"
	unset "$fileVar"
}

# Check if script is being sourced
_is_sourced() {
	[ "${#FUNCNAME[@]}" -ge 2 ] \
		&& [ "${FUNCNAME[0]}" = '_is_sourced' ] \
		&& [ "${FUNCNAME[1]}" = 'source' ]
}

#=============================================================================
# Database Directory Management
#=============================================================================

# Create and configure database directories
docker_create_db_directories() {
	local user; user="$(id -u)"

	# Create main data directory
	mkdir -p "$PGDATA"
	# ignore failure since there are cases where we can't chmod (and PostgreSQL might fail later anyhow - it's picky about permissions of this directory)
	chmod 00700 "$PGDATA" || :

	# Create runtime directory
	mkdir -p /var/run/postgresql || :
	chmod 03775 /var/run/postgresql || :

	# Create WAL directory if specified
	if [ -n "${POSTGRES_INITDB_WALDIR:-}" ]; then
		mkdir -p "$POSTGRES_INITDB_WALDIR"
		if [ "$user" = '0' ]; then
			find "$POSTGRES_INITDB_WALDIR" \! -user postgres -exec chown postgres '{}' +
		fi
		chmod 700 "$POSTGRES_INITDB_WALDIR"
	fi

	# allow the container to be started with `--user`
	if [ "$user" = '0' ]; then
		find "$PGDATA" \! -user postgres -exec chown postgres '{}' +
		find /var/run/postgresql \! -user postgres -exec chown postgres '{}' +
	fi
}

#=============================================================================
# Database Initialization
#=============================================================================

# Initialize empty database directory with secure defaults
docker_init_database_dir() {
	# Handle NSS wrapper for user authentication
	local uid; uid="$(id -u)"
	if ! getent passwd "$uid" &> /dev/null; then
		local wrapper
		for wrapper in {/usr,}/lib{/*,}/libnss_wrapper.so; do
			if [ -s "$wrapper" ]; then
				NSS_WRAPPER_PASSWD="$(mktemp)"
				NSS_WRAPPER_GROUP="$(mktemp)"
				export LD_PRELOAD="$wrapper" NSS_WRAPPER_PASSWD NSS_WRAPPER_GROUP
				local gid; gid="$(id -g)"
				printf 'postgres:x:%s:%s:PostgreSQL:%s:/bin/false\n' "$uid" "$gid" "$PGDATA" > "$NSS_WRAPPER_PASSWD"
				printf 'postgres:x:%s:\n' "$gid" > "$NSS_WRAPPER_GROUP"
				break
			fi
		done
	fi

	# Set WAL directory if specified
	if [ -n "${POSTGRES_INITDB_WALDIR:-}" ]; then
		set -- --waldir "$POSTGRES_INITDB_WALDIR" "$@"
	fi

	# Initialize database with secure defaults
	eval 'initdb \
		--username="$POSTGRES_USER" \
		--pwfile=<(printf "%s\n" "$POSTGRES_PASSWORD") \
		--auth=scram-sha-256 \
		--auth-local=scram-sha-256 \
		'"$POSTGRES_INITDB_ARGS"' "$@"'

	# Cleanup NSS wrapper
	if [[ "${LD_PRELOAD:-}" == */libnss_wrapper.so ]]; then
		rm -f "$NSS_WRAPPER_PASSWD" "$NSS_WRAPPER_GROUP"
		unset LD_PRELOAD NSS_WRAPPER_PASSWD NSS_WRAPPER_GROUP
	fi
}

# Verify minimum environment requirements
docker_verify_minimum_env() {
	# Check password length for PostgreSQL 13+
	case "${PG_MAJOR:-}" in
		13)
			if [ "${#POSTGRES_PASSWORD}" -ge 100 ]; then
				cat >&2 <<-'EOWARN'
					WARNING: The supplied POSTGRES_PASSWORD (from DB_PASSWORD) is 100+ characters.
					This will not work if used via PGPASSWORD with "psql".
					See: https://github.com/docker-library/postgres/issues/507
				EOWARN
			fi
			;;
	esac

	# Verify password is set and not using trust authentication
	if [ -z "$POSTGRES_PASSWORD" ] && [ 'trust' != "$POSTGRES_HOST_AUTH_METHOD" ]; then
		cat >&2 <<-'EOE'
			Error: Database is uninitialized and superuser password is not specified.
			You must specify DB_PASSWORD to a non-empty value in your .env file.
			
			For example:
			DB_PASSWORD=your-secure-password
			
			You may also use "POSTGRES_HOST_AUTH_METHOD=trust" to allow all
			connections without a password, but this is *not* recommended for production.
			
			See PostgreSQL documentation about "trust":
			https://www.postgresql.org/docs/current/auth-trust.html
		EOE
		exit 1
	fi

	# Warn about trust authentication
	if [ 'trust' = "$POSTGRES_HOST_AUTH_METHOD" ]; then
		cat >&2 <<-'EOWARN'
			*******************************************************************************
			WARNING: POSTGRES_HOST_AUTH_METHOD has been set to "trust". This will allow
					 anyone with access to the Postgres port to access your database without
					 a password, even if POSTGRES_PASSWORD is set.
					 
					 This is *not* recommended for production use. Please:
					 1. Set POSTGRES_HOST_AUTH_METHOD=scram-sha-256 in your .env file
					 2. Ensure POSTGRES_PASSWORD is set to a strong password
					 3. Use proper authentication for all database connections
					 
					See PostgreSQL documentation about "trust":
					https://www.postgresql.org/docs/current/auth-trust.html
		EOWARN
	fi
}

#=============================================================================
# Database Setup and Configuration
#=============================================================================

# Process initialization files
docker_process_init_files() {
	psql=( docker_process_sql )

	printf '\n'
	local f
	for f; do
		case "$f" in
			*.sh)
				# https://github.com/docker-library/postgres/issues/450#issuecomment-393167936
				# https://github.com/docker-library/postgres/pull/452
				if [ -x "$f" ]; then
					printf '%s: running %s\n' "$0" "$f"
					"$f"
				else
					printf '%s: sourcing %s\n' "$0" "$f"
					. "$f"
				fi
				;;
			*.sql)     printf '%s: running %s\n' "$0" "$f"; docker_process_sql -f "$f"; printf '\n' ;;
			*.sql.gz)  printf '%s: running %s\n' "$0" "$f"; gunzip -c "$f" | docker_process_sql; printf '\n' ;;
			*.sql.xz)  printf '%s: running %s\n' "$0" "$f"; xzcat "$f" | docker_process_sql; printf '\n' ;;
			*.sql.zst) printf '%s: running %s\n' "$0" "$f"; zstd -dc "$f" | docker_process_sql; printf '\n' ;;
			*)         printf '%s: ignoring %s\n' "$0" "$f" ;;
		esac
		printf '\n'
	done
}

# Process SQL commands
docker_process_sql() {
	local query_runner=( psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --no-password --no-psqlrc )
	if [ -n "$POSTGRES_DB" ]; then
		query_runner+=( --dbname "$POSTGRES_DB" )
	fi

	PGHOST= PGHOSTADDR= "${query_runner[@]}" "$@"
}

# Create initial database
docker_setup_db() {
	local dbAlreadyExists
	dbAlreadyExists="$(
		POSTGRES_DB= docker_process_sql --dbname postgres --set db="$POSTGRES_DB" --tuples-only <<-'EOSQL'
			SELECT 1 FROM pg_database WHERE datname = :'db' ;
		EOSQL
	)"
	if [ -z "$dbAlreadyExists" ]; then
		POSTGRES_DB= docker_process_sql --dbname postgres --set db="$POSTGRES_DB" <<-'EOSQL'
			CREATE DATABASE :"db" ;
		EOSQL
		printf '\n'
	fi
}

# Verify Apache AGE extension availability
docker_verify_age_extension() {
	local ageAvailable
	ageAvailable="$(
		docker_process_sql --dbname postgres --tuples-only <<-'EOSQL'
			SELECT 1 FROM pg_available_extensions WHERE name = 'age';
		EOSQL
	)"
	
	if [ -n "$ageAvailable" ]; then
		printf 'Apache AGE extension is available\n'
		return 0
	else
		printf 'WARNING: Apache AGE extension is not available - graph functionality will be disabled\n'
		return 1
	fi
}

#=============================================================================
# Environment Setup
#=============================================================================

# Load environment variables
docker_setup_env() {
	# Load critical database configuration
	file_env 'POSTGRES_PASSWORD' "${DB_PASSWORD:-}"
	file_env 'POSTGRES_USER' "${DB_USER:-postgres}"
	file_env 'POSTGRES_DB' "${DB_DATABASE:-runarion}"
	file_env 'POSTGRES_INITDB_ARGS'
	
	# Set default authentication method to scram-sha-256 for better security
	: "${POSTGRES_HOST_AUTH_METHOD:=${POSTGRES_HOST_AUTH_METHOD:-scram-sha-256}}"
	
	# Check for database existence
	declare -g DATABASE_ALREADY_EXISTS
	: "${DATABASE_ALREADY_EXISTS:=}"
	
	# Verify database directory
	if [ -s "$PGDATA/PG_VERSION" ]; then
		DATABASE_ALREADY_EXISTS='true'
	fi
	
	# Validate critical environment variables
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
}

# Configure pg_hba.conf with secure defaults
pg_setup_hba_conf() {
	if [ "$1" = 'postgres' ]; then
		shift
	fi
	
	# Get the configured encryption method
	local auth
	auth="$(postgres -C password_encryption "$@")"
	: "${POSTGRES_HOST_AUTH_METHOD:=$auth}"
	
	# Ensure we're not using trust authentication
	if [ 'trust' = "$POSTGRES_HOST_AUTH_METHOD" ]; then
		echo >&2 'Warning: Trust authentication is not recommended for production use.'
		echo >&2 'Please set POSTGRES_HOST_AUTH_METHOD=scram-sha-256 in your .env file.'
	fi
	
	{
		printf '\n'
		if [ 'trust' = "$POSTGRES_HOST_AUTH_METHOD" ]; then
			printf '# WARNING: Trust authentication is enabled. This is not recommended for production.\n'
			printf '# See https://www.postgresql.org/docs/17/auth-trust.html\n'
		fi
		
		# Configure host-based authentication
		printf 'host all all all %s\n' "$POSTGRES_HOST_AUTH_METHOD"
		
		# Add local authentication
		printf 'local all all %s\n' "$POSTGRES_HOST_AUTH_METHOD"
	} >> "$PGDATA/pg_hba.conf"
}

#=============================================================================
# Server Management
#=============================================================================

# Start temporary server for initialization
docker_temp_server_start() {
	if [ "$1" = 'postgres' ]; then
		shift
	fi

	# internal start of server in order to allow setup using psql client
	# does not listen on external TCP/IP and waits until start finishes
	set -- "$@" -c listen_addresses='' -p "${PGPORT:-5432}"

	# unset NOTIFY_SOCKET so the temporary server doesn't prematurely notify
	# any process supervisor.
	NOTIFY_SOCKET= \
	PGUSER="${PGUSER:-$POSTGRES_USER}" \
	pg_ctl -D "$PGDATA" \
		-o "$(printf '%q ' "$@")" \
		-w start
}

# Stop temporary server
docker_temp_server_stop() {
	PGUSER="${PGUSER:-postgres}" \
	pg_ctl -D "$PGDATA" -m fast -w stop
}

# check arguments for an option that would cause postgres to stop
# return true if there is one
_pg_want_help() {
	local arg
	for arg; do
		case "$arg" in
			# postgres --help | grep 'then exit'
			# leaving out -C on purpose since it always fails and is unhelpful:
			# postgres: could not access the server configuration file "/var/lib/postgresql/data/postgresql.conf": No such file or directory
			-'?'|--help|--describe-config|-V|--version)
				return 0
				;;
		esac
	done
	return 1
}

#=============================================================================
# Main Entry Point
#=============================================================================

_main() {
	# if first arg looks like a flag, assume we want to run postgres server
	if [ "${1:0:1}" = '-' ]; then
		set -- postgres "$@"
	fi

	if [ "$1" = 'postgres' ] && ! _pg_want_help "$@"; then
		docker_setup_env
		# setup data directories and permissions (when run as root)
		docker_create_db_directories
		if [ "$(id -u)" = '0' ]; then
			# then restart script as postgres user
			exec gosu postgres "$BASH_SOURCE" "$@"
		fi

		# only run initialization on an empty data directory
		if [ -z "$DATABASE_ALREADY_EXISTS" ]; then
			docker_verify_minimum_env

			# check dir permissions to reduce likelihood of half-initialized database
			ls /docker-entrypoint-initdb.d/ > /dev/null

			docker_init_database_dir
			pg_setup_hba_conf "$@"

			# PGPASSWORD is required for psql when authentication is required for 'local' connections via pg_hba.conf and is otherwise harmless
			# e.g. when '--auth=md5' or '--auth-local=md5' is used in POSTGRES_INITDB_ARGS
			export PGPASSWORD="${PGPASSWORD:-$POSTGRES_PASSWORD}"
			docker_temp_server_start "$@"

			docker_setup_db
			docker_verify_age_extension
			docker_process_init_files /docker-entrypoint-initdb.d/*

			docker_temp_server_stop
			unset PGPASSWORD

			cat <<-'EOM'

				PostgreSQL init process complete; ready for start up.

			EOM
		else
			cat <<-'EOM'

				PostgreSQL Database directory appears to contain a database; Skipping initialization

			EOM
		fi
	fi

	exec "$@"
}

if ! _is_sourced; then
	_main "$@"
fi 