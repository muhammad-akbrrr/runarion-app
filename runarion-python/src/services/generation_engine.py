# services/generation_engine.py

from typing import Type
from models.request import BaseGenerationRequest
from models.response import BaseGenerationResponse
from providers.openai_provider import OpenAIProvider
from providers.gemini_provider import GeminiProvider
# from providers.deepseek_provider import DeepSeekProvider  # to be implemented
from providers.base_provider import BaseProvider


class GenerationEngine:
    _provider_registry: dict[str, Type[BaseProvider]] = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        # "deepseek": DeepSeekProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_cls: Type[BaseProvider]):
        """Allow dynamic registration of new providers at runtime."""
        cls._provider_registry[name.lower()] = provider_cls

    def __init__(self, request: BaseGenerationRequest):
        self.request = request
        self.provider_name = request.provider.lower()
        self.provider_instance = self._get_provider_instance()

    def _get_provider_instance(self) -> BaseProvider:
        try:
            provider_cls = self._provider_registry[self.provider_name]
            return provider_cls(self.request)
        except KeyError:
            raise ValueError(f"Unsupported provider: {self.provider_name}")
        except Exception as e:
            raise RuntimeError(f"Failed to instantiate provider '{self.provider_name}': {e}")

    def generate(self, skip_quota: bool = False) -> BaseGenerationResponse:
        return self.provider_instance.generate(skip_quota=skip_quota)
