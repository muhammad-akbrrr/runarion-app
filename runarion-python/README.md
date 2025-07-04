# Runarion Python Service

## Overview

The Python service component of Runarion handles the AI-powered novel generation pipeline. This service processes story concepts through multiple phases to generate professional-quality novels, integrating with various AI models and services.

## Features

### Core AI Features
- AI-powered story generation with multiple model support (OpenAI, Gemini, DeepSeek)
- Advanced 3-phase novel writing pipeline
- Intelligent manuscript deconstruction and analysis
- Author style analysis and profiling

### Graph Database Integration
- **Apache AGE Extension**: PostgreSQL 17 with graph database capabilities
- Character relationship mapping and analysis
- Plot dependency tracking and visualization
- Complex narrative structure analysis using graph queries
- Scene and setting relationship modeling

### Pipeline Features
- **Phase 1**: Manuscript deconstruction, scene extraction, plot analysis
- **Phase 2**: Author style analysis with graph-based character relationships
- **Phase 3**: Enhanced novel generation using graph insights
- Real-time processing with job queue integration

### Technical Features
- Flask-based REST API with comprehensive error handling
- PDF enhancement and professional formatting
- Integration with Stable Diffusion for illustrations
- Docker containerization with health checks
- Comprehensive logging and monitoring

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
- **PostgreSQL 17 with Apache AGE extension** (for database and graph operations)
- Required system libraries (see requirements.txt)
- Graph database knowledge (Cypher-like queries) for advanced features

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

# Apache AGE Graph Database Configuration
AGE_ENABLED=true
AGE_GRAPH_NAME=novel_pipeline_graph

# Service Configuration
PYTHON_SERVICE_URL=http://python-app:5000
SD_SERVICE_URL=http://stable-diffusion:7860

# Pipeline Configuration
ENABLE_PARALLEL_PROCESSING=true
MAX_CONCURRENT_TASKS=4
```

## Graph Database Operations

### Apache AGE Integration

The Python service integrates with Apache AGE for advanced graph-based novel analysis:

#### Character Relationship Mapping
```python
# Example: Create character relationships in graph
def create_character_relationships(characters, scene_id):
    query = """
    SELECT * FROM cypher('novel_pipeline_graph', $$
        CREATE (c1:Character {name: $char1_name, scene_id: $scene_id})
        CREATE (c2:Character {name: $char2_name, scene_id: $scene_id})  
        CREATE (c1)-[:INTERACTS_WITH {scene_id: $scene_id}]->(c2)
        RETURN c1, c2
    $$) AS (c1 agtype, c2 agtype);
    """
```

#### Plot Dependency Analysis
```python
# Example: Track plot dependencies
def analyze_plot_dependencies(scenes):
    query = """
    SELECT * FROM cypher('novel_pipeline_graph', $$
        MATCH (s1:Scene)-[:LEADS_TO]->(s2:Scene)
        WHERE s1.plot_importance > 0.7
        RETURN s1.title, s2.title, path_length
    $$) AS (scene1 agtype, scene2 agtype, length agtype);
    """
```

#### Graph-Enhanced Analysis Features
- **Character Arc Tracking**: Follow character development across scenes
- **Setting Relationships**: Map location connections and transitions
- **Plot Consistency**: Identify narrative gaps and inconsistencies
- **Style Pattern Recognition**: Graph-based style analysis and matching

### Graph Database Health Checks
```bash
# Test AGE connectivity
python -c "import psycopg2; conn = psycopg2.connect('DATABASE_URL'); print('AGE Connected')"

# Verify graph operations
SELECT ag_catalog.age_version();
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
