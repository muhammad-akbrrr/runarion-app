from flask import Blueprint, request, jsonify, current_app
from pydantic import ValidationError
from models.request import GenerationRequest
from models.response import GenerationResponse
from providers.openai_provider import OpenAIProvider
from providers.gemini_provider import GeminiProvider
# from providers.deepseek_provider import DeepSeekProvider

generate = Blueprint("generate", __name__)

PROVIDER_MAP = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    # "deepseek": DeepSeekProvider,
}

@generate.route("/generate", methods=["POST"])
def generate_text_route():
    try:
        json_data = request.get_json()
        req_obj = GenerationRequest(**json_data)
        current_app.logger.info(f"Received generation request: {req_obj.model_dump()}")
    except ValidationError as e:
        current_app.logger.warning(f"Validation error: {e.errors()}")
        return jsonify({"error": "Invalid request", "details": e.errors()}), 422

    provider_name = req_obj.provider.lower()

    provider_class = PROVIDER_MAP.get(provider_name)
    if not provider_class:
        return jsonify({
            "error": f"Unsupported provider '{provider_name}'.",
            "supported_providers": list(PROVIDER_MAP.keys())
        }), 400

    try:
        provider_instance = provider_class(req_obj)
        response: GenerationResponse = provider_instance.generate()
        return jsonify(response.model_dump()), 200

    except Exception as e:
        current_app.logger.error(f"Generation error [{provider_name}]: {type(e).__name__} - {e}")
        return jsonify({
            "error": f"Failed to generate text with {provider_name}.",
            "message": str(e)
        }), 500