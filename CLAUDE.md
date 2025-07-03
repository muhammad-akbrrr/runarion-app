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

- **Primary Database**: PostgreSQL (shared between Laravel and Python)
- **Migrations**: Located in `runarion-laravel/database/migrations/`
- **Connection**: Both services connect to the same PostgreSQL instance

## Environment Configuration

Each service requires its own `.env` file:
- Root: `.env` (Docker configuration)
- Laravel: `runarion-laravel/.env`
- Python: `runarion-python/.env`
- Stable Diffusion: `runarion-stable-diffusion/.env`

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