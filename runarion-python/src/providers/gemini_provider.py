# providers/gemini_provider.py

import time
import uuid
from flask import current_app
from google import genai
from google.genai.types import GenerateContentConfig
from typing import Dict, Any, Generator
from providers.base_provider import BaseProvider
from models.request import BaseGenerationRequest, GenerationConfig
from models.response import BaseGenerationResponse

class GeminiProvider(BaseProvider):
    def __init__(self, request: BaseGenerationRequest):
        super().__init__(request)

        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            current_app.logger.error(f"Failed to initialize Gemini client: {e}")
            raise ValueError(f"Failed to initialize Gemini client: {str(e)}")
    
    def _build_gemini_config(self, config: GenerationConfig) -> Dict[str, Any]:
        """
        Build generation config for Gemini API.
        
        Args:
            config: Generation configuration.
            
        Returns:
            Dict[str, Any]: Gemini generation config.
        """
        gemini_config = {
            "temperature": config.temperature,
            "top_p": config.nucleus_sampling,
            "top_k": int(config.top_k * 40) if config.top_k > 0 else None,
            "max_output_tokens": config.max_output_tokens,
        }
        
        # Add stop sequences if provided
        if config.stop_sequences:
            gemini_config["stop_sequences"] = config.stop_sequences
        
        return {k: v for k, v in gemini_config.items() if v is not None}
    
    def _prepare_prompt_parts(self):
        """
        Prepare prompt parts for Gemini API.
        
        Returns:
            list: List of prompt parts.
        """
        prompt_parts = []
        
        # Add instruction as system prompt
        if self.instruction:
            prompt_parts.append(self.instruction)
        
        # Add user prompt
        if self.request.prompt:
            prompt_parts.append(self.request.prompt)
        
        return prompt_parts
        
    def generate(self) -> BaseGenerationResponse:
        """
        Generate text in a non-streaming fashion.
        
        Returns:
            BaseGenerationResponse: The generated text and metadata.
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())
        provider_request_id = None
        quota_generation_count = 1
        
        # Ensure streaming is disabled for non-streaming generation
        self.request.generation_config.stream = False
        
        # Build Gemini generation config
        generation_config = self._build_gemini_config(self.request.generation_config)
        current_app.logger.info(f"Gemini generation config: {generation_config}")
        
        # Prepare prompt parts
        prompt_parts = self._prepare_prompt_parts()
        current_app.logger.info(f"Gemini prompt parts: {prompt_parts}")

        try:
            self._check_quota()
        except Exception as e:
            current_app.logger.error(f"Gemini Quota error with model {self.model}: {e}")
            response = self._build_error_response(
                request_id=request_id,
                provider_request_id=provider_request_id or "",
                error_message=f"Gemini Quota error: {str(e)}",
            )
            self._log_generation_to_db(response)
            return response

        try:
            # Create the model
            model = self.client.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config
            )
            
            # Generate content
            raw_response = model.generate_content(prompt_parts)
            current_app.logger.info(f"Gemini API response: {raw_response}")
            
            # Extract provider request ID if available
            provider_request_id = getattr(raw_response, 'response_id', "")

            # Extract generated text
            generated_text = ""
            finish_reason = "stop"  # Default finish reason

            if hasattr(raw_response, 'text'):
                generated_text = raw_response.text
            
            # Extract usage information if available
            # Note: Gemini doesn't provide token counts directly
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Update quota
            self._update_quota(quota_generation_count)

            # Build response
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

            # Log generation to DB
            self._log_generation_to_db(response)
            return response

        except Exception as e:
            current_app.logger.error(f"Gemini API error with model {self.model}: {e}")
            response = self._build_error_response(
                request_id=request_id,
                provider_request_id=provider_request_id or "",
                error_message=f"Gemini API error: {str(e)}",
            )
            self._log_generation_to_db(response)
            return response
    
    def generate_stream(self) -> Generator[str, None, None]:
        """
        Generate text in a streaming fashion.
        
        Yields:
            str: Text chunks as they are generated.
        """
        # Ensure streaming is enabled
        self.request.generation_config.stream = True
        
        # Check quota before streaming
        try:
            self._check_quota()
        except Exception as e:
            current_app.logger.error(f"Gemini Quota error with model {self.model}: {e}")
            yield f"Error: {str(e)}"
            return
        
        # Build Gemini generation config
        generation_config = self._build_gemini_config(self.request.generation_config)
        current_app.logger.info(f"Gemini streaming config: {generation_config}")
        
        # Prepare prompt parts
        prompt_parts = self._prepare_prompt_parts()
        current_app.logger.info(f"Gemini streaming prompt parts: {prompt_parts}")
        
        try:
            # Create the model
            model = self.client.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config
            )
            
            # Make the streaming request
            response = model.generate_content(
                prompt_parts,
                stream=True
            )
            
            # Process the stream
            for chunk in response:
                if hasattr(chunk, 'text'):
                    if chunk.text:
                        yield chunk.text
            
            # Update quota after successful streaming
            self._update_quota(1)  # Count as one generation
            
        except Exception as e:
            current_app.logger.error(f"Gemini streaming error: {e}")
            yield f"Error: {str(e)}"
