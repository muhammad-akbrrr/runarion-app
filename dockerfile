FROM debian:stable-slim

# Set environment variables
ENV PG_MAJOR ${PG_MAJOR:-17}
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
  git \
  make \
  gcc \
  build-essential \
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
RUN mkdir -p /docker-entrypoint-initdb.d && \
    chown postgres:postgres /docker-entrypoint-initdb.d && \
    chmod 755 /docker-entrypoint-initdb.d

# Add PostgreSQL repository
RUN set -ex; \
  key='B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8'; \
  export GNUPGHOME="$(mktemp -d)"; \
  mkdir -p /usr/local/share/keyrings/; \
  gpg --batch --keyserver keyserver.ubuntu.com --recv-keys "$key"; \
  gpg --batch --export --armor "$key" > /usr/local/share/keyrings/postgres.gpg.asc; \
  gpgconf --kill all; \
  rm -rf "$GNUPGHOME"

# Install PostgreSQL
RUN set -ex; \
  export PYTHONDONTWRITEBYTECODE=1; \
  dpkgArch="$(dpkg --print-architecture)"; \
  aptRepo="[ signed-by=/usr/local/share/keyrings/postgres.gpg.asc ] http://apt.postgresql.org/pub/repos/apt/ bookworm-pgdg main $PG_MAJOR"; \
  case "$dpkgArch" in \
  amd64 | arm64 | ppc64el | s390x) \
  echo "deb $aptRepo" > /etc/apt/sources.list.d/pgdg.list; \
  apt-get update; \
  ;; \
  *) \
  echo "deb-src $aptRepo" > /etc/apt/sources.list.d/pgdg.list; \
  savedAptMark="$(apt-mark showmanual)"; \
  tempDir="$(mktemp -d)"; \
  cd "$tempDir"; \
  apt-get update; \
  apt-get install -y --no-install-recommends dpkg-dev; \
  echo "deb [ trusted=yes ] file://$tempDir ./" > /etc/apt/sources.list.d/temp.list; \
  _update_repo() { \
  dpkg-scanpackages . > Packages; \
  apt-get -o Acquire::GzipIndexes=false update; \
  }; \
  _update_repo; \
  nproc="$(nproc)"; \
  export DEB_BUILD_OPTIONS="nocheck parallel=$nproc"; \
  apt-get build-dep -y postgresql-common pgdg-keyring; \
  apt-get source --compile postgresql-common pgdg-keyring; \
  _update_repo; \
  apt-get build-dep -y "postgresql-$PG_MAJOR"; \
  apt-get source --compile "postgresql-$PG_MAJOR"; \
  apt-mark showmanual | xargs apt-mark auto > /dev/null; \
  apt-mark manual $savedAptMark; \
  ls -lAFh; \
  _update_repo; \
  grep '^Package: ' Packages; \
  cd /; \
  ;; \
  esac; \
  apt-get install -y --no-install-recommends postgresql-common; \
  sed -ri 's/#(create_main_cluster) .*$/\1 = false/' /etc/postgresql-common/createcluster.conf; \
  apt-get install -y --no-install-recommends "postgresql-$PG_MAJOR"; \
  rm -rf /var/lib/apt/lists/*; \
  if [ -n "$tempDir" ]; then \
  apt-get purge -y --auto-remove; \
  rm -rf "$tempDir" /etc/apt/sources.list.d/temp.list; \
  fi; \
  find /usr -name '*.pyc' -type f -exec bash -c 'for pyc; do dpkg -S "$pyc" &> /dev/null || rm -vf "$pyc"; done' -- '{}' +; \
  postgres --version

# Install Apache AGE extension for PostgreSQL 17
RUN set -eux; \
  apt-get update; \
  apt-get install -y --no-install-recommends \
  postgresql-server-dev-$PG_MAJOR \
  build-essential \
  libreadline-dev \
  zlib1g-dev \
  flex \
  bison \
  curl \
  ; \
  # Update CA certificates and configure git for HTTPS
  update-ca-certificates; \
  git config --global http.sslverify true; \
  # Clone Apache AGE with retry mechanism
  cd /tmp; \
  for i in 1 2 3; do \
    if git clone -b PG17 --depth 1 https://github.com/apache/age.git; then \
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
  apt-get purge -y --auto-remove \
  postgresql-server-dev-$PG_MAJOR \
  git \
  make \
  gcc \
  build-essential \
  libreadline-dev \
  zlib1g-dev \
  flex \
  bison \
  curl \
  ; \
  rm -rf /var/lib/apt/lists/*

# Configure PostgreSQL
RUN set -eux; \
  dpkg-divert --add --rename --divert "/usr/share/postgresql/postgresql.conf.sample.dpkg" "/usr/share/postgresql/$PG_MAJOR/postgresql.conf.sample"; \
  cp -v /usr/share/postgresql/postgresql.conf.sample.dpkg /usr/share/postgresql/postgresql.conf.sample; \
  ln -sv ../postgresql.conf.sample "/usr/share/postgresql/$PG_MAJOR/"; \
  sed -ri "s!^#?(listen_addresses)\s*=\s*\S+.*!\1 = '*'!" /usr/share/postgresql/postgresql.conf.sample; \
  # Only add AGE to shared_preload_libraries if it was successfully installed
  if [ -f "/usr/lib/postgresql/$PG_MAJOR/lib/age.so" ]; then \
    sed -ri "s!^#?(shared_preload_libraries)\s*=.*!\1 = 'age'!" /usr/share/postgresql/postgresql.conf.sample; \
    echo "AGE extension found and added to shared_preload_libraries"; \
  else \
    echo "AGE extension not found, skipping shared_preload_libraries configuration"; \
  fi; \
  grep -F "listen_addresses = '*'" /usr/share/postgresql/postgresql.conf.sample

# Set up runtime directories
RUN install --verbose --directory --owner postgres --group postgres --mode 3777 /var/run/postgresql
RUN install --verbose --directory --owner postgres --group postgres --mode 1777 "$PGDATA"

# Set up data volume
VOLUME /var/lib/postgresql/data

# Copy entrypoint scripts
COPY docker-entrypoint.sh docker-ensure-initdb.sh /usr/local/bin/
RUN ln -sT docker-ensure-initdb.sh /usr/local/bin/docker-enforce-initdb.sh

# Copy AGE initialization script
COPY 01-init-age.sql /docker-entrypoint-initdb.d/
RUN chown postgres:postgres /docker-entrypoint-initdb.d/01-init-age.sql && \
    chmod 644 /docker-entrypoint-initdb.d/01-init-age.sql

# Set entrypoint and default command
ENTRYPOINT ["docker-entrypoint.sh"]

# Configure graceful shutdown
STOPSIGNAL SIGINT

# Expose PostgreSQL port
EXPOSE ${DB_PORT:-5432}

# Start PostgreSQL
CMD ["postgres"]