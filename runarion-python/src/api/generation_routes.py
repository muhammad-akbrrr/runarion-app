# api/generation_routes.py

from flask import Blueprint, request, jsonify, current_app
import os
from models.llm_base import LLMProvider
from models.llm_response import LLMResponse
from services.openai_service import OpenAIProvider
from services.gemini_service import GeminiProvider

generate = Blueprint('generate', __name__)

# --- Constants ---
DEFAULT_SYSTEM_PROMPT = "You are a helpful AI Assistant."

# --- API Endpoint ---
@generate.route('/generate', methods=['POST'])
def generate_text_route():
    """
    Generates text using a configured provider (OpenAI or Gemini).
    Expects JSON payload:
    {
        "prompt": "Your prompt here",
        "provider": "openai" | "gemini", (optional, defaults to 'openai')
        "model": "specific-model-name", (optional, uses provider's default if not specified)
        "system_prompt": "Custom system prompt", (optional, uses default if not specified)
        "params": { ... provider-specific parameters ... } (optional)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400
    
    user_prompt = data.get('prompt')
    if not user_prompt:
        return jsonify({"error": "Missing 'prompt' in request body"}), 400

    provider_name = data.get('provider', 'openai').lower()
    model_name_override = data.get('model')
    custom_system_prompt = data.get('system_prompt', DEFAULT_SYSTEM_PROMPT)
    provider_specific_params = data.get('params', {})


    current_app.logger.info(
        f"Generation request: provider='{provider_name}', model='{model_name_override or 'default'}', "
        f"prompt='{user_prompt[:50]}...'"
    )

    provider_instance: LLMProvider
    llm_response: LLMResponse

    try:
        if provider_name == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            default_model = os.getenv('OPENAI_MODEL_NAME', "gpt-4.1-nano") # Your original desired default
            if not api_key:
                current_app.logger.error("OPENAI_API_KEY not found.")
                return jsonify({"error": "OpenAI API key not configured on the server."}), 500
            current_app.logger.info(f"Using OpenAI model: {default_model} with API key: {api_key[:4]}") # Log first 4 chars for security
            provider_instance = OpenAIProvider(api_key=api_key, default_model=default_model)
        
        elif provider_name == 'gemini':
            api_key = os.getenv('GEMINI_API_KEY') # Make sure this is set in your .env
            default_model = os.getenv('GEMINI_MODEL_NAME', "gemini-1.5-flash")
            if not api_key:
                current_app.logger.error("GEMINI_API_KEY not found.")
                return jsonify({"error": "Gemini API key not configured on the server."}), 500
            current_app.logger.info(f"Using Gemini model: {default_model} with API key: {api_key[:4]}")
            provider_instance = GeminiProvider(api_key=api_key, default_model=default_model)
            
        else:
            return jsonify({"error": f"Unsupported provider: '{provider_name}'. Supported providers: 'openai', 'gemini'."}), 400

        llm_response = provider_instance.generate_text(
            user_prompt=user_prompt,
            system_prompt=custom_system_prompt,
            model_name=model_name_override,
            **provider_specific_params
        )
        
        return jsonify(llm_response)

    except ValueError as ve: # Catch configuration/setup errors or specific provider value errors
        current_app.logger.error(f"Configuration or input error for provider {provider_name}: {ve}")
        return jsonify({"error": str(ve)}), 400 if "API key" not in str(ve).lower() else 500
    except Exception as e:
        current_app.logger.error(f"Error during text generation with provider '{provider_name}': {type(e).__name__} - {e}")
        # This catches errors re-raised from the provider's generate_text method
        return jsonify({"error": f"Error communicating with {provider_name}: {str(e)}"}), 500