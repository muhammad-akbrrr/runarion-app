# Runarion Laravel Application

## Overview

The Laravel component of Runarion provides the web interface and API endpoints for the AI-powered novel generation pipeline. It handles user authentication, story management, and integration with the Python service.

## Features

### Core Features
-   User authentication and authorization
-   3-phase novel pipeline processing
-   Real-time pipeline status monitoring with WebSockets
-   API integration with Python service
-   Advanced manuscript deconstruction and analysis

### Novel Pipeline Features
-   **Manuscript Upload & Processing**: PDF upload with automatic text extraction
-   **Scene Analysis**: Automatic scene detection and character identification
-   **Plot Issue Detection**: Plot hole and inconsistency identification
-   **Author Style Analysis**: AI-powered writing style analysis and profiling
-   **Graph Database Integration**: Character and plot relationship mapping via Apache AGE
-   **Enhanced Novel Generation**: Graph-aware novel rewriting and improvement

### Technical Features
-   PostgreSQL 17 with Apache AGE graph database extension
-   Real-time collaborative editing
-   File storage for manuscripts and generated content
-   Comprehensive audit trails with soft deletes

## Setup and Installation

### Prerequisites

-   PHP 8.4
-   Composer
-   Node.js and NPM
-   PostgreSQL 17 with Apache AGE extension
-   Docker (for development environment)

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

#### Core Application Models
    - `User` - User data and authentication
    - `Workspace` - Workspace management and collaboration
    - `Projects` - Project organization and settings

#### Novel Pipeline Models (Phase 1: Deconstruction)
    - `Draft` - Core manuscript tracking with file metadata and processing status
    - `DraftChunk` - Text segmentation for processing large documents
    - `Scene` - Scene-level analysis with character and setting extraction
    - `PlotIssue` - Plot hole and inconsistency identification

#### Novel Pipeline Models (Phase 2 & 3: Analysis & Rewriting)
    - `AnalysisReport` - Author style analysis and reporting
    - `Chapter` - Final chapter organization and structure
    - `FinalManuscript` - Complete generated novels with processing metadata

#### Existing Legacy Models
    - `ProjectContent` - Legacy project content management
    - `StructuredAuthorStyle` - Legacy author style storage

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

PYTHON_SERVICE_URL=http://python-app:5000
```

### Queue Configuration

For background job processing:

```bash
# Start queue worker
php artisan queue:work

# Monitor failed jobs
php artisan queue:failed
```

## Database Schema

### Novel Pipeline Tables

The Laravel application includes comprehensive database tables for the 3-phase novel pipeline:

#### Phase 1: Deconstruction Tables
- **`drafts`**: Core manuscript tracking (UUID primary key, workspace relationships, file metadata)
- **`draft_chunks`**: Text chunking for large document processing
- **`scenes`**: Scene-level analysis with character extraction and plot identification
- **`plot_issues`**: Plot consistency issues (plot holes, inconsistencies)

#### Phase 2: Analysis Tables  
- **`analysis_reports`**: Style analysis reports and author profiling data

#### Phase 3: Generation Tables
- **`chapters`**: Final chapter organization and content structure
- **`final_manuscripts`**: Complete generated novels with processing metadata

#### Graph Database Integration
- **Apache AGE Extension**: Character and plot relationships stored in graph format
- **Graph Operations**: Complex narrative analysis using Cypher-like queries
- **Relationship Mapping**: Character interactions, setting connections, plot dependencies

### Migration Commands

```bash
# Run novel pipeline migrations
php artisan migrate

# Fresh migration with sample data
php artisan migrate:fresh --seed

# Check migration status
php artisan migrate:status
```

### AGE Extension Setup

The PostgreSQL database includes Apache AGE extension for graph operations:

```bash
# Verify AGE extension (via Docker)
docker compose exec postgres-db psql -U postgres -d runarion -c "SELECT * FROM pg_extension WHERE extname = 'age';"

# Test graph operations
docker compose exec postgres-db psql -U postgres -d runarion -c "SELECT ag_catalog.age_version();"
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
