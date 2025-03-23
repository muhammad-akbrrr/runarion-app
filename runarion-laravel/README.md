# Runarion Laravel Application

## Overview

The Laravel component of Runarion provides the web interface and API endpoints for the AI-powered novel generation pipeline. It handles user authentication, story management, and integration with the Python service.

## Features

-   User authentication and authorization
-   Story management interface
-   Real-time pipeline status monitoring
-   API integration with Python service
-   Database management for story data
-   File storage for generated content

## Setup and Installation

### Prerequisites

-   PHP 8.3
-   Composer
-   Node.js and NPM
-   PostgreSQL 14

### Installation Steps

1. Install PHP dependencies:

```bash
cd runarion-laravel
composer install
```

2. Install Node.js dependencies:

```bash
npm install
```

3. Environment setup:

```bash
# Copy environment file
cp .env.example .env

# Generate application key
php artisan key:generate
```

4. Configure database in `.env`:

```
DB_CONNECTION=pgsql
DB_HOST=127.0.0.1
DB_PORT=5432
DB_DATABASE=runarion
DB_USERNAME=postgres
DB_PASSWORD=your_password
```

## Development

### Starting the Development Server

The Laravel application is designed to run within Docker containers. Do not run the development server directly. Instead, use the Docker development script from the root directory:

```bash
# From the root directory
./dev.sh
```

This will start all necessary services, including the Laravel application, in Docker containers.

### Database Management

Database management should be done through GUI tools like DBeaver (recommended) or pgAdmin:

1. Connect to the PostgreSQL database container:

    - Host: localhost
    - Port: 5432
    - Database: runarion
    - Username: from your .env file
    - Password: from your .env file

2. The database container persists data through Docker volumes, so your data will remain even after container restarts.

3. For database migrations and seeding, these will be handled automatically by the Docker setup.

### Directory Structure

```
runarion-laravel/
├── app/
│   ├── Http/
│   │   ├── Controllers/
│   │   └── Middleware/
│   ├── Models/
│   └── Services/
├── database/
│   ├── migrations/
│   └── seeders/
├── resources/
│   ├── js/
│   └── views/
└── routes/
    ├── api.php
    └── web.php
```

### Key Components

1. **Controllers**

    - `StoryController` - Story management
    - `PipelineController` - Pipeline control
    - `AuthController` - User authentication

2. **Models**

    - `User` - User data
    - `Story` - Story information
    - `Pipeline` - Pipeline status

3. **Services**
    - `PythonService` - Python API integration
    - `StoryService` - Story business logic
    - `FileService` - File management

## Configuration

### Environment Variables

Required variables in `.env`:

```
APP_NAME=Runarion
APP_ENV=local
APP_KEY=
APP_DEBUG=true
APP_URL=http://localhost

DB_CONNECTION=pgsql
DB_HOST=127.0.0.1
DB_PORT=5432
DB_DATABASE=runarion
DB_USERNAME=postgres
DB_PASSWORD=your_password

PYTHON_SERVICE_URL=http://localhost:5000
```

### Queue Configuration

For background job processing:

```bash
# Start queue worker
php artisan queue:work

# Monitor failed jobs
php artisan queue:failed
```

## Testing

Run the test suite:

```bash
php artisan test
```

### Common Issues

1. **Database Connection**

    - Verify PostgreSQL service is running
    - Check database credentials
    - Ensure database exists

2. **API Integration**

    - Check Python service availability
    - Verify API endpoints
    - Monitor request/response logs

3. **File Permissions**
    - Check storage directory permissions
    - Verify file upload configurations
    - Monitor disk space

## Security

-   All API endpoints are protected with authentication
-   File uploads are validated and sanitized
-   CSRF protection is enabled
-   Rate limiting is implemented
-   SQL injection prevention is active

## License

This project is licensed under the MIT License. See `LICENSE` for details.
