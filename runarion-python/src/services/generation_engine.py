# services/generation_engine.py

import time
from typing import Type, Generator
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
        self.start_time = time.time()
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

    
    def stream(self) -> Generator[str, None, None]:
        print(f"Starting stream for session {self.request.caller.session_id} with provider {self.provider_name}...")
        try:
            # Stream from the provider
            chunk_index = 0
            for chunk in self.provider_instance.generate_stream():
                if chunk:
                    if chunk.startswith("Error:"):
                        yield chunk
                        return
                    else:
                        yield chunk
                        chunk_index += 1
            
            # Log completion
            elapsed_time = time.time() - self.start_time
            print(f"Stream with session {self.request.caller.session_id} completed in {elapsed_time:.2f} seconds, generated {chunk_index} chunks.")

        except Exception as e:
            yield f"Error: {str(e)}"