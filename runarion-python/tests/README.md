# Runarion Deconstructor Pipeline Test Suite

This test suite provides comprehensive testing for the Runarion deconstructor pipeline with real AI provider integration. Tests are designed to run in Docker containers with dependencies on PostgreSQL and Laravel services.

## Overview

The test suite includes:

- **Integration tests** for end-to-end API testing with real AI providers
- **Stage-specific tests** for individual pipeline stages (currently Stage 1 and Stage 2)
- **Database integration** with PostgreSQL and Apache AGE
- **Real AI provider integration** using Gemini, OpenAI, and DeepSeek APIs

## Test Structure

```
tests/
├── conftest.py                    # Global pytest configuration and fixtures
├── test_imports.py                # Import validation tests
├── test_real_api_environment.py   # Environment validation tests
├── test_utils/                    # Testing utilities and helpers
├── integration/                   # End-to-end integration tests
├── stages/                        # Individual stage tests
│   ├── test_stage_1_ingestion.py  # Stage 1: Document ingestion
│   └── test_stage_2_cleaning.py   # Stage 2: Text cleaning with AI
├── sample_files/                  # Sample files for testing
│   ├── inputs/                    # Sample manuscripts
│   │   └── short_story.pdf        # ~3,300 words - basic functionality testing
│   └── test_configs/              # Test configuration files
│       ├── minimal_config.json
│       ├── full_config.json
│       └── performance_config.json
└── outputs/                       # Test outputs (auto-generated)
    ├── deconstructor/             # Stage-specific outputs
    │   ├── stage_1/ ... stage_7/  # Results, logs, performance data
    └── temp/                      # Temporary test files
```

## Docker Environment Setup

**IMPORTANT**: All tests must be run from within the Docker environment due to dependencies on PostgreSQL and Laravel services.

### Prerequisites

1. Start the development environment:

   ```bash
   ./dev.sh
   ```

2. Ensure all containers are running:
   ```bash
   docker ps
   # Should show: python-app, postgres-db, laravel-app
   ```

### Environment Variables

Set at least one AI provider API key:

```bash
# In your .env file or Docker environment
GEMINI_API_KEY=your-gemini-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
DEEPSEEK_API_KEY=your-deepseek-api-key-here

# Database (handled by Docker)
TEST_DATABASE_URL="postgresql://postgres:password@postgres-db:5432/runarion_test"
```

## Running Tests

### Basic Test Commands

All tests must be run from within the Docker container:

```bash
# Run all tests
docker exec python-app pytest tests/ -v

# Run specific test categories
docker exec python-app pytest tests/ -m integration -v
docker exec python-app pytest tests/ -m stage -v

# Run specific test files
docker exec python-app pytest tests/stages/test_stage_1_ingestion.py -v
docker exec python-app pytest tests/stages/test_stage_2_cleaning.py -v
```

### Key Testing Flags

The test suite supports three critical flags for controlling test behavior:

#### 1. `--sample-file` Flag

Specify which sample file to use for testing:

```bash
# Run stage tests with specific sample file
docker exec python-app pytest tests/stages/test_stage_1_ingestion.py -v \
  --sample-file="short_story.pdf"

# Run all stage tests with sample file
docker exec python-app pytest tests/stages/ -v \
  --sample-file="short_story.pdf"

# Run integration tests with sample file
docker exec python-app pytest tests/integration/ -v \
  --sample-file="short_story.pdf"
```

**Available Sample Files:**

- `short_story.pdf` - ~3,300 words, recommended for development

#### 2. `--cleanup-test-data` Flag

Control test data cleanup behavior:

```bash
# Clean up test data after each test (default)
docker exec python-app pytest tests/stages/test_stage_1_ingestion.py -v \
  --cleanup-test-data

# Keep test data for debugging
docker exec python-app pytest tests/stages/test_stage_1_ingestion.py -v \
  --no-cleanup-test-data
```

#### 3. `--persist-data` Flag

Control data persistence between test runs:

```bash
# Persist data between tests for faster subsequent runs
docker exec python-app pytest tests/stages/test_stage_2_cleaning.py -v \
  --persist-data

# Don't persist data (clean slate each time)
docker exec python-app pytest tests/stages/test_stage_2_cleaning.py -v \
  --no-persist-data
```

### Combined Flag Usage

```bash
# Run stage 2 tests with all key flags
docker exec python-app pytest tests/stages/test_stage_2_cleaning.py -v \
  --sample-file="short_story.pdf" \
  --cleanup-test-data \
  --persist-data

# Run full pipeline with specific configuration
docker exec python-app pytest tests/integration/test_pipeline_flow.py -v \
  --sample-file="short_story.pdf" \
  --cleanup-test-data \
  --persist-data
```

### Test Configuration Files

Use specific configuration files for different test scenarios:

```bash
# Minimal configuration for fast testing
docker exec python-app pytest tests/ -v \
  --config-file="minimal_config.json"

# Performance configuration for load testing
docker exec python-app pytest tests/ -v \
  --config-file="performance_config.json"

# Full configuration for comprehensive testing
docker exec python-app pytest tests/ -v \
  --config-file="full_config.json"
```

## Test Markers

Use pytest markers to run specific test categories:

```bash
# Run only integration tests
docker exec python-app pytest tests/ -m integration -v

# Run only stage tests
docker exec python-app pytest tests/ -m stage -v

# Run only database tests
docker exec python-app pytest tests/ -m database -v

# Skip expensive tests (saves API costs)
docker exec python-app pytest tests/ -m "not expensive" -v

# Run only fast tests
docker exec python-app pytest tests/ -m "not slow and not expensive" -v
```

## Stage-Specific Testing

### Stage 1: Document Ingestion

```bash
# Test PDF ingestion
docker exec python-app pytest tests/stages/test_stage_1_ingestion.py::TestStage1Ingestion::test_pdf_ingestion -v \
  --sample-file="short_story.pdf"

# Test text chunking
docker exec python-app pytest tests/stages/test_stage_1_ingestion.py::TestStage1Ingestion::test_text_chunking -v \
  --sample-file="short_story.pdf"
```

### Stage 2: Text Cleaning

```bash
# Test text cleaning with AI
docker exec python-app pytest tests/stages/test_stage_2_cleaning.py::TestStage2Cleaning::test_cleaning_success -v \
  --sample-file="short_story.pdf" \
  --provider="gemini"

# Test error handling
docker exec python-app pytest tests/stages/test_stage_2_cleaning.py::TestStage2Cleaning::test_error_handling -v \
  --sample-file="short_story.pdf"
```

## Database Dependencies

The test suite requires:

- **PostgreSQL** with Apache AGE extension
- **Laravel migrations** for database schema
- **Laravel seeders** for test data
- **Laravel factories** for data generation

These dependencies are automatically handled when running tests from the Docker environment.

## Environment Validation

Before running tests, validate your environment:

```bash
# Check environment setup
docker exec python-app python tests/test_real_api_environment.py

# Validate imports
docker exec python-app pytest tests/test_imports.py -v
```

## Output Management

Test outputs are automatically organized in the `outputs/` directory:

- **Results**: JSON files with test outcomes
- **Logs**: Detailed execution logs
- **Performance**: Timing and metrics data
- **Database Seeds**: Generated test data for next stages

## Cost Management

Real AI tests consume API tokens:

```bash
# Skip expensive tests
docker exec python-app pytest tests/ -m "not expensive" -v

# Run only cheap tests
docker exec python-app pytest tests/ -m "not slow and not expensive" -v
```

## Sample File Management

### Adding New Sample Files

1. Add file to `tests/sample_files/inputs/`:

   ```bash
   cp my_novel.pdf tests/sample_files/inputs/
   ```

2. Test with new file:
   ```bash
   docker exec python-app pytest tests/stages/test_stage_1_ingestion.py -v \
     --sample-file="my_novel.pdf"
   ```

### Sample File Debugging

```bash
# Debug sample file processing
docker exec python-app pytest tests/stages/test_stage_1_ingestion.py -v -s \
  --sample-file="short_story.pdf" \
  --log-cli-level=DEBUG
```

## Common Test Patterns

### Basic Stage Testing

```bash
# Test a single stage with default settings
docker exec python-app pytest tests/stages/test_stage_1_ingestion.py -v

# Test with specific sample file and cleanup
docker exec python-app pytest tests/stages/test_stage_1_ingestion.py -v \
  --sample-file="short_story.pdf" \
  --cleanup-test-data
```

### Integration Testing

```bash
# Test full pipeline flow
docker exec python-app pytest tests/integration/test_pipeline_flow.py -v \
  --sample-file="short_story.pdf" \
  --persist-data

# Test API endpoints
docker exec python-app pytest tests/integration/test_deconstructor_api.py -v \
  --sample-file="short_story.pdf"
```

### Performance Testing

```bash
# Run with performance configuration
docker exec python-app pytest tests/stages/test_stage_2_cleaning.py -v \
  --sample-file="short_story.pdf" \
  --config-file="performance_config.json" \
  --persist-data
```

## Troubleshooting

### Common Issues

1. **Container not running**: Ensure `./dev.sh` completed successfully
2. **Database connection**: Check postgres-db container is running
3. **API keys missing**: Set environment variables in Docker environment
4. **Import errors**: Run `pytest tests/test_imports.py` to validate

### Debug Commands

```bash
# Check container status
docker ps

# View container logs
docker logs python-app
docker logs postgres-db

# Access container shell
docker exec -it python-app bash

# Test database connection
docker exec python-app python -c "
from src.utils.database_utils import get_db_connection
print('Database connection:', get_db_connection())
"
```

## Development Workflow

1. **Start environment**: `./dev.sh`
2. **Run environment check**: `docker exec python-app python tests/test_real_api_environment.py`
3. **Run specific tests**: Use the key flags `--sample-file`, `--cleanup-test-data`, `--persist-data`
4. **Check outputs**: Review `tests/outputs/` for results and logs
5. **Debug issues**: Use verbose flags and container logs

## Current Test Coverage

- ✅ **Stage 1**: Document ingestion and chunking
- ✅ **Stage 2**: Text cleaning with AI
- ⏳ **Stages 3-7**: Planned for future implementation

For questions about the test suite, examine existing test examples and consult the Docker container logs for detailed execution information.
