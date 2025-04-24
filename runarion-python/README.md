# Runarion Python Service

## Overview

The Python service component of Runarion handles the AI-powered novel generation pipeline. This service processes story concepts through multiple phases to generate professional-quality novels, integrating with various AI models and services.

## Features

- AI-powered story generation
- Style customization and building
- Automated novel writing pipeline
- Character relationship analysis
- PDF enhancement and formatting
- Integration with Stable Diffusion for illustrations
- FastAPI-based REST API
- Docker containerization

## Directory Structure

```
runarion-python/
├── src/
│   ├── app.py            # Flask application and pipeline initialization
│   ├── models/           # AI model implementations
│   ├── services/         # Business logic services
│   └── utils/            # Utility functions and helpers
├── tests/                # Test suite
├── venv/                 # Python virtual environment
├── dockerfile           # Docker container definition
├── docker-entrypoint.sh # Container entrypoint script
├── requirements.txt     # Python dependencies
└── .env                 # Environment configuration
```

## Prerequisites

- Python 3.12
- Virtual environment management tool (venv)
- Docker (for containerized deployment)
- PostgreSQL 17 (for database)
- Required system libraries (see requirements.txt)

## Setup and Installation

### Local Development Setup

```bash
# Navigate to Python project
cd runarion-python

# For Windows:
python -m venv venv --clear
venv\Scripts\activate  # For CMD
# OR
source venv/Scripts/activate  # For Git Bash

# For Linux/macOS:
python3 -m venv venv --clear
source venv/bin/activate

# Install dependencies
python -m pip install --no-cache-dir -r requirements.txt

# Deactivate virtual environment when done
deactivate

# Return to root directory
cd ..
```

### Docker Setup

The service is designed to run in a Docker container. The container is managed through the main project's Docker Compose configuration.

To build and run the container:

```bash
# From the root directory
docker compose -f docker-compose.dev.yml up -d python-service
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```
# API Configuration
AI_MODEL_KEY=your_api_key
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
GOOGLE_API_KEY=your_google_key

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Service Configuration
PYTHON_SERVICE_URL=http://localhost:5000
SD_SERVICE_URL=http://stable-diffusion:7860

# Pipeline Configuration
ENABLE_PARALLEL_PROCESSING=true
MAX_CONCURRENT_TASKS=4
```

## API Endpoints

### Story Generation

- list API endpoints as well as their method, and descriptrion here

### Pipeline Control

- list API endpoints as well as their method, and descriptrion here

## Pipeline Phases

### 1. Initial Story Generation

- Processes user input and story concepts
- Generates initial story structure and outline
- Establishes core narrative elements

### 2. Style Building

- Analyzes and applies writing style preferences
- Maintains consistency in tone and voice
- Adapts to genre-specific requirements

### 3. Novel Writing

- Generates chapter content
- Maintains narrative consistency
- Handles character development and plot progression

### 4. Relationship Analysis

- Maps character interactions and relationships
- Ensures consistent character development
- Validates plot coherence

### 5. PDF Enhancement

- Formats content for professional publication
- Generates chapter breaks and sections
- Applies typography and layout rules
- Integrates with Stable Diffusion for illustrations

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

The project follows PEP 8 guidelines. Run linting with:

```bash
flake8 .
```

### Adding New Models

1. Create model class in `src/models/`
2. Implement required interfaces
3. Register in `src/models/registry.py`
4. Add configuration in `src/config/model_config.py`

## Troubleshooting

### Common Issues

1. **Model Loading Errors**

   - Verify API keys are set correctly
   - Check model availability and quotas
   - Ensure sufficient system resources

2. **Pipeline Interruptions**

   - Check database connectivity
   - Verify file system permissions
   - Monitor system resources

3. **Generation Quality Issues**

   - Adjust model parameters
   - Check input validation
   - Review style configurations

4. **Integration Issues**

   - Verify Stable Diffusion service availability
   - Check API endpoint configurations
   - Monitor inter-service communication

5. **Docker Issues**
   - Check container logs
   - Verify network connectivity
   - Ensure proper volume mounts

## Security

- API key management
- Input validation and sanitization
- Rate limiting
- CORS protection
- Container security best practices

## License

This project is licensed under the MIT License. See `LICENSE` for details.
