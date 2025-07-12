# Sample Files Directory

This directory contains input sample files and test configurations for the deconstructor pipeline.

**Note**: The test files in this directory should be provided by the development team. This README serves as a guide for organizing test files.

## Directory Structure

```
tests/
├── sample_files/
│   ├── inputs/           # Sample manuscripts for testing
│   │   ├── short_story.pdf    # ~2,000 words - basic functionality testing (EXISTS)
│   │   # ├── medium_novel.pdf   # ~20,000 words - medium complexity testing (FUTURE)
│   │   # ├── complex_novel.pdf  # ~50,000 words - full pipeline testing (FUTURE)
│   │   # ├── malformed_document.txt # Edge cases and error handling (FUTURE)
│   │   # └── multilingual_test.txt  # Unicode and encoding testing (FUTURE)
│   └── test_configs/     # Test configuration files
│       ├── minimal_config.json
│       ├── full_config.json
│       └── performance_config.json
└── outputs/
    ├── deconstructor/    # Expected results for validation
    │   ├── stage_1/      # Expected chunking results (ACTIVE)
    │   ├── stage_2/      # Expected cleaning results (ACTIVE)
    │   # ├── stage_3/      # Expected scene extraction results (FUTURE)
    │   # ├── stage_4/      # Expected analysis results (FUTURE)
    │   # ├── stage_5/      # Expected coherence check results (FUTURE)
    │   # ├── stage_6/      # Expected enhancement results (FUTURE)
    │   # └── stage_7/      # Expected chaptering results (FUTURE)
    └── temp/             # Runtime test outputs (cleaned up after tests)
```

## File Requirements

### Input Manuscripts (`inputs/`)

- **Format**: PDF and TXT files
- **Size**: Various sizes from 2KB to 5MB
- **Content**: Realistic novel/story content with chapters, scenes, dialogue
- **Encoding**: UTF-8 with various character sets for encoding tests

### Expected Outputs (`../outputs/deconstructor/stage_*`)

- **Format**: JSON files containing expected results for each stage
- **Content**: Realistic outputs that match the input manuscripts
- **Validation**: Used for regression testing and output validation
- **Organization**: Organized by stage number (stage_1, stage_2, etc.)

### Test Configurations (`test_configs/`)

- **minimal_config.json**: Basic configuration for fast testing
- **full_config.json**: Complete configuration for comprehensive testing
- **performance_config.json**: Configuration for performance testing

### Temporary Outputs (`../outputs/temp/`)

- **Purpose**: Runtime test outputs that are cleaned up after test completion
- **Format**: Various formats depending on test requirements
- **Lifecycle**: Automatically managed by test fixtures

## Usage in Tests

Test files are automatically discovered and used by the test suite using the new path management utilities:

```python
# Using the new path management system
from test_utils.path_manager import get_sample_file, get_expected_output
from test_utils.expected_output_loader import load_expected

# Load test manuscript
sample_file = get_sample_file('short_story.txt')
with open(sample_file, 'r') as f:
    manuscript_content = f.read()

# Load expected output
expected_chunks = load_expected(1, 'short_story_chunks.json')

# Or using fixtures in tests
def test_stage_1(sample_file_path, expected_output_helper):
    # sample_file_path is automatically provided
    result = process_file(sample_file_path)

    # Validate against expected output
    expected = expected_output_helper.load(1, 'expected_result.json')
    assert result == expected
```

## Adding New Test Files

1. Add manuscript files to the `inputs/` directory
2. Process files through the pipeline manually to generate expected outputs
3. Save expected outputs in the appropriate `../outputs/deconstructor/stage_*/` subdirectory
4. Update test cases to include new files using the path management utilities

## File Naming Conventions

- **Input manuscripts**: descriptive_name.extension (e.g., `mystery_novel.pdf`)
- **Expected outputs**: manuscript_name_stage.json (e.g., `mystery_novel_stage_1.json`)
- **Test configs**: purpose_config.json (e.g., `performance_config.json`)

## Path Management

The new test suite uses centralized path management via `test_utils.path_manager`:

- **Automatic discovery**: Input files are automatically discovered
- **Stage organization**: Expected outputs organized by pipeline stage
- **Cleanup management**: Temporary files are automatically cleaned up
- **Environment integration**: Paths configurable via environment variables

## Size Guidelines

- **Small files** (< 10KB): Fast unit tests
- **Medium files** (10KB - 100KB): Integration tests
- **Large files** (> 100KB): Performance and stress tests
