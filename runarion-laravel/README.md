# Runarion Laravel Application

## Overview

The Laravel component serves as the **application glue and bridge** for the Runarion ecosystem. It acts as the central orchestrator that connects the frontend interface to the backend AI processing services, while managing the core business logic (excluding AI/LLM operations). 

**Key Responsibilities:**
- **Frontend Bridge**: Provides the React+Inertia.js web interface and user experience
- **Database Controller**: Handles all database migrations, schema management, and data persistence
- **API Gateway**: Routes and manages communication between frontend and Python AI services
- **Business Logic Hub**: Manages user authentication, project organization, and non-AI workflows
- **Pipeline Coordinator**: Orchestrates the novel generation pipeline by communicating with Python service via HTTP API

**What it does NOT handle:** The actual AI processing, LLM operations, and novel pipeline execution - these are delegated to the Python service.

## Features

### Core Features

-   User authentication and authorization
-   **Pipeline Orchestration**: Coordinates 3-phase novel pipeline by communicating with Python service
-   Real-time pipeline status monitoring with WebSockets
-   **API Integration**: Serves as bridge between frontend and Python AI service
-   Database management for all pipeline data and user content

### Novel Pipeline Coordination (via Python Service)

The Laravel application coordinates these features by delegating AI processing to the Python service:

-   **Manuscript Upload & Processing**: Handles file uploads, delegates text extraction to Python service
-   **Scene Analysis**: Coordinates scene detection and character identification via API calls
-   **Plot Issue Detection**: Manages plot analysis workflow through Python service integration
-   **Author Style Analysis**: Orchestrates AI-powered style analysis via Python service
-   **Graph Database Integration**: Manages AGE database operations, coordinates with Python for relationship mapping
-   **Enhanced Novel Generation**: Coordinates graph-aware novel generation through Python service

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

# Generate App-ID, secrets, and key for reverb-related variables
php artisan tinker
Str::random(32);
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
│   ├── Events/                         # Real-time events (LLMStreamChunk, ProjectContentUpdated)
│   ├── Http/
│   │   ├── Controllers/
│   │   │   ├── Auth/                   # Authentication controllers
│   │   │   ├── ProjectEditor/          # Project editor controllers
│   │   │   │   ├── MainEditorController.php
│   │   │   │   ├── ImageGeneratorController.php
│   │   │   │   ├── MultiPromptController.php
│   │   │   │   └── ProjectDatabaseController.php
│   │   │   ├── DashboardController.php
│   │   │   ├── ProjectController.php
│   │   │   └── WorkspaceController.php
│   │   ├── Middleware/
│   │   │   ├── ResolveProjectEditor.php
│   │   │   └── ResolveWorkspace.php
│   │   └── Requests/
│   ├── Jobs/                           # Background jobs
│   │   ├── ManuscriptDeconstructionJob.php
│   │   └── StreamLLMJob.php
│   ├── Models/                         # Database models
│   │   ├── Draft.php                   # Novel pipeline models
│   │   ├── Scene.php
│   │   ├── Chapter.php
│   │   ├── FinalManuscript.php
│   │   ├── Projects.php                # Core application models
│   │   ├── Workspace.php
│   │   └── User.php
│   ├── Notifications/                  # Email/push notifications
│   └── Providers/
├── database/
│   ├── migrations/                     # Database schema migrations
│   │   ├── 2025_07_04_010000_create_novel_pipeline_drafts_table.php
│   │   ├── 2025_07_04_020000_create_novel_pipeline_scenes_table.php
│   │   └── ... (other migrations)
│   ├── seeders/                        # Database seeders
│   └── factories/                      # Model factories for testing
├── resources/
│   ├── js/                             # React/TypeScript frontend
│   │   ├── Components/
│   │   │   ├── ui/                     # UI components (shadcn/ui)
│   │   │   └── react-flow/             # React Flow components
│   │   ├── Pages/
│   │   │   ├── Projects/
│   │   │   │   └── Editor/             # Project editor pages
│   │   │   ├── Workspace/              # Workspace management
│   │   │   └── Auth/                   # Authentication pages
│   │   ├── Layouts/                    # Layout components
│   │   └── types/                      # TypeScript type definitions
│   ├── css/                            # Tailwind CSS
│   └── views/                          # Blade templates
├── routes/
│   ├── web.php                         # Web routes
│   ├── auth.php                        # Authentication routes
│   ├── editor.php                      # Project editor routes
│   └── channels.php                    # WebSocket channels
└── config/                             # Laravel configuration files
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
    - `PythonService` - **Primary service for AI operations** - Routes all AI/LLM requests to Python service
    - `StoryService` - Story business logic and coordination
    - `FileService` - File management and upload handling

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

-   **`drafts`**: Core manuscript tracking (UUID primary key, workspace relationships, file metadata)
-   **`draft_chunks`**: Text chunking for large document processing
-   **`scenes`**: Scene-level analysis with character extraction and plot identification
-   **`plot_issues`**: Plot consistency issues (plot holes, inconsistencies)

#### Phase 2: Analysis Tables

-   **`analysis_reports`**: Style analysis reports and author profiling data

#### Phase 3: Generation Tables

-   **`chapters`**: Final chapter organization and content structure
-   **`final_manuscripts`**: Complete generated novels with processing metadata

#### Graph Database Integration

-   **Apache AGE Extension**: Character and plot relationships stored in graph format
-   **Graph Operations**: Complex narrative analysis using Cypher-like queries
-   **Relationship Mapping**: Character interactions, setting connections, plot dependencies

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
docker compose exec postgres-db psql -U postgres -d runarion -c "SELECT extversion FROM pg_extension WHERE extname = 'age';"
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
