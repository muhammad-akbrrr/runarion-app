# PostgreSQL 17.4 Dockerfile
FROM debian:stable-slim

# Set environment variables
ENV PG_MAJOR ${PG_MAJOR:-17}
ENV PG_VERSION ${PG_VERSION:-17.4-1.pgdg120+2}
ENV PATH $PATH:/usr/lib/postgresql/$PG_MAJOR/bin
ENV LANG ${LANG:-en_US.utf8}
ENV PGDATA ${PGDATA:-/var/lib/postgresql/data}

# Create postgres user and group
RUN set -eux; \
  groupadd -r postgres --gid=${POSTGRES_GID:-999}; \
  useradd -r -g postgres --uid=${POSTGRES_UID:-999} --home-dir=/var/lib/postgresql --shell=/bin/bash postgres; \
  install --verbose --directory --owner postgres --group postgres --mode 1777 /var/lib/postgresql

# Install system dependencies
RUN set -ex; \
  apt-get update; \
  apt-get install -y --no-install-recommends \
  gnupg \
  less \
  libnss-wrapper \
  xz-utils \
  zstd \
  curl \
  lsb-release \
  ca-certificates \
  ; \
  rm -rf /var/lib/apt/lists/*

# Install gosu for proper user switching
ENV GOSU_VERSION ${GOSU_VERSION:-1.17}
RUN set -eux; \
  savedAptMark="$(apt-mark showmanual)"; \
  apt-get update; \
  apt-get install -y --no-install-recommends ca-certificates wget; \
  rm -rf /var/lib/apt/lists/*; \
  dpkgArch="$(dpkg --print-architecture | awk -F- '{ print $NF }')"; \
  wget -O /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch"; \
  wget -O /usr/local/bin/gosu.asc "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch.asc"; \
  export GNUPGHOME="$(mktemp -d)"; \
  gpg --batch --keyserver hkps://keys.openpgp.org --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4; \
  gpg --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu; \
  gpgconf --kill all; \
  rm -rf "$GNUPGHOME" /usr/local/bin/gosu.asc; \
  apt-mark auto '.*' > /dev/null; \
  [ -z "$savedAptMark" ] || apt-mark manual $savedAptMark > /dev/null; \
  apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
  chmod +x /usr/local/bin/gosu; \
  gosu --version; \
  gosu nobody true

# Set up locale
RUN set -eux; \
  if [ -f /etc/dpkg/dpkg.cfg.d/docker ]; then \
  grep -q '/usr/share/locale' /etc/dpkg/dpkg.cfg.d/docker; \
  sed -ri '/\/usr\/share\/locale/d' /etc/dpkg/dpkg.cfg.d/docker; \
  ! grep -q '/usr/share/locale' /etc/dpkg/dpkg.cfg.d/docker; \
  fi; \
  apt-get update; apt-get install -y --no-install-recommends locales; rm -rf /var/lib/apt/lists/*; \
  echo 'en_US.UTF-8 UTF-8' >> /etc/locale.gen; \
  locale-gen; \
  locale -a | grep 'en_US.utf8'

# Create initialization directory
RUN mkdir /docker-entrypoint-initdb.d

# Add PostgreSQL repository and install PostgreSQL 17
RUN set -ex; \
  # Add PostgreSQL repository
  mkdir -p /usr/share/keyrings; \
  curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg; \
  echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/postgresql.list; \
  # Install PostgreSQL
  apt-get update; \
  apt-get install -y --no-install-recommends \
  postgresql-common \
  postgresql-$PG_MAJOR \
  postgresql-client-$PG_MAJOR \
  ; \
  rm -rf /var/lib/apt/lists/*; \
  # Configure PostgreSQL
  sed -ri 's/#(create_main_cluster) .*$/\1 = false/' /etc/postgresql-common/createcluster.conf; \
  sed -ri "s!^#?(listen_addresses)\s*=\s*\S+.*!\1 = '*'!" /usr/share/postgresql/$PG_MAJOR/postgresql.conf.sample; \
  grep -F "listen_addresses = '*'" /usr/share/postgresql/$PG_MAJOR/postgresql.conf.sample

# Set up runtime directories
RUN install --verbose --directory --owner postgres --group postgres --mode 3777 /var/run/postgresql
RUN install --verbose --directory --owner postgres --group postgres --mode 1777 "$PGDATA"

# Set up data volume
VOLUME /var/lib/postgresql/data

# Copy entrypoint scripts
COPY docker-entrypoint.sh docker-ensure-initdb.sh /usr/local/bin/
RUN ln -sT docker-ensure-initdb.sh /usr/local/bin/docker-enforce-initdb.sh

# Set entrypoint and default command
ENTRYPOINT ["docker-entrypoint.sh"]

# Configure graceful shutdown
STOPSIGNAL SIGINT

# Expose PostgreSQL port
EXPOSE ${DB_PORT:-5432}

# Start PostgreSQL
CMD ["postgres"]