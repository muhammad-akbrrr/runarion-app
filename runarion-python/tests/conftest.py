"""
Global pytest configuration and fixtures for the Runarion deconstructor pipeline tests.
Provides shared fixtures for database access, real AI providers, and test utilities.
"""

import os
import sys
import pytest
import tempfile
import shutil
import uuid
import urllib.parse
from typing import Dict, Any, Optional, Generator
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
import json
from datetime import datetime

# Add src directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Add tests directory to Python path for test_utils imports
sys.path.insert(0, os.path.dirname(__file__))

# Import test utilities
from test_utils.expected_output_loader import ExpectedOutputLoader
from test_utils.path_manager import get_path_manager, TestPathManager
from test_utils.sample_data import SampleDataGenerator
from test_utils.real_generation_engine import RealGenerationEngineFactory
from test_utils.database_fixtures import DatabaseFixture
from test_utils.stage_dependencies import get_dependency_manager, register_stage_instance, reset_stage_dependencies
from test_utils.output_generator import get_output_generator


def build_test_database_url():
    """Build test database URL with proper URL encoding."""
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "postgres-db")
    port = os.getenv("DB_PORT", "5432")
    database = os.getenv("DB_DATABASE", "runarion")

    # URL-encode the password to handle special characters
    encoded_password = urllib.parse.quote_plus(password)

    return f'postgresql://{user}:{encoded_password}@{host}:{port}/{database}'


TEST_DATABASE_URL = os.getenv('TEST_DATABASE_URL', build_test_database_url())


@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """Setup test environment variables and configurations."""
    # Set test environment variables
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['TESTING'] = 'true'

    # Initialize path manager and ensure directories exist
    path_manager = get_path_manager()
    path_manager.ensure_directories_exist()

    yield

    # Cleanup temporary test outputs only (preserve input files and expected outputs)
    path_manager.cleanup_temp_outputs()


@pytest.fixture(scope='session')
def test_database_pool():
    """Create a test database connection pool for the entire test session."""
    try:
        # Create test database connection pool
        pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=TEST_DATABASE_URL
        )

        # Test connection
        conn = pool.getconn()
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1
        pool.putconn(conn)

        yield pool

    except Exception as e:
        pytest.skip(f"Test database not available: {e}")
    finally:
        if 'pool' in locals():
            pool.closeall()


@pytest.fixture
def db_fixture(test_database_pool):
    """Provide a database fixture with transaction isolation."""
    fixture = DatabaseFixture(test_database_pool)

    # Setup test data
    fixture.setup()

    yield fixture

    # Cleanup test data
    fixture.cleanup()


@pytest.fixture
def generation_engine_factory():
    """Provide a factory for creating real GenerationEngine instances."""
    return RealGenerationEngineFactory()


@pytest.fixture
def test_caller_info(generation_engine_factory):
    """Provide a test caller info object for API calls."""
    factory = generation_engine_factory
    return factory.create_test_caller_info(
        user_id="test_user",
        workspace_id="test_workspace",
        project_id="test_project"
    )


@pytest.fixture
def generation_engine(generation_engine_factory):
    """Provide a real GenerationEngine instance for testing with actual API calls."""
    # Check if API keys are available
    factory = generation_engine_factory
    available_providers = factory.get_available_providers()

    if not available_providers:
        pytest.skip("No API keys available for generation engine testing")

    # Use the first available provider (prefer Gemini)
    provider = "gemini" if "gemini" in available_providers else available_providers[0]

    return factory.create_generation_engine(
        provider=provider,
        prompt="Test prompt for generation",
        instruction="You are a helpful assistant for testing purposes."
    )


@pytest.fixture
def test_data_generator():
    """Provide a test data generator for creating test scenarios."""
    return SampleDataGenerator()




@pytest.fixture
def path_manager():
    """Provide the test path manager instance."""
    return get_path_manager()


@pytest.fixture
def expected_output_loader():
    """Provide the expected output loader instance."""
    return ExpectedOutputLoader()


@pytest.fixture
def test_paths(path_manager):
    """Provide all test paths for easy access."""
    return {
        'inputs': path_manager.inputs_dir,
        'outputs': path_manager.outputs_dir,
        'expected_outputs': path_manager.expected_outputs_dir,
        'temp_outputs': path_manager.temp_outputs_dir,
        'test_configs': path_manager.test_configs_dir,
        'sample_files': path_manager.sample_files_dir
    }



@pytest.fixture
def sample_file_path(path_manager, request):
    """Provide a sample file path for basic testing.

    Note: This fixture will look for existing sample files in the inputs directory.
    If no sample files exist yet, it creates a temporary one for compatibility.
    """
    # Get the sample file name from command line or use default
    sample_filename = request.config.getoption("--sample-file")

    # First, try to find the specified sample file
    sample_file = path_manager.inputs_dir / sample_filename
    if sample_file.exists():
        yield str(sample_file)
        return

    # If specified file doesn't exist, try to find any existing sample files
    existing_file = path_manager.get_sample_file_path()
    if existing_file and existing_file.exists():
        yield str(existing_file)
        return

    # Fallback: create a temporary file if no sample files exist yet
    sample_content = """Chapter 1: The Beginning

It was a dark and stormy night. The rain poured down in torrents, and the wind howled through the trees.

John sat by the window, watching the storm rage outside. He had been waiting for this moment for months,
and now it was finally here. The letter had arrived that morning, changing everything.

Chapter 2: The Journey

The next morning, John packed his bags and set out on the journey that would change his life forever.
He didn't know what lay ahead, but he was determined to face whatever challenges awaited him.

As he walked down the country road, the sun broke through the clouds, casting a warm glow over the landscape.
The storm had passed, and a new day was beginning.
"""

    # Create a sample file in the inputs directory using path manager
    path_manager.inputs_dir.mkdir(parents=True, exist_ok=True)
    temp_sample_file = path_manager.inputs_dir / 'temp_sample.txt'

    with open(temp_sample_file, 'w', encoding='utf-8') as f:
        f.write(sample_content)

    yield str(temp_sample_file)

    # Cleanup temporary file (but preserve user-created sample files)
    if temp_sample_file.exists() and 'temp_sample.txt' in temp_sample_file.name:
        temp_sample_file.unlink()


@pytest.fixture
def sample_draft_data():
    """Provide sample draft data for testing."""
    from test_utils.sample_data import generate_ulid
    return {
        'draft_id': generate_ulid(),
        'file_name': 'test_manuscript.txt',
        'user_id': 1,
        'workspace_id': generate_ulid(),
        'project_id': generate_ulid(),
        'provider': 'openai',
        'model': 'gpt-4o-mini',
        'chaptering_mode': 'flexible',
        'target_chapter_length': 2500
    }


@pytest.fixture
def api_client():
    """Provide a test client for API testing."""
    from app import app

    app.config['TESTING'] = True

    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def test_workspace_data(db_fixture):
    """Create test workspace and user data."""
    from test_utils.sample_data import generate_ulid
    workspace_id = generate_ulid()
    user_id = 1

    # Create test workspace and user
    workspace_data = db_fixture.create_test_workspace(workspace_id, user_id)

    yield workspace_data

    # Cleanup handled by db_fixture


@pytest.fixture
def orchestrator_instance(generation_engine, test_database_pool):
    """Provide a deconstructor orchestrator instance for testing with real API calls."""
    from services.deconstructor.orchestrator import DeconstructorOrchestrator

    orchestrator = DeconstructorOrchestrator(
        generation_engine=generation_engine,
        db_pool=test_database_pool
    )

    yield orchestrator


@pytest.fixture
def stage_1_instance(test_database_pool):
    """Provide a Stage 1 (ingestion) instance for testing."""
    from services.deconstructor.stage_1_ingestion import PDFIngestionStage

    stage = PDFIngestionStage(test_database_pool)

    yield stage


@pytest.fixture
def stage_2_instance(test_database_pool, generation_engine_factory):
    """Provide a Stage 2 (cleaning) instance for testing with real API calls."""
    from services.deconstructor.stage_2_cleaning import TextCleaningStage
    from flask import Flask

    # Create minimal Flask app for testing context
    app = Flask(__name__)
    app.config['TESTING'] = True
    
    with app.app_context():
        # Check if API keys are available
        factory = generation_engine_factory
        available_providers = factory.get_available_providers()

        if not available_providers:
            pytest.skip("No API keys available for generation engine testing")

        # Use the first available provider (prefer Gemini)
        provider = "gemini" if "gemini" in available_providers else available_providers[0]

        # Create a generation engine for cleaning
        generation_engine = factory.create_cleaning_stage_engine(provider=provider)

        stage = TextCleaningStage(test_database_pool, generation_engine)

        yield stage


@pytest.fixture
def register_stage_1_only(stage_1_instance):
    """Register only Stage 1 instance for Stage 1 tests."""
    # Register stage instance with the dependency manager
    register_stage_instance(1, stage_1_instance)
    
    yield
    
    # Clean up stage dependencies after test
    reset_stage_dependencies()


@pytest.fixture  
def register_stages_1_and_2(stage_1_instance, stage_2_instance):
    """Register Stage 1 and Stage 2 instances for Stage 2+ tests."""
    # Register stage instances with the dependency manager
    register_stage_instance(1, stage_1_instance)
    register_stage_instance(2, stage_2_instance)
    
    yield
    
    # Clean up stage dependencies after test
    reset_stage_dependencies()


@pytest.fixture
def output_generator():
    """Provide test output generator instance."""
    return get_output_generator()


@pytest.fixture
def stage_dependency_manager():
    """Provide stage dependency manager instance."""
    return get_dependency_manager()


@pytest.fixture
def dependency_results(request, db_fixture, sample_file_path, stage_dependency_manager):
    """
    Provide dependency results for tests that require previous stages.
    Works with the @requires_previous_stages decorator to ensure stage dependencies.
    """
    # Check if the test function has the @requires_previous_stages decorator
    test_func = request.function
    if not hasattr(test_func, '__wrapped__'):
        # No decorator, return None
        return None
    
    # Look for required stages in the decorator
    required_stages = []
    
    # Check if this is a Stage 2+ test by looking for the decorator pattern
    test_name = request.node.name
    if 'stage_2' in test_name.lower():
        required_stages = [1]  # Stage 2 tests need Stage 1
    elif 'stage_3' in test_name.lower():
        required_stages = [1, 2]  # Stage 3 tests need Stages 1 and 2
    # Add more stages as needed
    
    if not required_stages:
        return None
    
    # Get test configuration
    use_cached_outputs = request.config.getoption("--use-stage-outputs", False)
    skip_dependencies = request.config.getoption("--skip-dependencies", False)
    
    # Enable dependency mode on database fixture
    db_fixture.enable_dependency_mode()
    
    try:
        # Ensure stage dependencies
        dependency_results = stage_dependency_manager.ensure_stage_dependencies(
            required_stages=required_stages,
            db_fixture=db_fixture,
            sample_file_path=sample_file_path,
            use_cached_outputs=use_cached_outputs,
            skip_dependencies=skip_dependencies
        )
        
        # Protect records created by dependency stages from cleanup
        if dependency_results and dependency_results.get('stage_data'):
            for stage_num, stage_data in dependency_results['stage_data'].items():
                if 'draft_id' in stage_data:
                    # Protect the draft and its related records
                    db_fixture.protect_records('drafts', [stage_data['draft_id']])
                    
                    # Also protect chunks that were created
                    chunks_count = db_fixture.count_records('draft_chunks', stage_data['draft_id'])
                    if chunks_count > 0:
                        chunk_ids = db_fixture.execute_query(
                            "SELECT id FROM draft_chunks WHERE draft_id = %s",
                            (stage_data['draft_id'],)
                        )
                        chunk_id_list = [str(row[0]) for row in chunk_ids]
                        db_fixture.protect_records('draft_chunks', chunk_id_list)
        
        return dependency_results
        
    except Exception as e:
        # If dependency resolution fails, skip the test
        import pytest
        pytest.skip(f"Unable to resolve stage dependencies: {e}")


@pytest.fixture
def test_output_options(request):
    """Provide test output configuration options."""
    return {
        'use_stage_outputs': request.config.getoption("--use-stage-outputs"),
        'skip_dependencies': request.config.getoption("--skip-dependencies"),
        'generate_outputs': request.config.getoption("--generate-outputs")
    }


# Parameterized fixtures for different test scenarios


@pytest.fixture(params=['openai', 'gemini', 'deepseek'])
def ai_provider_name(request):
    """Parametrized fixture for testing different AI providers."""
    return request.param


@pytest.fixture(params=['flexible', 'constrained'])
def chaptering_mode(request):
    """Parametrized fixture for testing different chaptering modes."""
    return request.param


@pytest.fixture(params=[1000, 2500, 5000])
def chapter_length(request):
    """Parametrized fixture for testing different chapter lengths."""
    return request.param


@pytest.fixture
def stage_output_validator(expected_output_loader):
    """Provide a validator for stage outputs against expected results."""
    def validator(stage, actual_output, expected_filename):
        """Validate stage output against expected results."""
        return expected_output_loader.validate_output_structure(stage, actual_output, expected_filename)
    return validator


@pytest.fixture
def stage_output_comparator(expected_output_loader):
    """Provide a comparator for stage outputs against expected results."""
    def comparator(stage, actual_output, expected_filename, tolerance=0.01):
        """Compare stage output with expected results."""
        return expected_output_loader.compare_outputs(stage, actual_output, expected_filename, tolerance)
    return comparator


@pytest.fixture
def expected_output_helper(expected_output_loader, path_manager):
    """Provide helper functions for working with expected outputs."""
    class ExpectedOutputHelper:
        def load(self, stage, filename):
            return expected_output_loader.load_expected_output(stage, filename)

        def save(self, stage, filename, data):
            return expected_output_loader.save_expected_output(stage, filename, data)

        def list_files(self, stage):
            return expected_output_loader.list_expected_outputs_for_stage(stage)

        def get_path(self, stage, filename):
            return path_manager.get_expected_output_path(stage, filename)

    return ExpectedOutputHelper()

# Utility fixtures


@pytest.fixture
def temp_directory():
    """Provide a temporary directory for test operations."""
    temp_dir = tempfile.mkdtemp()

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def capture_logs():
    """Capture logs during test execution."""
    import logging
    from io import StringIO

    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)

    # Add handler to relevant loggers
    loggers = [
        logging.getLogger('services.deconstructor'),
        logging.getLogger('utils'),
        logging.getLogger('models')
    ]

    for logger in loggers:
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    yield log_capture

    # Cleanup
    for logger in loggers:
        logger.removeHandler(handler)

# Pytest hooks for custom behavior


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--sample-file",
        action="store",
        default="short_story.pdf",
        help="Sample file to use for testing (from tests/sample_files/inputs/)"
    )
    parser.addoption(
        "--use-stage-outputs",
        action="store_true",
        default=False,
        help="Use pre-generated stage outputs instead of running previous stages"
    )
    parser.addoption(
        "--skip-dependencies",
        action="store_true", 
        default=False,
        help="Skip stage dependency resolution (assume data already exists)"
    )
    parser.addoption(
        "--generate-outputs",
        action="store_true",
        default=True,
        help="Generate test output files after test execution (default: True)"
    )


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Register custom markers
    config.addinivalue_line(
        "markers", "integration: Integration tests requiring full services"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests that take more than 30 seconds"
    )
    config.addinivalue_line(
        "markers", "database: Tests that require database access"
    )
    config.addinivalue_line(
        "markers", "real_api: Tests that make real API calls and consume tokens"
    )
    config.addinivalue_line(
        "markers", "expensive: Tests that consume significant API quota/costs"
    )
    config.addinivalue_line(
        "markers", "stage: Tests for individual pipeline stages"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test paths."""
    for item in items:
        # Add integration marker to integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add database marker to tests that use database fixtures
        if any(fixture in item.fixturenames for fixture in ['db_fixture', 'test_database_pool']):
            item.add_marker(pytest.mark.database)

        # Add stage marker to stage tests
        if "stages" in str(item.fspath):
            item.add_marker(pytest.mark.stage)


def pytest_runtest_setup(item):
    """Setup individual test runs."""
    # Skip integration tests if database is not available
    if item.get_closest_marker("integration"):
        try:
            # Quick database connection test
            import psycopg2
            conn = psycopg2.connect(TEST_DATABASE_URL)
            conn.close()
        except Exception:
            pytest.skip("Integration test requires database connection")

    # Skip real API tests if API keys are not available
    if item.get_closest_marker("real_api"):
        from test_utils.real_generation_engine import RealGenerationEngineFactory
        factory = RealGenerationEngineFactory()
        available_providers = factory.get_available_providers()

        if not available_providers:
            pytest.skip("Real API test requires API keys in environment")


def pytest_sessionstart(session):
    """Session start hook."""
    print("Starting test session")


def pytest_sessionfinish(session, exitstatus):
    """Session finish hook."""
    print(f"Test session finished with exit status: {exitstatus}")
