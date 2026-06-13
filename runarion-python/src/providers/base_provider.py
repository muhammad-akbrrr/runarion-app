# providers/base_provider.py

import os
from abc import ABC, abstractmethod
from typing import Optional, Literal, Generator
from flask import current_app

from src.models.request import BaseGenerationRequest
from src.models.response import BaseGenerationResponse, UsageMetadata, QuotaMetadata
from src.services.quota_manager import QuotaManager
from src.utils.token_counter import TokenCounter
from src.utils.tokenizer import TokenizerManager

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
        self.usage_reservation = None
        self.billable_token_counter = TokenCounter(
            provider=self.request.provider,
            model=self.model,
        )
        
        # Process tokenization for phrase bias, banned tokens, and stop sequences
        self._process_tokenization()

    @abstractmethod
    def generate(self, skip_quota: bool = False) -> BaseGenerationResponse:
        """
        Generate text in a non-streaming fashion.
        
        Returns:
            BaseGenerationResponse: The generated text and metadata.
        """
        pass
    
    @abstractmethod
    def generate_stream(self) -> Generator[str, None, None]:
        """
        Generate text in a streaming fashion.
        
        Yields:
            str: Text chunks as they are generated.
        """
        pass
    
    def _get_quota_manager(self) -> QuotaManager:
        return QuotaManager()

    def _estimate_billable_input_tokens(self) -> int:
        segments = [self.instruction, self.prompt]

        conversation_history = getattr(self, "conversation_history", None) or []
        for message in conversation_history:
            role = message.get("role", "")
            parts = message.get("parts", [])
            text = " ".join(
                part.get("text", "")
                for part in parts
                if isinstance(part, dict) and part.get("text")
            )
            segments.append(f"{role}: {text}".strip())

        combined_text = "\n\n".join(segment for segment in segments if segment)
        return self.billable_token_counter.safe_count(combined_text)

    def _estimate_reserved_tokens(self) -> int:
        estimated_input_tokens = self._estimate_billable_input_tokens()
        estimated_output_tokens = max(1, int(self.request.generation_config.max_output_tokens or 0))
        estimated_reasoning_tokens = self._estimate_reasoning_tokens()
        return max(estimated_input_tokens + estimated_output_tokens + estimated_reasoning_tokens, 1)

    def _estimate_reasoning_tokens(self) -> int:
        thinking_budget = getattr(self.request.generation_config, "thinking_budget", None)
        if self.request.provider == "gemini" and thinking_budget and thinking_budget > 0:
            return int(thinking_budget)
        return 0

    def _begin_usage_metering(self):
        self.usage_reservation = self.quota_manager.reserve_tokens(
            caller=self.request.caller,
            estimated_tokens=self._estimate_reserved_tokens(),
            quota_mode=self.request.quota_context.mode,
            workflow_id=self.request.quota_context.workflow_id,
        )

    def _normalize_usage(
        self,
        generated_text: str,
        provider_input_tokens: int = 0,
        provider_output_tokens: int = 0,
        provider_reasoning_tokens: int = 0,
        provider_total_tokens: int = 0,
        usage_source: str = "provider",
    ) -> dict:
        estimated_input_tokens = self._estimate_billable_input_tokens()
        estimated_output_tokens = self.billable_token_counter.safe_count(generated_text or "")

        input_tokens = max(int(provider_input_tokens or 0), 0)
        output_tokens = max(int(provider_output_tokens or 0), 0)
        reasoning_tokens = max(int(provider_reasoning_tokens or 0), 0)
        total_tokens = max(int(provider_total_tokens or 0), 0)

        if total_tokens > 0:
            reasoning_tokens = max(reasoning_tokens, total_tokens - input_tokens - output_tokens)
        elif usage_source != "provider":
            input_tokens = estimated_input_tokens
            output_tokens = estimated_output_tokens

        billable_input_tokens = input_tokens or estimated_input_tokens
        billable_output_tokens = output_tokens or estimated_output_tokens
        billable_reasoning_tokens = reasoning_tokens
        billable_total_tokens = total_tokens or (
            billable_input_tokens + billable_output_tokens + billable_reasoning_tokens
        )

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "reasoning_tokens": reasoning_tokens,
            "total_tokens": total_tokens,
            "billable_input_tokens": billable_input_tokens,
            "billable_output_tokens": billable_output_tokens,
            "billable_reasoning_tokens": billable_reasoning_tokens,
            "billable_total_tokens": billable_total_tokens,
            "token_basis": self.request.provider,
            "usage_source": usage_source,
        }

    def _finalize_usage_metering(self, generated_text: str, normalized_usage: Optional[dict] = None) -> dict:
        normalized_usage = normalized_usage or self._normalize_usage(
            generated_text=generated_text,
            usage_source="estimated",
        )
        workspace_usage_period_id = (self.usage_reservation or {}).get("workspace_usage_period_id")
        reserved_tokens = max(0, int((self.usage_reservation or {}).get("reserved_tokens", 0)))

        self.quota_manager.finalize_usage(
            reservation=self.usage_reservation,
            actual_total_tokens=normalized_usage["billable_total_tokens"],
        )
        self.usage_reservation = None

        return {
            **normalized_usage,
            "workspace_usage_period_id": workspace_usage_period_id,
            "reserved_tokens": reserved_tokens,
        }

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
    
    def _process_tokenization(self):
        """
        Process tokenization for phrase bias, banned tokens, and stop sequences.
        This method updates the generation_config in the request with tokenized values.
        """
        config = self.request.generation_config
        
        # Process phrase bias if it exists
        if config.phrase_bias:
            try:
                tokenized_phrase_bias = TokenizerManager.tokenize_phrase_bias(config.phrase_bias, self.model)
                self.request.generation_config.phrase_bias = tokenized_phrase_bias
                current_app.logger.info(f"Tokenized phrase bias: {tokenized_phrase_bias}")
            except Exception as e:
                current_app.logger.error(f"Error tokenizing phrase bias: {e}")
        
        # Process banned tokens if they exist as strings
        if hasattr(config, 'banned_tokens') and config.banned_tokens:
            try:
                tokenized_banned_tokens = TokenizerManager.tokenize_banned_tokens(config.banned_tokens, self.model)
                self.request.generation_config.banned_tokens = tokenized_banned_tokens
                current_app.logger.info(f"Tokenized banned tokens: {tokenized_banned_tokens}")
            except Exception as e:
                current_app.logger.error(f"Error tokenizing banned tokens: {e}")
        
        # Stop sequences don't need tokenization as they're used as-is by the APIs

    def _build_response(
        self,
        generated_text: str,
        request_id: str,
        finish_reason: str = "stop",
        input_tokens: int = 0,
        output_tokens: int = 0,
        reasoning_tokens: int = 0,
        total_tokens: int = 0,
        quota_generation_count: int = 1,
        processing_time_ms: int = 0,
        provider_request_id: Optional[str] = None,
        usage_source: Optional[str] = None,
    ) -> BaseGenerationResponse:
        metadata = UsageMetadata(
            finish_reason=finish_reason,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total_tokens,
            processing_time_ms=processing_time_ms,
            usage_source=usage_source,
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
            reasoning_tokens=0,
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

    def _log_generation_to_db(self, response: BaseGenerationResponse, billable_usage: Optional[dict] = None):
        try:
            billable_usage = billable_usage or {
                "billable_input_tokens": None,
                "billable_output_tokens": None,
                "billable_reasoning_tokens": None,
                "billable_total_tokens": None,
                "token_basis": self.request.provider,
                "workspace_usage_period_id": None,
                "reserved_tokens": None,
                "usage_source": None,
            }

            with self.quota_manager.get_connection() as conn:
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
                            usecase,
                            feature,
                            token_basis,
                            workspace_usage_period_id,
                            quota_mode,
                            workflow_id,
                            prompt,
                            instruction,
                            generated_text,
                            success,
                            finish_reason,
                            input_tokens,
                            output_tokens,
                            reasoning_tokens,
                            total_tokens,
                            billable_input_tokens,
                            billable_output_tokens,
                            billable_reasoning_tokens,
                            billable_total_tokens,
                            reserved_tokens,
                            usage_source,
                            processing_time_ms,
                            error_message,
                            created_at
                        ) VALUES (
                            %s::UUID, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
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
                        self.request.usecase,
                        self.request.feature or self.request.usecase,
                        billable_usage["token_basis"],
                        billable_usage["workspace_usage_period_id"],
                        self.request.quota_context.mode,
                        self.request.quota_context.workflow_id,
                        self.request.prompt or "",
                        self.instruction or "",
                        response.text or "",
                        response.success,
                        response.metadata.finish_reason,
                        response.metadata.input_tokens,
                        response.metadata.output_tokens,
                        response.metadata.reasoning_tokens,
                        response.metadata.total_tokens,
                        billable_usage["billable_input_tokens"],
                        billable_usage["billable_output_tokens"],
                        billable_usage["billable_reasoning_tokens"],
                        billable_usage["billable_total_tokens"],
                        billable_usage["reserved_tokens"],
                        billable_usage["usage_source"] or response.metadata.usage_source,
                        response.metadata.processing_time_ms,
                        response.error_message
                    ))
                    conn.commit()
        except Exception as e:
            current_app.logger.error(f"Failed to log generation to DB: {e}")
