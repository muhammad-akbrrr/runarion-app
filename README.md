# Runarion - AI-Powered Novel Generation Pipeline

A revolutionary AI-powered novel generation and enhancement pipeline that transforms basic story concepts into professionally formatted, illustrated books.

## Documentation

1. [Laravel Documentation](./runarion-laravel/README.md)
2. [Python Documentation](./runarion-python/README.md)

## Overview

Runarion is a comprehensive five-phase pipeline that revolutionizes the book creation process:

1. Initial Story Generation
2. Style Building
3. Novel Writing
4. Relationship Analysis
5. PDF Enhancement

Each phase is meticulously designed to maintain quality and consistency while offering extensive customization options.

## Development Instructions

### Environment Setup

- Ensure Docker Engine is running before executing `./dev.sh`
- Check for port conflicts:
  - Laravel: 8000
  - Python: 5000
  - PostgreSQL: 5432
  - Vite: 5173
- Create .env files in the root, Laravel project, and Python project directories
- Replace default database password `@kb4r123` with your own PostgreSQL password
- Development uses bridge network (runarion-network); production uses overlay

### Configuration Management

- Update all .env files with appropriate development/production values
- When modifying .env files, always update .env.example files
- Application service providers are configured in config/app.php

### Container Management

- Hot reload is implemented for both Laravel and Python
- Rebuild containers when:
  - .env files are modified
  - node_modules need rebuilding
  - Some changes might not be caught by watchdog
- Monitor for file permission issues after container restarts
- Adjust memory allocation in .env and docker-compose files if Python container runs out of memory

### Database

- Use pgAdmin or DBeaver (recommended) for database monitoring
- To connect to the database:
  - Ensure container is running
  - Use connection values from Laravel's .env.example file
  - Use your custom PostgreSQL password
  - Test the connection before proceeding

### Routing & Development

- Prevent conflicts between Laravel route system (web.php) and Ziggy routes
- Always use route names when creating routes in web.php
- Update Ziggy routes when adding new routes in web.php
- Keep Laravel and Python models synchronized when making changes
- Migrations, models, and seeder data are controlled through the Laravel app
