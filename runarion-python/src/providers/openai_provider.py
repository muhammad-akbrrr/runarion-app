import time
import uuid
from flask import current_app
from openai import OpenAI
from models.request import GenerationRequest
from models.response import GenerationResponse
from providers.base_provider import BaseProvider
from models.request import CallerInfo  # Ensure CallerInfo is available


class OpenAIProvider(BaseProvider):
    def __init__(self, request: GenerationRequest):
        super().__init__(request)

        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            current_app.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")
        
        self.caller = self.request.caller
        self.quota_manager = self._get_quota_manager()
        self.remaining_quota = None

    def generate(self) -> GenerationResponse:
        model_to_use = self.model
        prompt = self.request.prompt or "<start writing from scratch>"
        instruction = self.instruction
        gen_cfg = self.request.generation_config

        openai_kwargs = {
            "model": model_to_use,
            "input": prompt,
            "instructions": instruction,
            "temperature": gen_cfg.temperature,
            "max_output_tokens": gen_cfg.max_output_tokens,
            "top_p": gen_cfg.top_p,
        }

        start_time = time.time()
        quota_generation_count = 1
        request_id = str(uuid.uuid4())
        provider_request_id = None
        
        try:
            self._check_quota()
        except Exception as e:
            current_app.logger.error(f"OpenAI Quota error with model {model_to_use}: {e}")
            response = self._build_error_response(
                request_id=request_id,
                provider_request_id="" if not provider_request_id else provider_request_id,
                error_message=f"OpenAI Quota error: {str(e)}",
            )
            
            self._log_generation_to_db(response)
            return response

        try:
            raw_response = self.client.responses.create(**openai_kwargs)
            provider_request_id = getattr(raw_response, 'id', "")

            generated_text = getattr(raw_response, 'output_text', "")
            finish_reason = getattr(raw_response, 'finish_reason', "")

            usage = getattr(raw_response, 'usage', None) or {}
            input_tokens = getattr(usage, "input_tokens", 0)
            output_tokens = getattr(usage, "output_tokens", 0)
            total_tokens = getattr(usage, "total_tokens", 0)

            processing_time_ms = int((time.time() - start_time) * 1000)

            self._update_quota(quota_generation_count)

            response = self._build_response(
                generated_text=generated_text,
                finish_reason=finish_reason,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                processing_time_ms=processing_time_ms,
                request_id=request_id,
                provider_request_id=provider_request_id,
                quota_generation_count=quota_generation_count,
            )

            self._log_generation_to_db(response)
            return response

        except Exception as e:
            current_app.logger.error(f"OpenAI API error with model {model_to_use}: {e}")
            response = self._build_error_response(
                request_id=request_id,
                provider_request_id="" if not provider_request_id else provider_request_id,
                error_message=f"OpenAI API error: {str(e)}",
            )
            
            self._log_generation_to_db(response)
            return response
