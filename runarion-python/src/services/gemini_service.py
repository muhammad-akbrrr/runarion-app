from flask import current_app
from google import genai
from models.llm_base import LLMProvider
from models.llm_response import LLMResponse, LLMUsageMetadata

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, default_model: str = "gemini-2.0-flash", default_system_prompt: str = "You are a helpful AI Assistant"):
        super().__init__(api_key, default_model, default_system_prompt)
        try:
            self.client = genai.Client(api_key=api_key)
        except Exception as e:
            current_app.logger.error(f"Failed to configure Gemini client: {e}")
            raise ValueError(f"Failed to configure Gemini client: {str(e)}")

    def generate_text(self, user_prompt: str, system_prompt: str, model_name: str = None, **kwargs) -> str:
        model_to_use = model_name or self.default_model
        final_system_prompt = system_prompt or self.default_system_prompt
        
        try:
            valid_gemini_gen_config_params = {"temperature", "top_p", "top_k", "max_output_tokens"}
            gemini_generation_config = {k: v for k, v in kwargs.items() if k in valid_gemini_gen_config_params}
            gemini_generation_config["system_instruction"] = final_system_prompt

            raw_response = self.client.models.generate_content(
                model=model_to_use,
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(
                    **gemini_generation_config
                )
            )
            
            generated_text = ""
            finish_reason_str = None
            actual_model_used = getattr(raw_response, "model_version", model_to_use)
            error_message_value = None
            usage_data = None
            
            if raw_response.prompt_feedback and raw_response.prompt_feedback.block_reason:
                reason_name = getattr(raw_response.prompt_feedback.block_reason, 'name', str(raw_response.prompt_feedback.block_reason))
                error_message_value = f"Content generation blocked by Gemini. Reason: {reason_name}"
                finish_reason_str = reason_name or "BLOCKED"
            
            if raw_response.candidates:
                candidate = raw_response.candidates[0]
                
                # Extract text from parts
                if candidate.content and candidate.content.parts:
                    generated_text = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text') and part.text)
                
                if candidate.finish_reason:
                    finish_reason_str = getattr(candidate.finish_reason, 'name', str(candidate.finish_reason))
            
            if hasattr(raw_response, 'usage_metadata') and raw_response.usage_metadata:
                usage_meta = raw_response.usage_metadata
                usage_data = LLMUsageMetadata(
                    input_tokens=getattr(usage_meta, 'prompt_token_count', None),
                    output_tokens=getattr(usage_meta, 'candidates_token_count', None),
                    total_tokens=getattr(usage_meta, 'total_token_count', None),
                    processing_time_ms=getattr(raw_response, 'processing_time_ms', None)
                )
            
            response = LLMResponse(
                status="error" if error_message_value else "success",
                text=generated_text,
                model_used=actual_model_used, # Or a more specific field if found from raw_response
                finish_reason=finish_reason_str,
                usage=usage_data,
                error_message=error_message_value,
            )
            
            current_app.logger.info(f"Gemini Response: '{response}'.")
            return response
        
        except Exception as e:
            current_app.logger.error(f"Gemini API error with model {model_to_use}: {e}")
            return LLMResponse(
                status="error",
                text="",
                model_used=model_to_use,
                error_message=f"Gemini API error: {str(e)}",
            )