# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Runarion is a full-stack AI-powered novel generation pipeline with three main components:
- **Laravel frontend** (`runarion-laravel/`): React+Inertia.js web interface with real-time features
- **Python backend** (`runarion-python/`): Flask API handling AI processing and novel generation
- **Stable Diffusion service** (`runarion-stable-diffusion/`): Local AI image generation service

## Development Commands

### Starting the Development Environment
```bash
# Start full development environment (all services)
./dev.sh

# Clean restart (if needed)
./dev.sh cleanup && ./dev.sh
```

### Laravel Commands
```bash
cd runarion-laravel

# Development server (with all services)
composer run dev

# Individual Laravel commands
php artisan serve
php artisan queue:listen --tries=1
php artisan migrate
php artisan migrate:fresh --seed
php artisan tinker

# Asset building
npm run dev    # Development with hot reload
npm run build  # Production build
```

### Python Commands  
```bash
cd runarion-python

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
source venv/Scripts/activate  # Windows Git Bash

# Run Flask development server
python src/app.py

# Run tests
python -m pytest tests/
```

### Testing Commands
```bash
# Laravel tests (from runarion-laravel/)
php artisan test
./vendor/bin/pest

# Python tests (from runarion-python/)
python -m pytest tests/
```

### Apache AGE Development Commands
```bash
# Check AGE extension status
docker compose -f docker-compose.dev.yml exec postgres-db psql -U postgres -d runarion -c "SELECT * FROM pg_extension WHERE extname = 'age';"

# Test graph operations
docker compose -f docker-compose.dev.yml exec postgres-db psql -U postgres -d runarion -c "SELECT ag_catalog.age_version();"

# Access graph database
docker compose -f docker-compose.dev.yml exec postgres-db psql -U postgres -d runarion -c "SET search_path = ag_catalog, public; SELECT * FROM ag_graph;"

# Run novel pipeline migrations
cd runarion-laravel && php artisan migrate

# Troubleshoot AGE compilation
docker compose -f docker-compose.dev.yml build --no-cache postgres-db
```

## Architecture Overview

### Service Communication
- Laravel communicates with Python via HTTP API calls
- PostgreSQL database shared between Laravel and Python services
- Real-time features using Laravel Reverb (WebSockets) and Pusher
- Image generation handled by local Stable Diffusion service

### Key Laravel Architecture
- **Inertia.js**: Frontend uses React components with Laravel backend
- **Queue System**: Background jobs for manuscript processing (`ManuscriptDeconstructionJob`, `StreamLLMJob`)
- **Events**: Real-time updates via `LLMStreamChunk`, `LLMStreamStarted`, `LLMStreamCompleted`
- **Models**: Core entities include `Projects`, `Workspace`, `ProjectContent`, `DeconstructorResponse`

### Python Service Architecture
- **Flask API**: Main entry point with CORS configured for Laravel frontend
- **Service Layer**: Organized by functionality (`deconstructor/`, `novel_writer/`, `style_analyzer/`)
- **Pipeline Stages**: Multi-stage processing (ingestion → cleaning → analysis → enhancement)
- **AI Providers**: Abstracted providers for OpenAI, Gemini, and DeepSeek

## Key File Locations

### Laravel
- Routes: `routes/web.php`, `routes/editor.php`
- Controllers: `app/Http/Controllers/`
- React Components: `resources/js/Components/`, `resources/js/Pages/`
- Models: `app/Models/`
- Jobs: `app/Jobs/`

### Python
- Main app: `src/app.py`
- API endpoints: `src/api/`
- Core services: `src/services/`
- AI providers: `src/providers/`
- Utilities: `src/utils/`

## Database

- **Primary Database**: PostgreSQL 17 with Apache AGE extension (shared between Laravel and Python)
- **Graph Database**: Apache AGE for novel pipeline relationship mapping
- **Migrations**: Located in `runarion-laravel/database/migrations/`
- **Connection**: Both services connect to the same PostgreSQL instance
- **AGE Initialization**: `01-init-age.sql` sets up graph database functionality

## Novel Pipeline (3-Phase System)

The core novel generation pipeline consists of three distinct phases, each with dedicated database tables and processing logic:

### Phase 1: Novel Deconstruction
**Purpose**: Analyze and deconstruct uploaded manuscripts into manageable components

**Database Tables**:
- `drafts`: Core manuscript tracking (UUID, workspace_id, file metadata, processing status)
- `draft_chunks`: Text segmentation for processing (chunk_number, raw_text, cleaned_text)
- `scenes`: Scene-level analysis (scene_number, title, summary, setting, characters JSON, original_content)
- `plot_issues`: Issue identification (issue_type: '01'=plot_hole, '02'=inconsistency)

**Key Features**:
- Manuscript upload and validation
- Automatic text chunking for large documents
- Scene extraction and analysis
- Plot consistency checking
- Character and setting identification

### Phase 2: Author Style Analysis/Generator
**Purpose**: Analyze author writing style and generate style profiles for novel enhancement

**Database Tables**:
- `analysis_reports`: Generated style analysis reports (report_type, report_subject, content_json)
- **Graph Integration**: Character and setting relationships stored in Apache AGE graph database

**Key Features**:
- Writing style pattern recognition
- Character relationship mapping via graph database
- Setting and world-building analysis
- Style consistency validation
- Author voice preservation

### Phase 3: Novel Rewriter Pipeline
**Purpose**: Generate enhanced novels using insights from previous phases

**Database Tables**:
- `chapters`: Final chapter organization (chapter_number, title, content)
- `final_manuscripts`: Complete generated novels (final_content, word_count, processing_summary)

**Key Features**:
- Graph-enhanced narrative generation
- Style-consistent rewriting
- Character relationship preservation
- Plot hole resolution
- Professional manuscript formatting

### Graph Database Integration (Apache AGE)

**Graph Schema**:
```cypher
// Novel pipeline graph for relationship mapping
CREATE (character:Character {name: 'string', traits: 'json'})
CREATE (setting:Setting {name: 'string', description: 'text'})
CREATE (plot_point:PlotPoint {description: 'text', scene_id: 'int'})

// Relationships
CREATE (character)-[:APPEARS_IN]->(scene)
CREATE (character)-[:INTERACTS_WITH]->(character)
CREATE (setting)-[:CONTAINS]->(scene)
CREATE (plot_point)-[:AFFECTS]->(character)
```

**Graph Operations**:
- Character relationship analysis
- Setting connectivity mapping
- Plot dependency tracking
- Narrative consistency validation

### Pipeline Flow
1. **Upload** → `drafts` table creation
2. **Deconstruction** → `scenes`, `plot_issues` population
3. **Style Analysis** → `analysis_reports` + graph relationship creation
4. **Rewriting** → `chapters`, `final_manuscripts` generation
5. **Output** → Enhanced novel with relationship-aware improvements

## Environment Configuration

Each service requires its own `.env` file:
- Root: `.env` (Docker configuration + AGE settings)
- Laravel: `runarion-laravel/.env`
- Python: `runarion-python/.env`
- Stable Diffusion: `runarion-stable-diffusion/.env`

**Apache AGE Configuration** (Root `.env`):
```bash
# Enable/disable Apache AGE extension
AGE_ENABLED=true

# Graph name for novel pipeline operations
AGE_GRAPH_NAME=novel_pipeline_graph
```

Required environment variables are validated in Python service startup.

## Code Patterns

### Laravel Patterns
- Use Inertia.js for passing data to React components
- Real-time updates via Laravel Events and WebSockets
- Queue jobs for long-running AI operations
- Resource controllers for CRUD operations

### Python Patterns
- Service-oriented architecture with clear separation of concerns
- Orchestrator pattern for complex multi-stage processes
- Provider pattern for AI model abstraction
- Database operations using connection pooling

## Development Notes

- The project uses Docker for consistency across environments
- NVIDIA GPU support required for Stable Diffusion service
- Laravel uses Pest for testing, Python uses pytest
- Frontend is built with React, TypeScript, and Tailwind CSS
- Real-time features implemented with Laravel Reverb and Pusher