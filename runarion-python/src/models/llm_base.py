# src/models/llm_base.py
from abc import ABC, abstractmethod
from models.llm_response import LLMResponse, LLMUsageMetadata

class LLMProvider(ABC):
    def __init__(self, api_key: str, default_model: str, default_system_prompt: str):
        if not api_key:
            raise ValueError(f"{self.__class__.__name__} API key is required.")
        self.api_key = api_key
        self.default_model = default_model
        self.default_system_prompt = default_system_prompt

    @abstractmethod
    def generate_text(
        self, 
        user_prompt: str, 
        system_prompt: str, 
        model_name: str = None, 
        **kwargs
    ) -> LLMResponse:
        """
        Generates text based on the user prompt and returns a standardized response.
        
        Args:
            user_prompt (str): The prompt from the user.
            system_prompt (str): The system instruction for the AI.
            model_name (str, optional): Specific model to use, overrides default.
            **kwargs: Additional provider-specific parameters.

        Returns:
            LLMResponse: An object containing the generated text and metadata.
        
        Raises:
            Exception: If a critical error prevents even a standardized error response (e.g., client init failed).
                     Otherwise, errors specific to generation should be in LLMResponse.error_message.
        """
        pass