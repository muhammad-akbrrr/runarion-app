# Runarion Deconstructor Pipeline Test Suite

This comprehensive test suite provides testing infrastructure for the Runarion deconstructor pipeline using real AI providers. The test suite focuses on practical, production-like testing that validates actual API integration.

## Overview

The test suite includes:

- **Integration tests** for end-to-end API testing with real AI providers
- **Stage-specific tests** for individual pipeline stages (currently Stage 1 and Stage 2)
- **Database integration** with PostgreSQL and Apache AGE
- **Real AI provider integration** using Gemini, OpenAI, and DeepSeek APIs
- **Cost-aware testing** with appropriate markers for expensive operations

## Test Structure

```
tests/
├── conftest.py                    # Global pytest configuration and fixtures
├── pytest.ini                    # Pytest settings and markers
├── test_imports.py                # Import validation tests
├── test_real_api_environment.py   # Environment validation tests
├── test_utils/                    # Testing utilities and helpers
│   ├── __init__.py
│   ├── database_fixtures.py       # Database setup/teardown utilities
│   ├── real_generation_engine.py  # Real AI provider factory
│   ├── sample_data.py             # Test data generators
│   └── assertions.py              # Custom test assertions
├── integration/                   # End-to-end integration tests
│   ├── __init__.py
│   ├── test_deconstructor_api.py  # API endpoint tests with real AI
│   └── test_pipeline_flow.py      # Full pipeline integration tests
├── stages/                        # Individual stage tests
│   ├── __init__.py
│   ├── test_stage_1_ingestion.py  # Stage 1: Document ingestion (no AI required)
│   └── test_stage_2_cleaning.py   # Stage 2: Text cleaning with real AI
└── sample_files/                  # Sample files for testing
    ├── README.md                  # Instructions for sample files
    └── test_configs/              # Test configuration files
        ├── minimal_config.json
        └── full_config.json
```

## Environment Setup

### API Keys Required

The test suite requires API keys for at least one AI provider:

```bash
# Gemini (Google) - Recommended
export GEMINI_API_KEY=your-gemini-api-key-here
export GEMINI_MODEL_NAME=gemini-2.0-flash

# OpenAI (Optional)
export OPENAI_API_KEY=your-openai-api-key-here
export OPENAI_MODEL_NAME=gpt-4o-mini

# DeepSeek (Optional)
export DEEPSEEK_API_KEY=your-deepseek-api-key-here
export DEEPSEEK_MODEL_NAME=deepseek-chat
```

### Database Configuration

```bash
# Test database
export TEST_DATABASE_URL="postgresql://postgres:password@postgres-db:5432/runarion_test"

# Test environment paths are managed automatically by the path manager

# Test environment
export ENVIRONMENT="test"
export TESTING="true"
```

### Environment Validation

Check your environment setup before running tests:

```bash
# Run environment validation
python tests/test_real_api_environment.py

# Or run as pytest
pytest tests/test_real_api_environment.py -v
```

## Running Tests

### Prerequisites

1. **Docker Environment**: Ensure your Docker development environment is running
2. **Database**: PostgreSQL with Apache AGE extension must be available
3. **API Keys**: At least one AI provider API key must be set

### Basic Commands

```bash
# Run all tests (requires API keys)
docker exec python-app pytest tests/ -v

# Run specific test categories
docker exec python-app pytest tests/ -m integration -v
docker exec python-app pytest tests/ -m stage -v
docker exec python-app pytest tests/ -m database -v

# Run specific test files
docker exec python-app pytest tests/integration/test_deconstructor_api.py -v
docker exec python-app pytest tests/stages/test_stage_2_cleaning.py -v

# Run with coverage
docker exec python-app pytest tests/ --cov=src --cov-report=html
```

### Running Tests with Specific Sample Files

The test suite can be configured to use specific sample files for testing:

#### **Sample File Selection**

```bash
# Run stage tests with a specific sample file
docker exec python-app pytest tests/stages/test_stage_1_ingestion.py -v \
  --sample-file="short_story.pdf"

# Run integration tests with specific sample file
docker exec python-app pytest tests/integration/test_deconstructor_api.py -v \
  --sample-file="short_story.pdf"

# Run all stage tests with different sample files
docker exec python-app pytest tests/stages/ -v --sample-file="short_story.pdf"
```

#### **Available Sample Files**

Currently available sample files in `tests/sample_files/inputs/`:

- **`short_story.pdf`** - ~2,000 words, basic functionality testing (recommended for development)

Future sample files (when added):

- **`medium_novel.pdf`** - ~20,000 words, medium complexity testing
- **`complex_novel.pdf`** - ~50,000 words, full pipeline stress testing
- **`malformed_document.txt`** - Edge cases and error handling
- **`multilingual_test.txt`** - Unicode and encoding testing

#### **Environment Variables for Sample Files**

You can also specify sample files via environment variables:

```bash
# Set default sample file for all tests
docker exec python-app bash -c "export TEST_SAMPLE_FILE=short_story.pdf && pytest tests/stages/ -v"

# Set sample file and run specific test
docker exec python-app bash -c "export TEST_SAMPLE_FILE=short_story.pdf && pytest tests/stages/test_stage_1_ingestion.py::TestStage1Ingestion::test_pdf_ingestion -v"
```

#### **Test Configuration Files**

Run tests with specific configuration files:

```bash
# Use minimal configuration
docker exec python-app pytest tests/ -v --config-file="minimal_config.json"

# Use performance configuration
docker exec python-app pytest tests/ -v --config-file="performance_config.json"

# Use full configuration
docker exec python-app pytest tests/ -v --config-file="full_config.json"
```

#### **Combined Sample File and Configuration**

```bash
# Run with specific sample file AND configuration
docker exec python-app pytest tests/stages/test_stage_2_cleaning.py -v \
  --sample-file="short_story.pdf" \
  --config-file="performance_config.json"

# Run integration test with custom settings
docker exec python-app pytest tests/integration/test_pipeline_flow.py -v \
  --sample-file="short_story.pdf" \
  --config-file="minimal_config.json" \
  --provider="gemini"
```

#### **Specific Test Examples**

```bash
# Test PDF ingestion with short story
docker exec python-app pytest tests/stages/test_stage_1_ingestion.py::TestStage1Ingestion::test_pdf_ingestion -v \
  --sample-file="short_story.pdf"

# Test text cleaning with specific AI provider
docker exec python-app pytest tests/stages/test_stage_2_cleaning.py::TestStage2Cleaning::test_cleaning_success -v \
  --sample-file="short_story.pdf" \
  --provider="gemini"

# Test full API workflow with sample file
docker exec python-app pytest tests/integration/test_deconstructor_api.py::TestDeconstructorAPI::test_complete_workflow -v \
  --sample-file="short_story.pdf"
```

#### **Adding New Sample Files**

To add and test new sample files:

1. **Add the file** to `tests/sample_files/inputs/`:

   ```bash
   # Copy your new sample file
   cp my_new_novel.pdf tests/sample_files/inputs/
   ```

2. **Test with your new file**:

   ```bash
   # Test ingestion with new file
   docker exec python-app pytest tests/stages/test_stage_1_ingestion.py -v \
     --sample-file="my_new_novel.pdf"
   ```

3. **Run full pipeline test**:
   ```bash
   # Test complete workflow with new file
   docker exec python-app pytest tests/integration/test_pipeline_flow.py -v \
     --sample-file="my_new_novel.pdf" \
     --config-file="minimal_config.json"
   ```

#### **Sample File Debugging**

```bash
# Debug sample file processing with verbose output
docker exec python-app pytest tests/stages/test_stage_1_ingestion.py -v -s \
  --sample-file="short_story.pdf" \
  --log-cli-level=DEBUG

# Check sample file path resolution
docker exec python-app python -c "
from test_utils.path_manager import get_sample_file
print(f'Sample file path: {get_sample_file(\"short_story.pdf\")}')
"
```

### Test Markers

The test suite uses pytest markers to categorize tests:

- `@pytest.mark.integration`: Integration tests requiring full services
- `@pytest.mark.stage`: Tests for individual pipeline stages
- `@pytest.mark.database`: Tests requiring database access
- `@pytest.mark.real_api`: Tests that make real API calls (most tests)
- `@pytest.mark.expensive`: Tests that consume significant API quota/costs
- `@pytest.mark.slow`: Tests that take more than 30 seconds
- `@pytest.mark.api`: Tests for API endpoints
- `@pytest.mark.performance`: Performance and load tests

### Cost-Aware Testing

```bash
# Run all tests except expensive ones
docker exec python-app pytest tests/ -m "not expensive" -v

# Run only expensive tests (use sparingly)
docker exec python-app pytest tests/ -m expensive -v

# Run fast tests only
docker exec python-app pytest tests/ -m "not slow and not expensive" -v

# Run integration tests without expensive ones
docker exec python-app pytest tests/ -m "integration and not expensive" -v
```

### Skipping Tests Without API Keys

Tests automatically skip when API keys are not available:

```bash
# This will skip real API tests if no keys are found
docker exec python-app pytest tests/ -v
```

## Test Features

### Real AI Provider Integration

The test suite uses actual AI providers for realistic testing:

```python
def test_example(generation_engine_factory, db_fixture):
    """Example test using real AI providers."""
    # Check if API keys are available
    available_providers = generation_engine_factory.get_available_providers()
    if not available_providers:
        pytest.skip("No API keys available")

    # Create real generation engine
    engine = generation_engine_factory.create_generation_engine(
        provider="gemini",
        prompt="Test prompt",
        instruction="Test instruction"
    )

    # Use engine for testing...
```

### Database Fixtures

Database fixtures provide transaction isolation and cleanup:

```python
def test_example(db_fixture):
    """Example test using database fixtures."""
    # Create test data
    draft = db_fixture.create_test_draft()
    chunks = db_fixture.create_test_chunks(draft['draft_id'], 3)

    # Test operations
    # ...

    # Automatic cleanup after test
```

### Real API Assertions

Use specialized assertions for real API responses:

```python
from test_utils.assertions import RealAPIAssertions, PipelineAssertions

# Validate real API responses
RealAPIAssertions.assert_successful_generation(response)
RealAPIAssertions.assert_token_usage(response, min_tokens=10)
RealAPIAssertions.assert_processing_time_reasonable(response, max_seconds=30)

# Validate pipeline results
PipelineAssertions.assert_draft_status(status, 'completed')
PipelineAssertions.assert_api_response_structure(response, success=True)
```

## Writing New Tests

### Test Organization

1. **Integration Tests**: Place in `tests/integration/`

   - Test complete workflows with real AI
   - Use real database connections
   - Test API endpoints

2. **Stage Tests**: Place in `tests/stages/`
   - Test individual pipeline stages
   - Use database fixtures
   - Test both success and error conditions

### Test Patterns

Follow these patterns for consistency:

```python
@pytest.mark.real_api
@pytest.mark.database
class TestNewFeature:
    """Test new feature functionality."""

    def test_feature_success(self, generation_engine_factory, db_fixture):
        """Test successful feature execution."""
        # Skip if no API keys
        available_providers = generation_engine_factory.get_available_providers()
        if not available_providers:
            pytest.skip("No API keys available")

        # Test implementation
        # ...

        # Use appropriate assertions
        RealAPIAssertions.assert_successful_generation(result)
        PipelineAssertions.assert_database_record_exists(db_fixture, 'table', 'id')

    @pytest.mark.expensive
    def test_feature_large_input(self, generation_engine_factory, db_fixture):
        """Test feature with large input (expensive test)."""
        # Implementation for high-cost test
        pass
```

### Cost Management

- Mark expensive tests with `@pytest.mark.expensive`
- Include skip logic for missing API keys
- Use realistic but minimal test data
- Document token consumption in test docstrings

## Current Test Coverage

### Available Tests

1. **Stage 1 Tests** (`test_stage_1_ingestion.py`)

   - Document ingestion and chunking
   - File format support
   - Database operations
   - No AI required

2. **Stage 2 Tests** (`test_stage_2_cleaning.py`)

   - Text cleaning with real AI
   - Unicode handling
   - Performance monitoring
   - Error handling

3. **Integration Tests** (`test_deconstructor_api.py`)

   - Complete API workflow
   - Error handling
   - Provider validation
   - Performance monitoring

4. **Pipeline Flow Tests** (`test_pipeline_flow.py`)
   - End-to-end pipeline execution
   - Stage isolation testing
   - Data flow validation
   - Error handling and recovery

### Adding New Stage Tests

To add tests for additional stages (3-7):

1. Create new test file: `tests/stages/test_stage_X_name.py`
2. Follow the pattern from `test_stage_2_cleaning.py`
3. Add appropriate fixtures to `conftest.py`
4. Use real API assertions and cost-aware markers

Example structure:

```python
@pytest.mark.real_api
@pytest.mark.database
class TestStageX:
    """Test Stage X: Description"""

    def test_stage_x_success(self, stage_x_instance, db_fixture):
        """Test successful stage execution."""
        # Implementation
        pass

    @pytest.mark.expensive
    def test_stage_x_large_input(self, stage_x_instance, db_fixture):
        """Test stage with large input."""
        # Implementation
        pass
```

## Debugging Tests

### Verbose Output

```bash
# Run with maximum verbosity
docker exec python-app pytest tests/ -vvv

# Show print statements
docker exec python-app pytest tests/ -s

# Show test durations
docker exec python-app pytest tests/ --durations=10
```

### Environment Issues

```bash
# Check environment
python tests/test_real_api_environment.py

# Validate imports
pytest tests/test_imports.py -v

# Check database connection
pytest tests/conftest.py::test_database_connection -v
```

### API Issues

- Verify API keys are set correctly
- Check network connectivity
- Monitor rate limits and quotas
- Review API provider status pages

## Performance Considerations

### Token Usage

- Real API tests consume tokens and cost money
- Use `@pytest.mark.expensive` for high-consumption tests
- Monitor and optimize test data sizes
- Consider using smaller models for basic testing

### Test Speed

- Database tests use transaction isolation for speed
- Real API calls add network latency
- Use appropriate timeouts
- Run expensive tests selectively

### Best Practices

1. Use minimal test data that still validates functionality
2. Run expensive tests only when necessary
3. Monitor API costs and usage
4. Keep real API tests focused and efficient

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Deconstructor Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Start services
        run: docker-compose -f docker-compose.test.yml up -d

      - name: Run tests (excluding expensive)
        run: |
          docker exec python-app pytest tests/ -v \
            -m "not expensive" \
            --cov=src --cov-report=xml \
            --junitxml=test-results.xml
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}

      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## Troubleshooting

### Common Issues

1. **Missing API Keys**: Tests skip automatically - set environment variables
2. **Database Connection**: Check `TEST_DATABASE_URL` and Docker services
3. **Import Errors**: Run `pytest tests/test_imports.py` to validate setup
4. **Rate Limits**: Use `@pytest.mark.expensive` and run selectively

### Getting Help

- Check existing test examples for patterns
- Review pytest documentation for advanced features
- Examine real API response structures in `RealAPIAssertions`
- Validate environment with `test_real_api_environment.py`

## Contributing

When adding new tests:

1. Follow existing patterns and conventions
2. Add appropriate documentation and markers
3. Include both success and failure scenarios
4. Use cost-aware testing practices
5. Test with multiple providers when possible
6. Add comprehensive error handling

For questions about the test suite, consult existing examples and documentation.
