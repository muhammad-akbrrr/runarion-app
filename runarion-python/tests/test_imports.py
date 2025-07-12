"""
Test to verify all imports work correctly.
"""

import pytest


def test_basic_imports():
    """Test that all basic imports work."""
    # Test test utilities
    from test_utils.database_fixtures import DatabaseFixture
    from test_utils.real_generation_engine import RealGenerationEngineFactory
    from test_utils.sample_data import SampleDataGenerator
    from test_utils.assertions import PipelineAssertions, RealAPIAssertions
    
    # Test service imports (only existing/tested stages)
    from services.deconstructor.orchestrator import DeconstructorOrchestrator
    from services.deconstructor.stage_1_ingestion import PDFIngestionStage
    from services.deconstructor.stage_2_cleaning import TextCleaningStage
    # Note: Stages 3-7 are not yet implemented/tested, so they are excluded from import tests
    
    # Test model imports
    from models.deconstructor.status import DraftStatus
    
    # Test utility imports
    from utils.database_utils import safe_insert_text
    from utils.document_processor import DocumentProcessor
    from utils.logging_config import get_pipeline_logger
    
    assert True  # If we get here, all imports worked


def test_sample_data_generation():
    """Test that sample data generation works without faker."""
    from test_utils.sample_data import SampleDataGenerator
    
    generator = SampleDataGenerator()
    
    # Test basic data generation
    draft_data = generator.generate_draft_request()
    assert 'draft_id' in draft_data
    assert 'file_name' in draft_data
    
    user_data = generator.generate_user_data()
    assert 'user_id' in user_data
    assert 'username' in user_data
    
    workspace_data = generator.generate_workspace_data()
    assert 'workspace_id' in workspace_data
    assert 'name' in workspace_data
    
    # Test manuscript generation
    manuscript = generator.generate_manuscript_content(chapter_count=2, words_per_chapter=100)
    assert len(manuscript) > 0
    assert 'Chapter 1' in manuscript
    assert 'Chapter 2' in manuscript


def test_real_generation_engine_factory():
    """Test that real generation engine factory works correctly."""
    from test_utils.real_generation_engine import RealGenerationEngineFactory
    
    # Test factory creation
    factory = RealGenerationEngineFactory()
    assert factory is not None
    
    # Test environment validation
    validation_results = factory.validate_environment()
    assert 'valid' in validation_results
    assert 'available_providers' in validation_results
    assert 'missing_keys' in validation_results
    
    # Test provider availability check
    providers = ['openai', 'gemini', 'deepseek']
    for provider in providers:
        has_key = factory.check_api_key_availability(provider)
        assert isinstance(has_key, bool)
    
    # Test caller info creation
    caller_info = factory.create_test_caller_info()
    assert caller_info.user_id == "1"
    assert caller_info.workspace_id is not None


def test_pytest_markers():
    """Test that pytest markers are working."""
    import pytest
    
    # This should run without errors
    assert hasattr(pytest, 'mark')
    assert hasattr(pytest.mark, 'integration')
    assert hasattr(pytest.mark, 'database')
    assert hasattr(pytest.mark, 'stage')


if __name__ == "__main__":
    test_basic_imports()
    test_sample_data_generation()
    test_real_generation_engine_factory()
    test_pytest_markers()
    print("All import tests passed!")