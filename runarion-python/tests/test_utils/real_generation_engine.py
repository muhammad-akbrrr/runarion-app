"""
Factory for creating real GenerationEngine instances for testing.
Provides utilities for creating actual GenerationEngine instances with proper configurations.
"""

import os
import uuid
from typing import Dict, Any, Optional
from services.generation_engine import GenerationEngine
from models.request import BaseGenerationRequest, CallerInfo, GenerationConfig


class RealGenerationEngineFactory:
    """
    Factory for creating real GenerationEngine instances for testing.
    Handles proper configuration and API key management.
    """
    
    def __init__(self):
        self.default_config = {
            'temperature': 0.7,
            'max_output_tokens': 1000,
            'min_output_tokens': 50,
            'nucleus_sampling': 0.9,
            'repetition_penalty': 0.0,
            'top_k': 40.0,
            'top_a': 0.0,
            'tail_free_sampling': 1.0,
            'stream': False
        }
        
        self.test_caller_template = {
            'user_id': '1',
            'workspace_id': str(uuid.uuid4()),
            'project_id': str(uuid.uuid4()),
            'session_id': str(uuid.uuid4()),
            'api_keys': {}
        }
    
    def create_generation_engine(
        self,
        provider: str = "gemini",
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        instruction: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        caller_info: Optional[Dict[str, Any]] = None,
        use_env_api_key: bool = True
    ) -> GenerationEngine:
        """
        Create a GenerationEngine instance with proper configuration.
        
        Args:
            provider: AI provider name ('openai', 'gemini', 'deepseek')
            model: Specific model name (uses environment default if not provided)
            prompt: Input prompt for generation
            instruction: System instruction for generation
            generation_config: Configuration overrides
            caller_info: Caller information overrides
            use_env_api_key: Whether to use API key from environment
            
        Returns:
            GenerationEngine instance ready for use
        """
        # Build generation config
        config = self.default_config.copy()
        if generation_config:
            config.update(generation_config)
        
        generation_config_obj = GenerationConfig(**config)
        
        # Build caller info
        caller_data = self.test_caller_template.copy()
        if caller_info:
            caller_data.update(caller_info)
        
        # Handle API keys
        if use_env_api_key:
            # API key will be resolved from environment by the provider
            caller_data['api_keys'] = {}
        else:
            # Use provided API keys
            caller_data['api_keys'] = caller_info.get('api_keys', {}) if caller_info else {}
        
        caller_info_obj = CallerInfo(**caller_data)
        
        # Resolve model from environment if not provided
        if not model:
            model = self._get_default_model(provider)
        
        # Create the generation request
        request = BaseGenerationRequest(
            usecase="deconstructor_test",
            provider=provider,
            model=model,
            prompt=prompt or "",
            instruction=instruction or "",
            generation_config=generation_config_obj,
            caller=caller_info_obj
        )
        
        # Create and return the generation engine
        return GenerationEngine(request)
    
    def _get_default_model(self, provider: str) -> str:
        """Get default model for a provider from environment."""
        env_map = {
            'openai': 'OPENAI_MODEL_NAME',
            'gemini': 'GEMINI_MODEL_NAME',
            'deepseek': 'DEEPSEEK_MODEL_NAME'
        }
        
        env_key = env_map.get(provider)
        if not env_key:
            raise ValueError(f"Unknown provider: {provider}")
        
        model = os.getenv(env_key)
        if not model:
            # Fallback defaults
            defaults = {
                'openai': 'gpt-4o-mini',
                'gemini': 'gemini-2.0-flash',
                'deepseek': 'deepseek-chat'
            }
            model = defaults.get(provider)
        
        return model
    
    def create_test_caller_info(
        self,
        user_id: str = "1",
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        session_id: Optional[str] = None,
        api_keys: Optional[Dict[str, str]] = None
    ) -> CallerInfo:
        """
        Create a CallerInfo object for testing.
        
        Args:
            user_id: User ID for the caller
            workspace_id: Workspace ID (generates UUID if not provided)
            project_id: Project ID (generates UUID if not provided)
            session_id: Session ID (generates UUID if not provided)
            api_keys: API keys dictionary
            
        Returns:
            CallerInfo object for testing
        """
        return CallerInfo(
            user_id=user_id,
            workspace_id=workspace_id or str(uuid.uuid4()),
            project_id=project_id or str(uuid.uuid4()),
            session_id=session_id or str(uuid.uuid4()),
            api_keys=api_keys or {}
        )
    
    def check_api_key_availability(self, provider: str) -> bool:
        """
        Check if API key is available for a provider.
        
        Args:
            provider: Provider name to check
            
        Returns:
            True if API key is available, False otherwise
        """
        env_map = {
            'openai': 'OPENAI_API_KEY',
            'gemini': 'GEMINI_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY'
        }
        
        env_key = env_map.get(provider)
        if not env_key:
            return False
        
        api_key = os.getenv(env_key)
        return api_key is not None and api_key.strip() != ""
    
    def get_available_providers(self) -> list[str]:
        """
        Get list of providers with available API keys.
        
        Returns:
            List of provider names with available API keys
        """
        providers = ['openai', 'gemini', 'deepseek']
        return [p for p in providers if self.check_api_key_availability(p)]
    
    def create_cleaning_stage_engine(
        self,
        provider: str = "gemini",
        chunk_text: Optional[str] = None
    ) -> GenerationEngine:
        """
        Create a GenerationEngine configured for text cleaning stage.
        
        Args:
            provider: AI provider to use
            chunk_text: Text chunk to clean
            
        Returns:
            GenerationEngine configured for cleaning
        """
        prompt = chunk_text or "Sample text chunk that needs cleaning and improvement."
        instruction = """You are a professional text editor. Clean and improve the provided text chunk while preserving the original meaning. Focus on:
- Correcting grammar and spelling errors
- Improving sentence structure and flow
- Enhancing readability
- Maintaining the original tone and style
- Preserving all character names and proper nouns

Return only the cleaned text without any additional commentary."""
        
        return self.create_generation_engine(
            provider=provider,
            prompt=prompt,
            instruction=instruction,
            generation_config={'temperature': 0.3}  # Lower temperature for cleaning
        )
    
    def create_scene_detection_engine(
        self,
        provider: str = "gemini",
        manuscript_text: Optional[str] = None
    ) -> GenerationEngine:
        """
        Create a GenerationEngine configured for scene detection stage.
        
        Args:
            provider: AI provider to use
            manuscript_text: Manuscript text to analyze
            
        Returns:
            GenerationEngine configured for scene detection
        """
        prompt = manuscript_text or "Sample manuscript text with multiple scenes."
        instruction = """Analyze the provided text and identify distinct scenes. For each scene, provide:
- Scene number
- Title/summary
- Setting description
- Characters involved
- Start and end markers in the text
- Estimated word count

Return the analysis in JSON format with a "scenes" array."""
        
        return self.create_generation_engine(
            provider=provider,
            prompt=prompt,
            instruction=instruction,
            generation_config={'temperature': 0.5}
        )
    
    def validate_environment(self) -> Dict[str, Any]:
        """
        Validate the test environment for real API usage.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'available_providers': [],
            'missing_keys': []
        }
        
        # Check for available providers
        available_providers = self.get_available_providers()
        results['available_providers'] = available_providers
        
        if not available_providers:
            results['valid'] = False
            results['errors'].append("No API keys found in environment")
            results['missing_keys'] = ['OPENAI_API_KEY', 'GEMINI_API_KEY', 'DEEPSEEK_API_KEY']
        else:
            # Check for missing keys
            all_providers = ['openai', 'gemini', 'deepseek']
            missing = [p for p in all_providers if p not in available_providers]
            if missing:
                results['missing_keys'] = [f"{p.upper()}_API_KEY" for p in missing]
                results['warnings'].append(f"Missing API keys for providers: {missing}")
        
        # Check for model configuration
        for provider in available_providers:
            model = self._get_default_model(provider)
            if not model:
                results['warnings'].append(f"No default model configured for {provider}")
        
        return results