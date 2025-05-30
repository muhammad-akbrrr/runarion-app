# src/models/llm_base.py
from abc import ABC, abstractmethod
from models.llm_response import LLMResponse, LLMUsageMetadata
from models.llm_request import LLMRequest

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
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Generate text using the LLM provider.

        Args:
            request (LLMRequest): The request object containing user prompt, system prompt, model name, and any additional parameters.

        Returns:
            LLMResponse: Standardized response object containing generated text, usage metadata, and any error messages.

        """
        pass
