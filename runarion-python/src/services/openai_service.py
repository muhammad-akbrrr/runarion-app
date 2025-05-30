from flask import current_app
from openai import OpenAI
from models.llm_base import LLMProvider
from models.llm_response import LLMResponse, LLMUsageMetadata

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, default_model: str = "gpt-4.1-nano", default_system_prompt: str = "You are a helpful AI Assistant"):
        super().__init__(api_key, default_model, default_system_prompt)
        try:
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            current_app.logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")

    def generate_text(self, user_prompt: str, system_prompt: str, model_name: str = None, **kwargs) -> str:
        model_to_use = model_name or self.default_model
        final_system_prompt = system_prompt or self.default_system_prompt
        
        try:
            valid_openai_params = {"temperature", "top_p", "max_output_tokens"}
            openai_specific_kwargs = {k: v for k, v in kwargs.items() if k in valid_openai_params}
            openai_specific_kwargs["instructions"] = final_system_prompt

            raw_response = self.client.responses.create(
                model=model_to_use,
                input=user_prompt,
                **openai_specific_kwargs # Pass filtered or specific parameters
            )
            
            generated_text = raw_response.output_text if hasattr(raw_response, 'output_text') else ""
            actual_model_used = getattr(raw_response, 'model', model_to_use)
            finish_reason = getattr(raw_response, 'finish_reason', None)
            raw_usage = getattr(raw_response, 'usage', None)
            if raw_usage:
                usage_data = LLMUsageMetadata(
                    input_tokens=getattr(raw_usage, 'input_tokens', None) ,
                    output_tokens=getattr(raw_usage, 'output_tokens', None),
                    total_tokens=getattr(raw_usage, 'total_tokens', None),
                    processing_time_ms=getattr(raw_response, 'processing_time_ms', None)
                )
            
            response = LLMResponse(
                status= "error" if raw_response.error else "success",
                text=generated_text,
                model_used=actual_model_used,
                finish_reason=finish_reason,
                usage=usage_data
            )
            
            current_app.logger.info(f"Openai Response: '{response}'.")
            return response
        
        except Exception as e:
            current_app.logger.error(f"OpenAI API error with model {model_to_use}: {e}")
            return LLMResponse(
                status="error",
                text="",
                model_used=model_to_use,
                error_message=f"OpenAI API error: {str(e)}",
            )