# Runarion - AI-Powered Novel Generation Pipeline

A revolutionary AI-powered novel generation and enhancement pipeline that transforms basic story concepts into professionally formatted, illustrated books.

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Initial Setup](#initial-setup)
  - [Laravel Setup](#laravel-setup)
  - [Python Setup](#python-setup)
- [Development](#development)
  - [Docker Development](#docker-development)
  - [Port Management](#port-management)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Overview

Runarion is a comprehensive five-phase pipeline that revolutionizes the book creation process:

1. Initial Story Generation
2. Style Building
3. Novel Writing
4. Relationship Analysis
5. PDF Enhancement

## Features

- AI-powered story generation
- Style customization and building
- Automated novel writing pipeline
- Character relationship analysis
- Professional PDF formatting and enhancement
- Integrated illustration generation

## Prerequisites

- Docker Engine
- Node.js (v20 or higher)
- PHP 8.3
- Composer
- Python 3.12
- PostgreSQL 14
- Git

### Windows-Specific Requirements

This project supports development on both Linux and Windows. The development scripts automatically convert entry scripts to Unix format using `dos2unix`. 

Before building the application container on Windows:

1. Install `dos2unix` globally by running the following command in an administrator terminal (CMD or PowerShell):
```bash
choco install dos2unix
```

2. Once installed, you'll be able to run the Docker container on both Linux and Windows operating systems.

## Installation

### Initial Setup

1. Clone the repository:
```bash
git clone https://github.com/muhammad-akbrrr/runarion-app.git
cd runarion-app
```

2. Create necessary .env files:
   - Copy `.env.example` to `.env` in the root directory
   - Copy `.env.example` to `.env` in both `runarion-laravel` and `runarion-python` directories

### Laravel Setup

```bash
# Navigate to Laravel project
cd runarion-laravel

# Install PHP dependencies
composer install

# Install Node.js dependencies
npm install

# Generate application key
php artisan key:generate

# Return to root directory
cd ..
```

### Python Setup

```bash
# Navigate to Python project
cd runarion-python

# For Windows:
python -m venv venv
venv\Scripts\activate  # For CMD
# OR
source venv/Scripts/activate  # For Git Bash

# For Linux/macOS:
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Deactivate virtual environment when done
deactivate

# Return to root directory
cd ..
```

## Development

### Docker Development

The project uses Docker for development to ensure consistency across environments.

```bash
# Start development environment
./dev.sh

# Rebuild containers (when needed)
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up --build -d

# Quick restart
docker compose -f docker-compose.dev.yml restart

# Cleanup and restart
./dev.sh cleanup
./dev.sh
```

### Port Management

The application uses the following ports:
- Laravel: 8000
- Python: 5000
- PostgreSQL: 5432
- Vite: 5173

To manage port conflicts:

**Windows:**
```bash
# Check port usage
netstat -ano | findstr :<PORT_NUMBER>

# Kill process using port
taskkill /PID <PID> /F
```

**Linux:**
```bash
# Check port usage
sudo lsof -i :<PORT_NUMBER>

# Kill process using port
sudo kill <PID>
```

## Architecture

The application is split into three main components:
- Laravel Application (`runarion-laravel`): Handles web interface, authentication, and database operations
- Python Service (`runarion-python`): Manages AI processing and novel generation pipeline
- Database Service (PostgreSQL): A commonly shared database between the python service and the laravel service

## Configuration

- Database configuration is managed through Laravel's `.env` file
- AI settings can be adjusted in the Python service's configuration
- Docker settings are defined in `docker-compose.dev.yml`
- Environment-specific settings should be configured in respective `.env` files

Key configuration files:
- `.env` files (root, Laravel, and Python directories)
- `config/app.php` (Laravel configuration)
- `docker-compose.dev.yml` (Docker configuration)

## Troubleshooting

Common issues and solutions:

1. **Port Conflicts**
   - Use the port management commands above to identify and resolve conflicts
   - Check if other applications are using required ports

2. **Docker Issues**
   - Ensure Docker Engine is running
   - Try rebuilding containers using `./dev.sh cleanup && ./dev.sh`
   - Check Docker logs for specific error messages

3. **Permission Issues**
   - Ensure proper file permissions in mounted volumes
   - Check user permissions in Docker containers

4. **Database Connection Issues**
   - Verify PostgreSQL password in `.env` files
   - Ensure database service is running
   - Check network connectivity between containers
