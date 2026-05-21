FROM postgres:16

# Set environment variables
ENV PG_MAJOR 16
ENV LANG ${LANG:-en_US.utf8}

# Install dependencies needed for building Apache AGE extension
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  postgresql-server-dev-16 \
  libreadline-dev \
  zlib1g-dev \
  flex \
  bison \
  git \
  curl \
  ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Install Apache AGE extension for PostgreSQL 16
RUN set -eux; \
  # Update CA certificates and configure git for HTTPS
  update-ca-certificates; \
  git config --global http.sslverify true; \
  # Clone Apache AGE with retry mechanism
  cd /tmp; \
  for i in 1 2 3; do \
    if git clone -b PG16 --depth 1 https://github.com/apache/age.git; then \
      break; \
    else \
      echo "Git clone attempt $i failed, retrying..."; \
      sleep 5; \
    fi; \
  done; \
  # Verify clone succeeded
  if [ ! -d "age" ]; then \
    echo "Failed to clone Apache AGE repository after 3 attempts"; \
    exit 1; \
  fi; \
  cd age; \
  # Use official AGE build commands per documentation
  make install; \
  cd /; \
  rm -rf /tmp/age; \
  # Clean up build dependencies but keep runtime dependencies
  apt-get purge -y --auto-remove \
  build-essential \
  postgresql-server-dev-16 \
  libreadline-dev \
  zlib1g-dev \
  flex \
  bison \
  git \
  curl \
  ; \
  apt-get autoremove -y; \
  rm -rf /var/lib/apt/lists/*

# Configure PostgreSQL for AGE extension
RUN set -eux; \
  # Check if AGE extension was successfully installed
  if [ -f "/usr/lib/postgresql/16/lib/age.so" ]; then \
    echo "AGE extension found and ready for configuration"; \
    # Create a custom postgresql.conf snippet for AGE
    echo "shared_preload_libraries = 'age'" > /usr/share/postgresql/postgresql.conf.sample.age; \
    echo "AGE extension configured in shared_preload_libraries"; \
  else \
    echo "AGE extension not found, skipping shared_preload_libraries configuration"; \
  fi

# Copy AGE initialization scripts to the official image's init directory
COPY 00-configure-age-settings.sh /docker-entrypoint-initdb.d/
COPY 01-init-age.sql /docker-entrypoint-initdb.d/
COPY 02-init-novel-graph-schema.sql /docker-entrypoint-initdb.d/

# Set proper permissions for init scripts
RUN chmod +x /docker-entrypoint-initdb.d/00-configure-age-settings.sh \
    && chown postgres:postgres /docker-entrypoint-initdb.d/00-configure-age-settings.sh \
    && chown postgres:postgres /docker-entrypoint-initdb.d/01-init-age.sql \
    && chmod 644 /docker-entrypoint-initdb.d/01-init-age.sql \
    && chown postgres:postgres /docker-entrypoint-initdb.d/02-init-novel-graph-schema.sql \
    && chmod 644 /docker-entrypoint-initdb.d/02-init-novel-graph-schema.sql

# Create custom entrypoint script that includes AGE configuration
COPY docker-entrypoint-age.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint-age.sh

# Use custom entrypoint that configures AGE before starting PostgreSQL
ENTRYPOINT ["docker-entrypoint-age.sh"]

# Default command
CMD ["postgres"]