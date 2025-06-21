# Deconstructor Tests

This directory contains tests for the deconstructor functionality, specifically the story rewrite pipeline.

## Directory Structure

```
deconstructor/
├── __init__.py
├── conftest.py                          # Pytest configuration
├── test_story_rewrite_pipeline.py       # Main test file
├── README.md                            # This file
└── test_pdfs/                           # Test PDF files directory
    ├── __init__.py
    ├── README.md                        # PDF directory documentation
    ├── rough_drafts/                    # User rough draft stories
    │   └── __init__.py
    ├── author_samples/                  # Author sample works
    │   └── __init__.py
    └── expected_outputs/                # Expected output files
        └── __init__.py
```

## Test Files Required

To run the tests, you need to add the following PDF files to the `test_pdfs` directory:

### Required Files:

- `rough_drafts/rough_draft_fantasy_story.pdf` - A sample rough draft story
- `author_samples/author_tolkien_lotr_sample.pdf` - Sample from J.R.R. Tolkien's work
- `author_samples/author_rowling_hp_sample.pdf` - Sample from J.K. Rowling's work

### Optional Files:

- `expected_outputs/expected_tolkien_style_rewrite.pdf` - Expected output for validation

## Running Tests

### Prerequisites

1. **Database Setup**: Ensure you have a test database configured
2. **Environment Variables**: Set up your API keys and database credentials
3. **PDF Files**: Add the required test PDF files to the `test_pdfs` directory

### Environment Variables

```bash
# Database
export DB_HOST=localhost
export DB_NAME=runarion_test
export DB_USER=postgres
export DB_PASSWORD=your_password
export DB_PORT=5432

# API Keys
export OPENAI_API_KEY=your_openai_key
export GEMINI_API_KEY=your_gemini_key
```

### Running Tests

#### Run all deconstructor tests:

```bash
cd runarion-python
python -m pytest tests/deconstructor/ -v
```

#### Run specific test file:

```bash
python -m pytest tests/deconstructor/test_story_rewrite_pipeline.py -v
```

#### Run tests with specific markers:

```bash
# Run only fast tests (skip slow ones)
python -m pytest tests/deconstructor/ -v -m "not slow"

# Run only integration tests
python -m pytest tests/deconstructor/ -v -m "integration"

# Run only tests that require PDFs
python -m pytest tests/deconstructor/ -v -m "requires_pdfs"
```

#### Run tests with coverage:

```bash
python -m pytest tests/deconstructor/ --cov=src/services/deconstructor --cov-report=html
```

## Test Categories

### 1. Unit Tests

- Test individual components in isolation
- Fast execution
- No external dependencies

### 2. Integration Tests

- Test the complete workflow
- Require database and API access
- Marked with `@pytest.mark.integration`

### 3. PDF Tests

- Tests that require PDF files
- Marked with `@pytest.mark.requires_pdfs`
- Will be skipped if PDF files are missing

### 4. Slow Tests

- Tests that take longer to execute
- Marked with `@pytest.mark.slow`
- Can be skipped with `-m "not slow"`

## Test Workflows

### 1. New Author Style Workflow

- Upload rough draft PDF
- Upload author sample PDFs
- Create new author style
- Rewrite story in that style

### 2. Existing Author Style Workflow

- Upload rough draft PDF
- Use existing author style ID
- Rewrite story in that style

### 3. Different Perspectives Test

- Test the same story in different writing perspectives:
  - First person
  - Second person
  - Third person omniscient
  - Third person limited

### 4. Error Handling Tests

- Test invalid file paths
- Test invalid author style IDs
- Test missing required fields

## Adding New Tests

### 1. Create Test PDF Files

Add your test PDF files to the appropriate subdirectory in `test_pdfs/`.

### 2. Write Test Functions

Follow the existing pattern in `test_story_rewrite_pipeline.py`:

```python
def test_your_new_test(self):
    """Test description."""
    if not self.has_test_files:
        self.skipTest("Test PDF files not found.")

    # Your test code here
    request = StoryRewriteRequest(...)
    response = pipeline.process_request(request)

    # Assertions
    self.assertIsNotNone(response)
    # ... more assertions
```

### 3. Add Appropriate Markers

Use pytest markers to categorize your tests:

```python
@pytest.mark.integration
@pytest.mark.slow
def test_complex_workflow(self):
    # Test code
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running tests from the `runarion-python` directory
2. **Database Connection**: Check your database configuration and credentials
3. **Missing PDF Files**: Tests will be skipped if required PDF files are missing
4. **API Key Issues**: Ensure your API keys are valid and have sufficient quota

### Debug Mode

Run tests with more verbose output:

```bash
python -m pytest tests/deconstructor/ -v -s --tb=long
```

### Test Isolation

Each test runs in isolation with its own database connection. The `setUp` and `tearDown` methods ensure proper cleanup.

## Continuous Integration

These tests can be integrated into CI/CD pipelines. Make sure to:

1. Set up test database in CI environment
2. Configure API keys as secrets
3. Add test PDF files to the repository or download them during CI setup
4. Run tests with appropriate markers for CI speed optimization

## Test PDF Files Directory

This directory contains PDF files used for testing the deconstructor functionality.

### Directory Structure

```
test_pdfs/
├── rough_drafts/          # User's rough draft stories for testing
├── author_samples/        # Author sample works for style analysis
└── expected_outputs/      # Expected output files for validation
```

### File Naming Convention

- **Rough Drafts**: `rough_draft_[description].pdf`
- **Author Samples**: `author_[author_name]_[work_title].pdf`
- **Expected Outputs**: `expected_[test_name].pdf`

### Usage

Place your test PDF files in the appropriate subdirectories:

1. **rough_drafts/**: PDF files containing rough draft stories to be rewritten
2. **author_samples/**: PDF files containing sample works from authors for style analysis
3. **expected_outputs/**: PDF files containing expected rewritten outputs (for validation)

### Example Files

You can add sample PDF files here for testing:

- `rough_drafts/rough_draft_fantasy_story.pdf`
- `author_samples/author_tolkien_lotr_sample.pdf`
- `author_samples/author_rowling_hp_sample.pdf`
- `expected_outputs/expected_tolkien_style_rewrite.pdf`

### Note

These files are for testing purposes only and should not contain copyrighted material in production environments.
