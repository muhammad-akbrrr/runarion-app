# api/generation_routes.py

from flask import Blueprint, request, jsonify, current_app
import os

from pydantic import ValidationError
from models.llm_base import LLMProvider
from models.llm_response import LLMResponse
from models.llm_request import BaseRequest, LLMRequest
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
    
    try:
        json_data = request.get_json()
        req_data = BaseRequest(**json_data)
    except ValidationError as e:
        current_app.logger.warning(f"Request validation failed: {e.errors()}")
        return jsonify({"error": "Invalid request body", "details": e.errors()}), 422 # Unprocessable Entity

    provider_name = req_data.provider
    
    llm_req = LLMRequest.from_base_request(req_data)
    provider_instance: LLMProvider
    llm_response: LLMResponse

    try:
        if provider_name == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                current_app.logger.error("OPENAI_API_KEY not found.")
                return jsonify({"error": "OpenAI API key not configured on the server."}), 500

            if not llm_req.model:
                current_app.logger.warning("Model not set, using default.")
                llm_req.model = os.getenv('OPENAI_MODEL_NAME', "gpt-4.1-nano")

            current_app.logger.info(f"Using OpenAI model: {llm_req.model} with API key: {api_key[:4]}")  # Log first 4 chars for security
            provider_instance = OpenAIProvider(api_key=api_key)
        elif provider_name == 'gemini':
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                current_app.logger.error("GEMINI_API_KEY not found.")
                return jsonify({"error": "Gemini API key not configured on the server."}), 500
            
            if not llm_req.model:
                current_app.logger.warning("Model not set, using default.")
                llm_req.model = os.getenv('GEMINI_MODEL_NAME', "gemini-1.5-flash")
            
            current_app.logger.info(f"Using Gemini model: {llm_req.model} with API key: {api_key[:4]}")
            provider_instance = GeminiProvider(api_key=api_key)
            
        else:
            return jsonify({"error": f"Unsupported provider: '{provider_name}'. Supported providers: 'openai', 'gemini'."}), 400

        llm_response = provider_instance.generate_text(llm_req)
        
        return jsonify(llm_response)

    except Exception as e:
        current_app.logger.error(f"Error during text generation with provider '{provider_name}': {type(e).__name__} - {e}")
        return jsonify({"error": f"Error communicating with {provider_name}: {str(e)}"}), 500