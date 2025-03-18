# Runarion Python Service

## Overview

The Python service component of Runarion handles the AI-powered novel generation pipeline. This service processes story concepts through multiple phases to generate professional-quality novels.

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

## Setup and Installation

### Prerequisites
- Python 3.12
- Virtual environment management tool (venv)
- Required system libraries (see requirements.txt)

### Installation Steps

**Linux/macOS:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Windows:**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (CMD)
venv\Scripts\activate
# OR (Git Bash)
source venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt
```

To deactivate the virtual environment when done:
```bash
deactivate
```

## Configuration

### Environment Variables
Create a `.env` file in the root directory with the following variables:
```
AI_MODEL_KEY=your_api_key
OPENAI_API_KEY=your_openai_key
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

## API Endpoints

### Story Generation
- `POST /api/generate/story` - Initialize story generation (placeholder)
- `GET /api/story/{id}` - Retrieve generated story (placeholder)
- `PUT /api/story/{id}/style` - Update story style (placeholder)

### Pipeline Control
- `POST /api/pipeline/start` - Start pipeline processing (placeholder)
- `GET /api/pipeline/status` - Check pipeline status (placeholder)
- `POST /api/pipeline/pause` - Pause processing (placeholder)

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
1. Create model class in `models/`
2. Implement required interfaces
3. Register in `config/model_registry.py`
4. Add configuration in `config/model_config.py`

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

## License

This project is licensed under the MIT License. See `LICENSE` for details.
