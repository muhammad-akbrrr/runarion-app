# providers/base_provider.py

import os
from abc import ABC, abstractmethod
from flask import current_app
from typing import Literal
from models.request import BaseGenerationRequest
from models.response import BaseGenerationResponse

class BaseProvider(ABC):
    def __init__(self, request: BaseGenerationRequest):
        self.request = request
        self.api_key, self.key_used = self._resolve_api_key()
        self.model = self._resolve_model()

    @abstractmethod
    def generate(self) -> BaseGenerationResponse:
        pass

    def _resolve_api_key(self) -> tuple[str, Literal["own", "default"]]:
        key = self.request.caller.api_keys.get(self.request.provider)
        if key and key.strip():
            return key.strip(), "own"

        env_map = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY"
        }

        env_key = env_map.get(self.request.provider)
        if not env_key:
            raise ValueError(f"No fallback API key mapping found for provider: {self.request.provider}")

        default_key = os.getenv(env_key)
        if not default_key:
            raise ValueError(
                f"No API key provided in request and fallback environment variable '{env_key}' is not set."
            )

        current_app.logger.warning("No API key provided in request, using default key.")
        return default_key, "default"

    def _resolve_model(self) -> str:
        if self.request.model and self.request.model.strip():
            return self.request.model.strip()

        env_map = {
            "openai": "OPENAI_MODEL_NAME",
            "gemini": "GEMINI_MODEL_NAME",
            "deepseek": "DEEPSEEK_MODEL_NAME"
        }

        env_key = env_map.get(self.request.provider)
        if not env_key:
            raise ValueError(f"No fallback model mapping found for provider: {self.request.provider}")

        default_model = os.getenv(env_key)
        if not default_model:
            raise ValueError(
                f"No default model provided in request and fallback environment variable '{env_key}' is not set."
            )

        current_app.logger.warning("No model name provided in request, using default model.")
        return default_model