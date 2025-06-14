# providers/story_generation/gemini_provider.py

import time
import uuid
from flask import current_app
from google import genai
from models.story_generation.request import StoryGenerationRequest
from models.story_generation.response import StoryGenerationResponse
from providers.story_generation.base_provider import StoryGenerationBaseProvider
from google.genai.types import GenerateContentConfig

class StoryGenerationGeminiProvider(StoryGenerationBaseProvider):
    def __init__(self, request: StoryGenerationRequest):
        super().__init__(request)

        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            current_app.logger.error(f"Failed to initialize Gemini client: {e}")
            raise ValueError(f"Failed to initialize Gemini client: {str(e)}")

    def generate(self) -> StoryGenerationResponse:
        model_to_use = self.model
        prompt = self.request.prompt or "<start writing from scratch>"
        instruction = self.instruction
        gen_cfg = self.request.generation_config

        gemini_kwargs = {
            "model": model_to_use,
            "contents": prompt,
            "config": GenerateContentConfig(
                system_instruction=instruction,
                temperature=gen_cfg.temperature,
                max_output_tokens=gen_cfg.max_output_tokens,
                top_p=gen_cfg.top_p,
                top_k=gen_cfg.top_k,
            ),
        }

        start_time = time.time()
        quota_generation_count = 1
        request_id = str(uuid.uuid4())
        provider_request_id = None

        try:
            self._check_quota()
        except Exception as e:
            current_app.logger.error(f"Gemini Quota error with model {model_to_use}: {e}")
            response = self._build_error_response(
                request_id=request_id,
                provider_request_id="" if not provider_request_id else provider_request_id,
                error_message=f"Gemini Quota error: {str(e)}",
            )
            self._log_generation_to_db(response)
            return response

        try:
            raw_response = self.client.models.generate_content(**gemini_kwargs)
            provider_request_id = getattr(raw_response, 'response_id', "")

            if raw_response.prompt_feedback and raw_response.prompt_feedback.block_reason:
                reason_name = getattr(raw_response.prompt_feedback.block_reason, 'name', str(raw_response.prompt_feedback.block_reason))
                error_message = f"Content generation blocked by Gemini. Reason: {reason_name}"
                current_app.logger.warning(error_message)
                return self._build_error_response(
                    request_id=request_id,
                    provider_request_id=provider_request_id,
                    error_message=error_message
                )

            generated_text = ""
            finish_reason = ""

            if raw_response.candidates:
                candidate = raw_response.candidates[0]
                if candidate.content and candidate.content.parts:
                    generated_text = "".join(
                        part.text for part in candidate.content.parts if hasattr(part, "text") and part.text
                    )
                if candidate.finish_reason:
                    finish_reason = getattr(candidate.finish_reason, 'name', str(candidate.finish_reason))

            usage = getattr(raw_response, 'usage_metadata', None) or {}
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0
            total_tokens = getattr(usage, "total_token_count", 0) or 0

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
            current_app.logger.error(f"Gemini API error with model {model_to_use}: {e}")
            response = self._build_error_response(
                request_id=request_id,
                provider_request_id=provider_request_id or "",
                error_message=f"Gemini API error: {str(e)}",
            )
            self._log_generation_to_db(response)
            return response
