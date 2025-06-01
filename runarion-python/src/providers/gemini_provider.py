import time
import uuid
from flask import current_app
from google import genai
from models.request import GenerationRequest
from models.response import GenerationResponse
from providers.base_provider import BaseProvider
from services.quota_manager import QuotaManager
from werkzeug.exceptions import Forbidden

class GeminiProvider(BaseProvider):
    def __init__(self, request: GenerationRequest):
        super().__init__(request)

        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            current_app.logger.error(f"Failed to initialize Gemini client: {e}")
            raise ValueError(f"Failed to initialize Gemini client: {str(e)}")
        
        self.quota_manager = QuotaManager()

    def generate(self) -> GenerationResponse:
        # Prepare parameters
        model_to_use = self.model
        prompt = self.request.prompt or "<start writing from scratch>"

        gen_cfg = self.request.generation_config
        
        # Gemini param mapping - adjust as per the SDK you use
        gemini_kwargs = {
            "model": model_to_use,
            "contents": prompt,
            "config": genai.types.GenerateContentConfig(
                system_instruction=self.build_instruction(),
                temperature=gen_cfg.temperature,
                max_output_tokens=gen_cfg.max_output_tokens,
                top_p=gen_cfg.top_p,
                top_k=gen_cfg.top_k,
            ),
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
            # Call the Gemini generate_content endpoint
            raw_response = self.client.models.generate_content(**gemini_kwargs)
            
            # Check for block reason
            if raw_response.prompt_feedback and raw_response.prompt_feedback.block_reason:
                reason_name = getattr(raw_response.prompt_feedback.block_reason, 'name', str(raw_response.prompt_feedback.block_reason))
                error_message = f"Content generation blocked by Gemini. Reason: {reason_name}"
                current_app.logger.warning(error_message)
                return self._build_error_response(
                    error_message=error_message
                )
                
            # Extract text from first candidate
            if raw_response.candidates:
                candidate = raw_response.candidates[0]
                if candidate.content and candidate.content.parts:
                    generated_text = "".join(
                        part.text for part in candidate.content.parts if hasattr(part, "text") and part.text
                    )
                if candidate.finish_reason:
                    finish_reason = getattr(candidate.finish_reason, 'name', str(candidate.finish_reason))

            usage = getattr(raw_response, 'usage_metadata', None) or {}
            input_tokens = getattr(usage, "prompt_token_count", 0)
            output_tokens = getattr(usage, "candidates_token_count", 0)
            total_tokens = getattr(usage, "total_token_count", 0)

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
            current_app.logger.error(f"Gemini API error with model {model_to_use}: {e}")
            return self._build_error_response(
                error_message=f"Gemini API error: {str(e)}",
            )
