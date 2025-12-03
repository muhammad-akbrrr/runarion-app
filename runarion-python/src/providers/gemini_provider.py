# providers/gemini_provider.py

import time
import uuid
from flask import current_app
from google import genai
from google.genai.types import GenerateContentConfig, SafetySetting, HarmCategory, HarmBlockThreshold, ThinkingConfig
from typing import Dict, Any, Generator, List, Optional
from providers.base_provider import BaseProvider
from models.request import BaseGenerationRequest, GenerationConfig
from models.response import BaseGenerationResponse


# Supported Gemini models with their configurations
# Model names from: https://ai.google.dev/gemini-api/docs/models
# Thinking budgets from CoAuth reference implementation
SUPPORTED_GEMINI_MODELS = {
    # Gemini 3.0 Pro Preview - Latest with thinking (requires paid API key)
    "gemini-3-pro-preview": {
        "supports_thinking": True,
        "default_thinking_budget": 4096,
        "description": "Gemini 3.0 Pro Preview - Advanced reasoning (Paid)"
    },
    # Gemini 2.5 Pro - Advanced model with thinking
    "gemini-2.5-pro": {
        "supports_thinking": True,
        "default_thinking_budget": 4096,
        "description": "Gemini 2.5 Pro - High quality with thinking"
    },
    # Gemini 2.5 Flash - Fast model with thinking
    "gemini-2.5-flash": {
        "supports_thinking": True,
        "default_thinking_budget": 2048,
        "description": "Gemini 2.5 Flash - Fast with thinking"
    },
    # Gemini 2.0 Flash - Most stable, no thinking support
    "gemini-2.0-flash": {
        "supports_thinking": False,
        "default_thinking_budget": 0,
        "description": "Gemini 2.0 Flash - Fast and stable"
    },
    "gemini-2.0-flash-exp": {
        "supports_thinking": False,
        "default_thinking_budget": 0,
        "description": "Gemini 2.0 Flash Experimental"
    },
    # Gemini 1.5 Pro/Flash - Legacy models
    "gemini-1.5-pro": {
        "supports_thinking": False,
        "default_thinking_budget": 0,
        "description": "Gemini 1.5 Pro"
    },
    "gemini-1.5-flash": {
        "supports_thinking": False,
        "default_thinking_budget": 0,
        "description": "Gemini 1.5 Flash"
    },
}


# Safety settings configured to BLOCK_NONE for all categories
# This ensures unrestricted creative writing capabilities
GEMINI_SAFETY_SETTINGS = [
    SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=HarmBlockThreshold.BLOCK_NONE),
]


class GeminiProvider(BaseProvider):
    def __init__(self, request: BaseGenerationRequest):
        super().__init__(request)

        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            current_app.logger.error(f"Failed to initialize Gemini client: {e}")
            raise ValueError(f"Failed to initialize Gemini client: {str(e)}")
        
        # Validate the model if it's in our supported list
        self._validate_model()
        
        # Conversation history for maintaining context across generations
        # Format: List[Dict[str, Any]] with {"role": "user"|"assistant", "parts": [{"text": "..."}]}
        self.conversation_history: Optional[List[Dict[str, Any]]] = None
    
    def _validate_model(self) -> None:
        """
        Validate and log the model being used.
        Logs a warning if model is not in the supported list but allows it to proceed
        (for forward compatibility with new Gemini models).
        """
        if self.model in SUPPORTED_GEMINI_MODELS:
            model_info = SUPPORTED_GEMINI_MODELS[self.model]
            current_app.logger.info(
                f"Using Gemini model: {self.model} - {model_info['description']} "
                f"(thinking: {model_info['supports_thinking']}, default_budget: {model_info['default_thinking_budget']})"
            )
        else:
            # Allow unknown models but log a warning
            current_app.logger.warning(
                f"Using unrecognized Gemini model: {self.model}. "
                f"Supported models: {list(SUPPORTED_GEMINI_MODELS.keys())}. "
                f"Proceeding with default settings."
            )
    
    def _get_thinking_config(self, config: GenerationConfig) -> Optional[ThinkingConfig]:
        """
        Build the ThinkingConfig based on request config and model capabilities.
        
        CoAuth approach: Set thinking_budget (4096 for pro, 2048 for flash)
        with include_thoughts=False (MUST be False, not None!)
        
        thinking_budget and max_output_tokens should be INDEPENDENT:
        - thinking_budget: how many tokens for internal reasoning
        - max_output_tokens: how many tokens for actual output
        
        Returns:
            ThinkingConfig or None
        """
        # Get model info (use defaults for unknown models)
        model_info = SUPPORTED_GEMINI_MODELS.get(self.model, {
            "supports_thinking": False,
            "default_thinking_budget": 0
        })
        
        # If model doesn't support thinking, return None
        if not model_info.get("supports_thinking", False):
            current_app.logger.info(f"Model {self.model} does not support thinking")
            return None
        
        # Get thinking budget from request or use model default
        if config.thinking_budget is not None:
            thinking_budget = config.thinking_budget
        else:
            thinking_budget = model_info.get("default_thinking_budget", 4096)
        
        # If budget is 0, disable thinking
        if thinking_budget == 0:
            current_app.logger.info(f"Thinking disabled for {self.model} (budget=0)")
            return None
        
        # CoAuth style: set budget with include_thoughts=False
        # CRITICAL: include_thoughts MUST be False, not None!
        current_app.logger.info(f"Thinking enabled for {self.model}: budget={thinking_budget}, include_thoughts=False")
        return ThinkingConfig(thinking_budget=thinking_budget, include_thoughts=False)
    
    def set_conversation_history(self, history: List[Dict[str, Any]]) -> None:
        """
        Set conversation history for this generation.
        
        Args:
            history: List of messages in Gemini format:
                    [{"role": "user", "parts": [{"text": "..."}]}, ...]
        """
        self.conversation_history = history
    
    def _build_gemini_kwargs(self, config: GenerationConfig) -> Dict:
        """
        Transforms the GenerationConfig into a dictionary of kwargs suitable for 
        the Gemini config API.
        
        Key features:
        - Configurable thinking_config based on model and request settings
        - Safety settings always set to BLOCK_NONE for all categories (unrestricted writing)
        - Support for all Gemini models (3.0 Pro, 2.5 Pro, 2.5 Flash, 2.0 Flash, etc.)
        
        CRITICAL FOR THINKING MODELS:
        - Gemini's max_output_tokens is the TOTAL limit for thinking + response combined
        - When thinking is enabled, we must set max_output_tokens = thinking_budget + desired_output
        - Otherwise the model hits MAX_TOKENS after thinking, with almost no actual output
        """
        # Note: Gemini doesn't support logit_bias directly like OpenAI does
        
        all_stop_sequences = config.stop_sequences or []
        # if hasattr(config, 'banned_tokens') and config.banned_tokens:
        #     all_stop_sequences.extend(config.banned_tokens)
        
        # Use conversation history if provided, otherwise use prompt
        contents = self.conversation_history if self.conversation_history else (self.request.prompt or "")
        
        # Get thinking config based on model and request settings
        thinking_config = self._get_thinking_config(config)
        
        # Calculate the actual max_output_tokens to send to Gemini
        # For thinking models: max_output_tokens must include BOTH thinking AND response tokens
        # Otherwise the model hits MAX_TOKENS after thinking with almost no actual output
        actual_max_output_tokens = config.max_output_tokens
        
        if thinking_config is not None:
            # Get the thinking budget we're using
            thinking_budget = thinking_config.thinking_budget if thinking_config.thinking_budget else 0
            # Add thinking budget to max_output_tokens so the model has room for BOTH
            actual_max_output_tokens = thinking_budget + config.max_output_tokens
            current_app.logger.info(
                f"Thinking model: adjusting max_output_tokens from {config.max_output_tokens} to "
                f"{actual_max_output_tokens} (thinking_budget={thinking_budget} + desired_output={config.max_output_tokens})"
            )
                
        gemini_kwargs = {
            "model": self.model,
            "contents": contents,
            "config": GenerateContentConfig(
                system_instruction=self.instruction or "",
                temperature=config.temperature,
                max_output_tokens=actual_max_output_tokens,
                top_p=config.nucleus_sampling,
                top_k=int(config.top_k) if config.top_k > 0 else None,
                stop_sequences=all_stop_sequences,
                presence_penalty=config.repetition_penalty if config.repetition_penalty != 0 else None,
                frequency_penalty=config.repetition_penalty if config.repetition_penalty != 0 else None,
                # Configurable thinking config - None disables thinking, otherwise uses configured budget
                thinking_config=thinking_config,
                # CRITICAL: Safety settings MUST be BLOCK_NONE for all categories
                # This ensures unrestricted creative writing for all models
                safety_settings=GEMINI_SAFETY_SETTINGS
            ),
        }
        
        return {k: v for k, v in gemini_kwargs.items() if v is not None}
        
    def generate(self, skip_quota: bool = False) -> BaseGenerationResponse:
        """
        Generate text in a non-streaming fashion.
        
        Returns:
            BaseGenerationResponse: The generated text and metadata.
        """
        self.request.generation_config.stream = False
        start_time = time.time()
        request_id = str(uuid.uuid4())
        provider_request_id = None
        quota_generation_count = 0 if skip_quota else 1
        
        # Build Gemini generation config
        gemini_kwargs = self._build_gemini_kwargs(self.request.generation_config)
        current_app.logger.info(f"Gemini generation kwargs: {gemini_kwargs}")

        # Skip quota check if skip_quota is True
        if not skip_quota:
            try:
                self._check_quota()
            except Exception as e:
                current_app.logger.error(f"Gemini Quota error with model {self.model}: {e}")
                response = self._build_error_response(
                    request_id=request_id,
                    provider_request_id=provider_request_id or "",
                    error_message=f"Gemini Quota error: {str(e)}",
                )
                if not skip_quota:
                    self._log_generation_to_db(response)
                return response

        try:
            # Create the model
            raw_response = self.client.models.generate_content(**gemini_kwargs)
            current_app.logger.info(f"Gemini API response: {raw_response}")
            provider_request_id = getattr(raw_response, 'response_id', "")
            
            if raw_response.prompt_feedback and raw_response.prompt_feedback.block_reason:
                reason_name = getattr(raw_response.prompt_feedback.block_reason, 'name', str(raw_response.prompt_feedback.block_reason))
                error_message = f"Content generation blocked by Gemini. Reason: {reason_name}"
                current_app.logger.warning(error_message)
                response = self._build_error_response(
                    request_id=request_id,
                    provider_request_id=provider_request_id,
                    error_message=error_message
                )
                if not skip_quota:
                    self._log_generation_to_db(response)
                return response

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
            input_tokens = getattr(usage, "prompt_token_count", 0)
            output_tokens = getattr(usage, "candidates_token_count", 0)
            total_tokens = getattr(usage, "total_token_count", 0)

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
            current_app.logger.error(f"Gemini API error with model {self.model}: {e}")
            response = self._build_error_response(
                request_id=request_id,
                provider_request_id=provider_request_id or "",
                error_message=f"Gemini API error: {str(e)}",
            )
            
            # Skip logging to DB if skip_quota is True
            if not skip_quota:
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
        start_time = time.time()
        request_id = str(uuid.uuid4())
        provider_request_id = None
        quota_generation_count = 1
        
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
            yield f"Error: {str(e)}"
            return response
        
        # Build Gemini generation config
        gemini_kwargs = self._build_gemini_kwargs(self.request.generation_config)
        current_app.logger.info(f"Gemini generation kwargs: {gemini_kwargs}")
        
        generated_text = ""
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        finish_reason = "stop"

        try:
            # Streaming API call - following CoAuth's simple approach
            current_app.logger.info(f"Starting Gemini streaming with model: {self.model}")
            stream = self.client.models.generate_content_stream(**gemini_kwargs)
            
            # Check if stream is valid
            if stream is None:
                current_app.logger.error(f"Gemini API returned None stream for model {self.model}")
                yield "Error: Gemini API returned empty stream. Please try again or use a different model."
                return

            chunk_count = 0
            # Process each chunk from the stream
            for chunk in stream:
                chunk_count += 1
                
                # Get response ID if available
                if hasattr(chunk, 'response_id'):
                    provider_request_id = chunk.response_id

                try:
                    # First, try the simple approach: chunk.text directly
                    # This works for non-thinking models (2.0 Flash, etc.)
                    text = chunk.text if hasattr(chunk, 'text') else None
                    if text:
                        generated_text += text
                        yield text
                    else:
                        # For thinking models (2.5 Pro, 2.5 Flash, 3.0 Pro), 
                        # chunk.text may not be available directly.
                        # We need to extract text from candidates' parts,
                        # skipping any thinking parts (thought=True).
                        if hasattr(chunk, 'candidates') and chunk.candidates:
                            for cand in chunk.candidates:
                                # Capture finish reason if present
                                if hasattr(cand, 'finish_reason') and cand.finish_reason:
                                    finish_reason = str(cand.finish_reason)
                                
                                # Extract text from content parts
                                if hasattr(cand, 'content') and cand.content:
                                    if hasattr(cand.content, 'parts') and cand.content.parts:
                                        for part in cand.content.parts:
                                            # Skip thinking parts - only yield actual output
                                            is_thought = getattr(part, 'thought', False)
                                            if is_thought:
                                                continue
                                            
                                            # Get the text from this part
                                            part_text = getattr(part, 'text', None)
                                            if part_text:
                                                generated_text += part_text
                                                yield part_text
                                                
                except (AttributeError, TypeError) as e:
                    # Some chunks might have unexpected structure
                    current_app.logger.warning(f"Chunk {chunk_count} error: {e}")
                    continue

            current_app.logger.info(f"Gemini streaming completed. Chunks: {chunk_count}, Generated length: {len(generated_text)}, Finish reason: {finish_reason}")

            # Final usage data (Gemini stream does NOT return this currently, set 0s safely)
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
                quota_generation_count=quota_generation_count
            )

            self._log_generation_to_db(response)

        except Exception as e:
            import traceback
            current_app.logger.error(f"Gemini streaming error with model {self.model}: {e}")
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            current_app.logger.error(f"Generated so far: {len(generated_text)} chars")
            
            # Log the error response
            error_response = self._build_error_response(
                request_id=request_id,
                provider_request_id=provider_request_id or "",
                error_message=f"Gemini streaming error: {str(e)}"
            )
            self._log_generation_to_db(error_response)
            yield f"Error: {str(e)}"
        
        
