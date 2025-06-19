from flask import Blueprint, request, jsonify, current_app
from pydantic import ValidationError
from models.request import BaseGenerationRequest
from services.generation_engine import GenerationEngine
from services.usecase_handler.mock_handler import MockHandler
from services.usecase_handler.story_handler import StoryHandler
from models.response import BaseGenerationResponse

generate = Blueprint("generate" , __name__)

USECASE_MAP = {
    "mock" : MockHandler(),
    "story": StoryHandler(),
    # "summarizer": SummarizerHandler(),
}

@generate.route("/generate", methods=["POST"])
def generate_text_route():
    json_data = request.get_json()
    usecase = json_data.get("usecase", "mock")

    handler = USECASE_MAP.get(usecase)
    if not handler:
        return jsonify({"error": f"Unsupported usecase '{usecase}'."}), 400

    try:
        req_obj = handler.build_request(json_data)
        engine = GenerationEngine(req_obj)
        response = engine.generate()
        return jsonify(response.model_dump()), 200
    except Exception as e:
        current_app.logger.error(f"Generation error: {type(e).__name__} - {e}")
        return jsonify({"error": "Failed to generate text.", "message": str(e)}), 500
