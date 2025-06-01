import time
import uuid
from flask import current_app
from openai import OpenAI
from models.request import GenerationRequest
from models.response import GenerationResponse
from providers.base_provider import BaseProvider
from services.quota_manager import QuotaManager

class OpenAIProvider(BaseProvider):
    def __init__(self, request: GenerationRequest):
        super().__init__(request)

        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            current_app.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")
        
        self.quota_manager = QuotaManager()

    def generate(self) -> GenerationResponse:
        # Prepare parameters
        model_to_use = self.model
        prompt = self.request.prompt or "<start writing from scratch>"

        gen_cfg = self.request.generation_config
    
        # OpenAI param mapping - adjust as per the SDK you use
        openai_kwargs = {
            "model": model_to_use,
            "input": prompt,
            "instructions": self.build_instruction(),
            "temperature": gen_cfg.temperature,
            "max_output_tokens": gen_cfg.max_output_tokens,
            "top_p": gen_cfg.top_p,
        }

        start_time = time.time()
        # TODO: implement proper request ID and quota generation count
        request_id = str(uuid.uuid4())
        quota_generation_count = 1  # Stub for now
        
        # Check quota before making the API call
        # try:
        #     remaining = self.quota_manager.fetch(self.request.caller)
        #     current_app.logger.info(f"Workspace has {remaining} remaining monthly generations.")
        # except ValueError as e:
        #     current_app.logger.error(f"Quota check failed for caller {self.request.caller} : {e}")
        #     return self._build_error_response(
        #         error_message=f"Quota Manager error: {str(e)}",
        #     )

        try:
            # Call the OpenAI responses endpoint
            raw_response = self.client.responses.create(**openai_kwargs)
            
            # Extract response text and metadata
            generated_text = getattr(raw_response, 'output_text', "")
            finish_reason = getattr(raw_response, 'finish_reason', "")

            usage = getattr(raw_response, 'usage', None) or {}
            input_tokens = getattr(usage, "input_tokens", 0)
            output_tokens = getattr(usage, "output_tokens", 0)
            total_tokens = getattr(usage, "total_tokens", 0)

            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Update quota after successful generation
            # self.quota_manager.update(self.request.caller, quota_generation_count)

            return self._build_response(
                generated_text=generated_text,
                finish_reason=finish_reason,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                processing_time_ms=processing_time_ms,
                request_id=request_id,
                quota_generation_count=quota_generation_count,
            )

        except Exception as e:
            current_app.logger.error(f"OpenAI API error with model {model_to_use}: {e}")
            return self._build_error_response(
                error_message=f"OpenAI API error: {str(e)}",
            )
