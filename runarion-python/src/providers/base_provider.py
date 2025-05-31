import os
from abc import ABC, abstractmethod
from flask import current_app
from typing import Literal
from models.request import GenerationRequest
from models.response import GenerationResponse, UsageMetadata, QuotaMetadata
from services.instruction_builder import InstructionBuilder

class BaseProvider(ABC):
    def __init__(self, request: GenerationRequest):
        self.request = request

        # Determine which API key is actually used: own or default
        self.api_key, self.key_used = self._api_key_resolver()

        self.model = self._resolve_model()

    def _api_key_resolver(self) -> tuple[str, Literal["own", "default"]]:
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
    
    def build_instruction(self) -> str:
        """
        Build the instruction string based on the prompt configuration.
        """
        builder = InstructionBuilder(self.request.prompt_config)
        instruction = builder.build() if self.request.prompt.strip() else builder.build_from_scratch()
        current_app.logger.debug(f"Built instruction:\n {instruction}, {"from scratch" if not self.request.prompt.strip() else "continuation"}")
        return instruction

    @abstractmethod
    def generate(self) -> GenerationResponse:
        """
        Generate text using the specified provider.

        This method must return a GenerationResponse instance with all required fields filled.
        """
        pass
    
    def _build_error_response(
        self,
        error_message: str = "An error occurred during generation.",
    ) -> GenerationResponse:
        """Helper to build an error response object."""

        metadata = UsageMetadata(
            finish_reason="error",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            processing_time_ms=0,
        )

        quota = QuotaMetadata(
            user_id=self.request.caller.user_id,
            workspace_id=self.request.caller.workspace_id,
            project_id=self.request.caller.project_id,
            generation_count=0,
        )

        response = GenerationResponse(
            success=False,
            text="",
            provider=self.request.provider,
            model_used=self.model,
            key_used=self.key_used,
            request_id="",  # You can add a request ID generator or pass it from the controller
            metadata=metadata,
            quota=quota,
            error_message=error_message
        )
        return response

    def _build_response(
        self,
        generated_text: str,
        finish_reason: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        processing_time_ms: int,
        request_id: str,
        quota_generation_count: int,
    ) -> GenerationResponse:
        """Helper to build the standardized response object."""

        metadata = UsageMetadata(
            finish_reason=finish_reason,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            processing_time_ms=processing_time_ms,
        )

        quota = QuotaMetadata(
            user_id=self.request.caller.user_id,
            workspace_id=self.request.caller.workspace_id,
            project_id=self.request.caller.project_id,
            generation_count=quota_generation_count,
        )

        response = GenerationResponse(
            success=True,
            text=generated_text,
            provider=self.request.provider,
            model_used=self.model,
            key_used=self.key_used,
            request_id=request_id,
            metadata=metadata,
            quota=quota,
        )
        return response
