# providers/openai_provider.py

import time
import uuid
import openai
from flask import current_app
from openai import OpenAI
from typing import Dict, Generator
from providers.base_provider import BaseProvider
from models.response import BaseGenerationResponse
from models.request import BaseGenerationRequest, GenerationConfig

class OpenAIProvider(BaseProvider):
    def __init__(self, request: BaseGenerationRequest):
        super().__init__(request)

        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            current_app.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def _build_openai_kwargs(self, config: GenerationConfig) -> Dict:
        """
        Transforms the GenerationConfig into a dictionary of kwargs suitable for 
        the OpenAI Chat Completions API.
        """
        messages = []
        if self.instruction:
            messages.append({"role": "system", "content": self.instruction})
        if self.request.prompt:
            messages.append({"role": "user", "content": self.request.prompt})
            
        logit_bias = {}    
        if config.banned_tokens:
            for token_id in config.banned_tokens:
                logit_bias[str(token_id)] = -100
        
        if config.phrase_bias:
            for item in config.phrase_bias:
                for token_id_str, bias_value in item.items():
                    # Ensure token_id_str is a string
                    logit_bias[token_id_str] = bias_value
                
        openai_kwargs = {
            "messages": messages,
            "model" : self.model,
            "frequency_penalty": config.repetition_penalty,
            "presence_penalty": config.repetition_penalty,
            "stop": config.stop_sequences if config.stop_sequences else None,
            "temperature": config.temperature,
            "top_p": config.nucleus_sampling,
            "logit_bias": logit_bias if logit_bias else None,
            "max_tokens": config.max_output_tokens, 
            "stream": config.stream
        }
        
        return {k: v for k, v in openai_kwargs.items() if v is not None}
        
    def generate(self) -> BaseGenerationResponse:
        """
        Generate text in a non-streaming fashion.
        
        Returns:
            BaseGenerationResponse: The generated text and metadata.
        """
        self.request.generation_config.stream = False
        start_time = time.time()
        request_id = str(uuid.uuid4())
        provider_request_id = None
        quota_generation_count = 1
        
        openai_kwargs = self._build_openai_kwargs(self.request.generation_config)
        current_app.logger.info(f"OpenAI API request: {openai_kwargs}")

        try:
            self._check_quota()
        except Exception as e:
            current_app.logger.error(f"OpenAI Quota error with model {self.model}: {e}")
            response = self._build_error_response(
                request_id=request_id,
                provider_request_id=provider_request_id or "",
                error_message=f"OpenAI Quota error: {str(e)}",
            )
            self._log_generation_to_db(response)
            return response

        try:
            raw_response = self.client.chat.completions.create(**openai_kwargs)
            current_app.logger.info(f"OpenAI API response: {raw_response}")
            provider_request_id = getattr(raw_response, 'id', "")

            generated_text = ""
            finish_reason = ""

            if raw_response.choices and len(raw_response.choices) > 0:
                choice = raw_response.choices[0]
                generated_text = choice.message.content or ""
                finish_reason = choice.finish_reason or ""

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
            current_app.logger.error(f"OpenAI API error with model {self.model}: {e}")
            response = self._build_error_response(
                request_id=request_id,
                provider_request_id=provider_request_id or "",
                error_message=f"OpenAI API error: {str(e)}",
            )
            self._log_generation_to_db(response)
            return response
    
    def generate_stream(self) -> Generator[str, None, None]:
        """
        Generate text in a streaming fashion.

        Yields:
            str: Text chunks as they are generated.
        """
        self.request.generation_config.stream = True
        request_id = str(uuid.uuid4())
        provider_request_id = None
        quota_generation_count = 1
        start_time = time.time()

        try:
            self._check_quota()
        except Exception as e:
            current_app.logger.error(f"OpenAI Quota error with model {self.model}: {e}")
            error_response = self._build_error_response(
                request_id=request_id,
                provider_request_id="",
                error_message=f"OpenAI Quota error: {str(e)}"
            )
            self._log_generation_to_db(error_response)
            yield f"Error: {str(e)}"
            return

        openai_kwargs = self._build_openai_kwargs(self.request.generation_config)
        current_app.logger.info(f"OpenAI streaming request: {openai_kwargs}")

        # Collect results
        generated_text = ""
        finish_reason = ""
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        try:
            stream = self.client.chat.completions.create(**openai_kwargs)

            for chunk in stream:
                if hasattr(chunk, 'choices') and chunk.choices:
                    choice = chunk.choices[0]
                    provider_request_id = getattr(chunk, 'id', provider_request_id)

                    if hasattr(choice, 'delta') and hasattr(choice.delta, 'content'):
                        content = choice.delta.content
                        if content:
                            generated_text += content
                            yield content

            # Attempt to get usage metadata from the final response
            try:
                usage = getattr(stream, 'usage', None)
                if usage:
                    input_tokens = getattr(usage, "input_tokens", 0)
                    output_tokens = getattr(usage, "output_tokens", 0)
                    total_tokens = getattr(usage, "total_tokens", 0)
            except Exception as e:
                current_app.logger.warning(f"Failed to parse usage metadata from stream: {e}")

            finish_reason = choice.finish_reason if hasattr(choice, 'finish_reason') else "stop"

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
                provider_request_id=provider_request_id or "",
                quota_generation_count=quota_generation_count,
            )
            self._log_generation_to_db(response)

        except Exception as e:
            current_app.logger.error(f"OpenAI streaming error: {e}")
            error_response = self._build_error_response(
                request_id=request_id,
                provider_request_id=provider_request_id or "",
                error_message=f"OpenAI API error: {str(e)}",
            )
            self._log_generation_to_db(error_response)
            yield f"Error: {str(e)}"

