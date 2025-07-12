"""
Test environment validation for real API integration.
Validates that the environment is properly configured for real API testing.
"""

import pytest
import os
from test_utils.real_generation_engine import RealGenerationEngineFactory


class TestRealAPIEnvironment:
    """Test environment setup for real API calls."""
    
    def test_environment_validation(self):
        """Test that environment is properly configured for real API testing."""
        factory = RealGenerationEngineFactory()
        validation_results = factory.validate_environment()
        
        # Print results for debugging
        print(f"Environment validation results: {validation_results}")
        
        # Test should pass even if no API keys are available
        # This allows the test suite to run without requiring API keys
        assert 'valid' in validation_results
        assert 'available_providers' in validation_results
        assert 'missing_keys' in validation_results
        assert 'errors' in validation_results
        assert 'warnings' in validation_results
    
    def test_api_key_detection(self):
        """Test API key detection logic."""
        factory = RealGenerationEngineFactory()
        
        # Test each provider
        providers = ['openai', 'gemini', 'deepseek']
        for provider in providers:
            has_key = factory.check_api_key_availability(provider)
            print(f"Provider {provider}: {'API key available' if has_key else 'No API key'}")
            
            # This is informational - we don't fail if keys are missing
            assert isinstance(has_key, bool)
    
    def test_available_providers_list(self):
        """Test getting list of available providers."""
        factory = RealGenerationEngineFactory()
        available = factory.get_available_providers()
        
        print(f"Available providers: {available}")
        
        # Should return a list (may be empty)
        assert isinstance(available, list)
        
        # All returned providers should be valid
        valid_providers = ['openai', 'gemini', 'deepseek']
        for provider in available:
            assert provider in valid_providers
    
    def test_default_model_resolution(self):
        """Test default model resolution for each provider."""
        factory = RealGenerationEngineFactory()
        
        providers = ['openai', 'gemini', 'deepseek']
        for provider in providers:
            try:
                model = factory._get_default_model(provider)
                print(f"Default model for {provider}: {model}")
                assert model is not None
                assert len(model.strip()) > 0
            except ValueError as e:
                print(f"No default model for {provider}: {e}")
                # This is acceptable - some providers may not have defaults
    
    @pytest.mark.skipif(
        not RealGenerationEngineFactory().get_available_providers(),
        reason="No API keys available for real API testing"
    )
    def test_generation_engine_creation(self):
        """Test creating real generation engines with available providers."""
        factory = RealGenerationEngineFactory()
        available_providers = factory.get_available_providers()
        
        # Test with first available provider
        if available_providers:
            provider = available_providers[0]
            engine = factory.create_generation_engine(
                provider=provider,
                prompt="Test prompt",
                instruction="Test instruction"
            )
            
            assert engine is not None
            assert engine.provider_name == provider
            assert engine.request.prompt == "Test prompt"
            assert engine.request.instruction == "Test instruction"
    
    @pytest.mark.skipif(
        not RealGenerationEngineFactory().get_available_providers(),
        reason="No API keys available for real API testing"
    )
    def test_caller_info_creation(self):
        """Test creating caller info objects."""
        factory = RealGenerationEngineFactory()
        
        # Test with defaults
        caller_info = factory.create_test_caller_info()
        assert caller_info.user_id == "1"
        assert caller_info.workspace_id is not None
        assert caller_info.project_id is not None
        assert caller_info.session_id is not None
        
        # Test with custom values
        custom_caller = factory.create_test_caller_info(
            user_id="test_user",
            workspace_id="test_workspace",
            project_id="test_project",
            session_id="test_session"
        )
        assert custom_caller.user_id == "test_user"
        assert custom_caller.workspace_id == "test_workspace"
        assert custom_caller.project_id == "test_project"
        assert custom_caller.session_id == "test_session"
    
    def test_environment_variables_structure(self):
        """Test that environment variables follow expected structure."""
        expected_env_vars = {
            'GEMINI_API_KEY': 'API key for Gemini provider',
            'OPENAI_API_KEY': 'API key for OpenAI provider',
            'DEEPSEEK_API_KEY': 'API key for DeepSeek provider',
            'GEMINI_MODEL_NAME': 'Default model for Gemini',
            'OPENAI_MODEL_NAME': 'Default model for OpenAI',
            'DEEPSEEK_MODEL_NAME': 'Default model for DeepSeek',
        }
        
        for env_var, description in expected_env_vars.items():
            value = os.getenv(env_var)
            print(f"{env_var}: {'SET' if value else 'NOT SET'} ({description})")
            
            # We don't require these to be set, just test they can be accessed
            # The value will be None if not set, which is acceptable
            assert value is None or isinstance(value, str)
    
    def test_specialized_engine_creation(self):
        """Test creating specialized engines for different stages."""
        factory = RealGenerationEngineFactory()
        available_providers = factory.get_available_providers()
        
        if not available_providers:
            pytest.skip("No API keys available for specialized engine testing")
        
        provider = available_providers[0]
        
        # Test cleaning stage engine
        cleaning_engine = factory.create_cleaning_stage_engine(provider=provider)
        assert cleaning_engine is not None
        assert "clean" in cleaning_engine.request.instruction.lower()
        
        # Test scene detection engine
        scene_engine = factory.create_scene_detection_engine(provider=provider)
        assert scene_engine is not None
        assert "scene" in scene_engine.request.instruction.lower()
        assert "json" in scene_engine.request.instruction.lower()


if __name__ == "__main__":
    # Run environment validation when executed directly
    factory = RealGenerationEngineFactory()
    results = factory.validate_environment()
    
    print("=== Real API Environment Validation ===")
    print(f"Valid: {results['valid']}")
    print(f"Available providers: {results['available_providers']}")
    print(f"Missing keys: {results['missing_keys']}")
    
    if results['errors']:
        print(f"Errors: {results['errors']}")
    
    if results['warnings']:
        print(f"Warnings: {results['warnings']}")
    
    if results['available_providers']:
        print("\nYou can run real API tests with:")
        print("  pytest -m real_api")
        print("  pytest -m expensive  # For tests that consume significant tokens")
    else:
        print("\nTo enable real API testing, set one or more API keys:")
        for key in results['missing_keys']:
            print(f"  export {key}=your-api-key-here")