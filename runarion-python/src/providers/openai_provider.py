# providers/openai_provider.py

import time
import uuid
import openai
from flask import current_app
from openai import OpenAI
from providers.base_provider import BaseProvider
from models.response import BaseGenerationResponse
from models.request import BaseGenerationRequest

class OpenAIProvider(BaseProvider):
    def __init__(self, request: BaseGenerationRequest):
        super().__init__(request)

        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            current_app.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")
        
    def generate(self, skip_quota: bool = False) -> BaseGenerationResponse:
        start_time = time.time()
        request_id = str(uuid.uuid4())
        provider_request_id = None
        
        # Set quota_generation_count to 0 if skip_quota is True
        quota_generation_count = 0 if skip_quota else 1
        
        config = self.request.generation_config
        
        openai_kwargs = {
            "model": self.model,
            "input": self.request.prompt or "",
            "instructions": self.instruction or "",
            "temperature": config.temperature,
            "max_output_tokens": config.max_output_tokens,
            "top_p": config.nucleus_sampling,
        }

        # Skip quota check if skip_quota is True
        if not skip_quota:
            try:
                self._check_quota()
            except Exception as e:
                current_app.logger.error(f"OpenAI Quota error with model {self.model}: {e}")
                response = self._build_error_response(
                    request_id=request_id,
                    provider_request_id=provider_request_id or "",
                    error_message=f"OpenAI Quota error: {str(e)}",
                )
                if not skip_quota:
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

            # Skip quota update if skip_quota is True
            if not skip_quota:
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

            # Skip logging to DB if skip_quota is True
            if not skip_quota:
                self._log_generation_to_db(response)
                
            return response

        except Exception as e:
            current_app.logger.error(f"OpenAI API error with model {self.model}: {e}")
            response = self._build_error_response(
                request_id=request_id,
                provider_request_id=provider_request_id or "",
                error_message=f"OpenAI API error: {str(e)}",
            )
            
            # Skip logging to DB if skip_quota is True
            if not skip_quota:
                self._log_generation_to_db(response)
                
            return response
