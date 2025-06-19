# providers/base_provider.py

import os
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Literal
from flask import current_app

from models.request import BaseGenerationRequest, GenerationConfig
from models.response import BaseGenerationResponse, UsageMetadata, QuotaMetadata
from services.quota_manager import QuotaManager

class BaseProvider(ABC):
    def __init__(self, request: BaseGenerationRequest):
        self.request = request
        self.api_key, self.key_used = self._resolve_api_key()
        self.model = self._resolve_model()
        self.client = None

        # Prepare inputs
        self.prompt = request.prompt or ""
        self.instruction = self._format_instruction(request.instruction)
        self.quota_manager = self._get_quota_manager()
        self.remaining_quota = None

    @abstractmethod
    def generate(self) -> BaseGenerationResponse:
        pass
    
    def _get_quota_manager(self) -> QuotaManager:
        return QuotaManager()
    
    def _check_quota(self):
        self.remaining_quota = self.quota_manager.check_quota(self.request.caller)
        
    def _update_quota(self, quota_generation_count: int):
        self.quota_manager.update_quota(
            caller=self.request.caller,
            expected_quota=self.remaining_quota,
            quota_generation_count=quota_generation_count
        )

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
            raise ValueError(
                f"No fallback API key mapping found for provider: {self.request.provider}")

        default_key = os.getenv(env_key)
        if not default_key:
            raise ValueError(
                f"No API key provided in request and fallback environment variable '{env_key}' is not set."
            )

        current_app.logger.warning(
            "No API key provided in request, using default key.")
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
            raise ValueError(
                f"No fallback model mapping found for provider: {self.request.provider}")
        default_model = os.getenv(env_key)
        if not default_model:
            raise ValueError(
                f"No default model provided in request and fallback environment variable '{env_key}' is not set."
            )

        current_app.logger.warning(
            "No model name provided in request, using default model.")
        return default_model

    def _format_instruction(self, instruction: Optional[object]) -> str:
        if instruction is None:
            return ""
        if isinstance(instruction, str):
            return instruction.strip()
        return str(instruction).strip()

    def _build_response(
        self,
        generated_text: str,
        request_id: str,
        finish_reason: str = "stop",
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        quota_generation_count: int = 0,
        processing_time_ms: int = 0,
        provider_request_id: Optional[str] = None
    ) -> BaseGenerationResponse:
        metadata = UsageMetadata(
            finish_reason=finish_reason,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            processing_time_ms=processing_time_ms
        )

        quota = QuotaMetadata(
            user_id=self.request.caller.user_id,
            workspace_id=self.request.caller.workspace_id,
            project_id=self.request.caller.project_id,
            generation_count=quota_generation_count
        )

        return BaseGenerationResponse(
            success=True,
            text=generated_text,
            provider=self.request.provider,
            model_used=self.model,
            key_used=self.key_used,
            request_id=request_id,
            provider_request_id=provider_request_id,
            metadata=metadata,
            quota=quota
        )

    def _build_error_response(
        self, 
        request_id: str, 
        provider_request_id: str = "",
        error_message: str = "An error occurred during generation."
    ) -> BaseGenerationResponse:
        metadata = UsageMetadata(
            finish_reason="error",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            processing_time_ms=0
        )

        quota = QuotaMetadata(
            user_id=self.request.caller.user_id,
            workspace_id=self.request.caller.workspace_id,
            project_id=self.request.caller.project_id,
            generation_count=0,
        )

        return BaseGenerationResponse(
            success=False,
            text="",
            provider=self.request.provider,
            model_used=self.model,
            key_used=self.key_used,
            request_id=request_id,
            provider_request_id=provider_request_id,
            metadata=metadata,
            quota=quota,
            error_message=error_message
        )
        
    def _log_generation_to_db(self, response: BaseGenerationResponse):
        try:
            with self.quota_manager.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO generation_logs (
                            request_id,
                            provider_request_id,
                            user_id,
                            workspace_id,
                            project_id,
                            provider,
                            model_used,
                            key_used,
                            prompt,
                            instruction,
                            generated_text,
                            success,
                            finish_reason,
                            input_tokens,
                            output_tokens,
                            total_tokens,
                            processing_time_ms,
                            error_message,
                            created_at
                        ) VALUES (
                            %s::UUID, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                        )
                        ON CONFLICT (request_id) DO NOTHING
                    """, (
                        response.request_id,
                        response.provider_request_id or None,
                        int(response.quota.user_id),
                        response.quota.workspace_id,
                        response.quota.project_id,
                        response.provider,
                        response.model_used,
                        response.key_used,
                        self.request.prompt or "",
                        self.instruction or "",
                        response.text or "",
                        response.success,
                        response.metadata.finish_reason,
                        response.metadata.input_tokens,
                        response.metadata.output_tokens,
                        response.metadata.total_tokens,
                        response.metadata.processing_time_ms,
                        response.error_message
                    ))
                    conn.commit()
        except Exception as e:
            current_app.logger.error(f"Failed to log generation to DB: {e}")
