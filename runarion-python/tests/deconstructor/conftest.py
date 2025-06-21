"""
Pytest configuration for deconstructor tests.
"""

import os
import sys
import pytest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.fixture(scope="session")
def test_pdf_directory():
    """Get the test PDF directory path."""
    return Path(__file__).parent / "test_pdfs"


@pytest.fixture(scope="session")
def test_files_exist(test_pdf_directory):
    """Check if required test files exist."""
    rough_draft = test_pdf_directory / "rough_drafts" / "rough_draft_fantasy_story.pdf"
    author_sample1 = test_pdf_directory / \
        "author_samples" / "author_tolkien_lotr_sample.pdf"
    author_sample2 = test_pdf_directory / \
        "author_samples" / "author_rowling_hp_sample.pdf"

    return {
        "rough_draft": rough_draft.exists(),
        "author_sample1": author_sample1.exists(),
        "author_sample2": author_sample2.exists(),
        "all_exist": rough_draft.exists() and author_sample1.exists() and author_sample2.exists()
    }


@pytest.fixture(scope="session")
def database_config():
    """Database configuration for tests."""
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "database": os.getenv("DB_NAME", "runarion_test"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
        "port": os.getenv("DB_PORT", "5432"),
    }


@pytest.fixture(scope="session")
def api_keys():
    """API keys for testing."""
    return {
        "openai": os.getenv("OPENAI_API_KEY"),
        "gemini": os.getenv("GEMINI_API_KEY"),
    }


def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "requires_pdfs: marks tests that require PDF files"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    for item in items:
        # Mark tests that require PDF files
        if "test_pdfs" in str(item.fspath) or "pdf" in item.name.lower():
            item.add_marker(pytest.mark.requires_pdfs)

        # Mark integration tests
        if "integration" in item.name.lower() or "workflow" in item.name.lower():
            item.add_marker(pytest.mark.integration)

        # Mark slow tests
        if "slow" in item.name.lower() or "pipeline" in item.name.lower():
            item.add_marker(pytest.mark.slow)
