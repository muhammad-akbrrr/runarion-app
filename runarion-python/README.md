# Runarion Python Service

## Overview

The Python service is the **AI/LLM processing powerhouse** of Runarion, handling ALL artificial intelligence and machine learning operations. This service contains the complete novel generation pipeline and processes all AI-related requests from the Laravel application via HTTP API.

**Primary Responsibilities:**

- **AI Processing Engine**: Handles all LLM interactions (OpenAI, Gemini, DeepSeek)
- **Novel Pipeline Execution**: Runs the complete 3-phase novel generation pipeline
- **Graph-Based AI Analysis**: Performs complex narrative analysis using Apache AGE graph database
- **Style Analysis & Profiling**: AI-powered author style analysis and matching
- **Future PDF Enhancement**: Will integrate with Stable Diffusion service for visual novel enhancements

**Service Architecture:** The Python service operates as a standalone Flask API that receives requests from Laravel, processes them using AI models, and returns results. It does NOT handle user authentication, frontend interfaces, or general business logic - these are managed by the Laravel application.

## Features

### Core AI Features

- **Multi-Model LLM Support**: Integrates with OpenAI, Gemini, and DeepSeek for diverse AI capabilities
- **Advanced Novel Generation Pipeline**: Complete 3-phase AI-driven novel creation system
- **Intelligent Manuscript Processing**: AI-powered deconstruction, analysis, and enhancement
- **AI Style Analysis**: Machine learning-based author style profiling and matching
- **Graph-Enhanced AI Processing**: Uses Apache AGE for complex narrative relationship analysis

### Graph Database Integration

- **Apache AGE Extension**: PostgreSQL 17 with graph database capabilities
- Character relationship mapping and analysis
- Plot dependency tracking and visualization
- Complex narrative structure analysis using graph queries
- Scene and setting relationship modeling

### AI Pipeline Features

- **Phase 1 (AI Deconstruction)**: LLM-powered manuscript analysis, scene extraction, and plot issue detection
- **Phase 2 (AI Style Analysis)**: Machine learning-based author style profiling with graph-enhanced character relationship mapping
- **Phase 3 (AI Novel Generation)**: Advanced LLM-driven novel creation using graph insights and style consistency
- **Real-time AI Processing**: Streaming LLM responses with job queue integration for Laravel coordination

### Technical Features

- **Flask-based AI API**: REST API optimized for AI/LLM processing with comprehensive error handling
- **Future PDF Enhancement**: Planned integration with Stable Diffusion service for AI-generated illustrations
- **AI Model Management**: Robust handling of multiple LLM providers with fallback strategies
- **Docker Containerization**: Optimized containerization for AI processing workloads
- **AI Processing Monitoring**: Comprehensive logging and monitoring for LLM operations and pipeline execution

## Directory Structure

```
runarion-python/
├── src/
│   ├── app.py                          # Flask application and main API entry point
│   ├── config.py                       # Configuration management
│   ├── api/                            # API endpoints
│   │   ├── deconstructor.py            # Novel deconstruction API
│   │   ├── novel_writer.py             # Novel generation API
│   │   ├── style_analyzer.py           # Style analysis API
│   │   └── generation.py               # General generation API
│   ├── models/                         # Data models and request/response schemas
│   │   ├── request.py                  # Request models
│   │   ├── response.py                 # Response models
│   │   ├── quota.py                    # Quota management models
│   │   └── story_generation/           # Story generation models
│   │       ├── prompt_config.py
│   │       └── streaming.py
│   ├── providers/                      # AI/LLM provider implementations
│   │   ├── base_provider.py            # Base provider interface
│   │   ├── openai_provider.py          # OpenAI integration
│   │   └── gemini_provider.py          # Google Gemini integration
│   ├── services/                       # Core AI processing services
│   │   ├── deconstructor/              # Novel deconstruction pipeline
│   │   │   ├── orchestrator.py         # Deconstruction orchestrator
│   │   │   ├── prompt_template.py      # Prompt templates
│   │   │   ├── stage_1_ingestion.py    # Document ingestion
│   │   │   ├── stage_2_cleaning.py     # Text cleaning
│   │   │   # ├── stage_3_sceneExtract.py # Scene extraction (FUTURE)
│   │   │   # ├── stage_4_analysis/       # Analysis stages (FUTURE)
│   │   │   # │   ├── analyzer_4a.py      # Character analysis (FUTURE)
│   │   │   # │   ├── analyzer_4b.py      # Setting analysis (FUTURE)
│   │   │   # │   └── analyzer_4c_reports.py # Report generation (FUTURE)
│   │   │   # ├── stage_5_coherence.py    # Coherence validation (FUTURE)
│   │   │   # ├── stage_6_enhancement.py  # Content enhancement (FUTURE)
│   │   │   # └── stage_7_chaptering.py   # Chapter organization (FUTURE)
│   │   ├── style_analyzer/             # Author style analysis
│   │   │   ├── orchestrator.py         # Style analysis orchestrator
│   │   │   ├── prompt_template.py      # Style analysis prompts
│   │   │   ├── stage_1_sampling.py     # Text sampling
│   │   │   └── stage_2_profiling.py    # Style profiling
│   │   ├── novel_writer/               # Novel generation pipeline
│   │   │   ├── orchestrator.py         # Novel writing orchestrator
│   │   │   ├── prompt_template.py      # Writing prompts
│   │   │   ├── entity_profiler.py      # Character/entity profiling
│   │   │   └── scene_generator.py      # Scene generation
│   │   ├── usecase_handler/            # Use case handlers
│   │   │   ├── base_handler.py         # Base handler interface
│   │   │   ├── story_handler.py        # Story handling logic
│   │   │   └── mock_handler.py         # Mock handler for testing
│   │   ├── generation_engine.py        # Core generation engine
│   │   └── quota_manager.py            # API quota management
│   └── utils/                          # Utility functions
│       ├── document_processor.py       # Document processing utilities
│       ├── tokenizer.py               # Text tokenization
│       ├── get_model_max_token.py     # Model token limits
│       └── story_instruction_builder.py # Story instruction building
├── tests/                              # Test suite
│   ├── test_utils/                     # Test utilities
│   └── __init__.py
├── uploads/                            # File upload directory
├── venv/                               # Python virtual environment
├── dockerfile                         # Docker container definition
├── docker-entrypoint.sh               # Container entrypoint script
├── requirements.txt                    # Python dependencies
└── README.md                          # This file
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

**POST** `/api/generate` - Generate content using AI providers
**POST** `/api/stream` - Stream AI-generated content in real-time  
**GET** `/health` - Service health check endpoint

### Pipeline Control

**POST** `/api/deconstruct` - Start novel deconstruction pipeline (Stages 1-2 currently active)
**GET** `/api/deconstruct/status/<draft_id>` - Get pipeline processing status
**GET** `/api/deconstruct/results/<draft_id>` - Get completed pipeline results

## AI Pipeline Phases

### 1. AI-Powered Story Deconstruction

- **LLM Processing**: Uses advanced language models to analyze uploaded manuscripts
- **Scene Extraction**: AI-powered scene identification and character recognition
- **Plot Analysis**: Automated plot hole detection and narrative inconsistency identification
- **Graph Integration**: Character and setting relationship mapping using Apache AGE

### 2. AI Style Analysis & Profiling

- **Style Recognition**: Machine learning-based analysis of author writing patterns
- **Voice Consistency**: AI-powered tone and style consistency validation
- **Genre Adaptation**: LLM-based adaptation to specific genre requirements
- **Graph-Enhanced Analysis**: Character relationship analysis using graph database queries

### 3. AI Novel Generation

- **LLM Content Creation**: Advanced language model-driven chapter generation
- **Narrative Consistency**: AI-powered plot and character development tracking
- **Style Preservation**: Maintains author voice consistency throughout generation
- **Graph-Aware Writing**: Uses relationship insights from Apache AGE for enhanced storytelling

### 4. AI Relationship Analysis

- **Character Mapping**: Graph-based AI analysis of character interactions
- **Plot Validation**: AI-powered narrative coherence and consistency checking
- **Relationship Tracking**: Machine learning-based character development analysis
- **Graph Query Processing**: Complex narrative analysis using Apache AGE Cypher-like queries

### 5. Future PDF Enhancement (Planned)

- **AI-Generated Illustrations**: Integration with Stable Diffusion service for chapter illustrations
- **Smart Formatting**: AI-powered professional publication formatting
- **Visual Enhancement**: Machine learning-based typography and layout optimization
- **Multi-Modal Integration**: Combining text generation with visual AI capabilities

## Development

### Running Tests

**Note**: Tests require pytest and other dependencies to be installed:

```bash
# Install test dependencies first
pip install pytest psycopg2-binary PyMuPDF

# Run tests
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
