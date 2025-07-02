from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
import json
import traceback
from pydantic import ValidationError
from models.request import BaseGenerationRequest
from services.generation_engine import GenerationEngine
from services.usecase_handler.mock_handler import MockHandler
from services.usecase_handler.story_handler import StoryHandler
from models.response import BaseGenerationResponse

generate = Blueprint("generate", __name__)

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

@generate.route("/stream", methods=["POST"])
def stream_text_route():
    json_data = request.get_json()
    
    # Validate that stream is set to True
    if not json_data.get("stream", False):
        return {"error": "Stream parameter must be set to true for this endpoint"}, 400
    
    # Force stream to be True
    json_data["stream"] = True
    
    if "generation_config" in json_data:
        json_data["generation_config"]["stream"] = True
    else:
        json_data["generation_config"] = {"stream": True}
    
    usecase = json_data.get("usecase", "mock")
    
    handler = USECASE_MAP.get(usecase)
    if not handler:
        return jsonify({"error": f"Unsupported usecase '{usecase}'."}), 400
    
    try:
        req_obj = handler.build_request(json_data)
        current_app.logger.info(f"Built streaming request object: {req_obj}")
                
        if not req_obj.generation_config.stream:
            current_app.logger.warning("Stream flag was not properly set in request object, forcing it now")
            req_obj.generation_config.stream = True

        # Create the streaming engine
        engine = GenerationEngine(req_obj)

        # Return a streaming response
        return Response(
            stream_with_context(stream_generator(engine)),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
            }
        )

    except ValidationError as e:
        current_app.logger.error(f"Validation error: {e}")
        return {"error": "Invalid request data", "details": e.errors()}, 400

def stream_generator(engine):
    """
    Generator function that yields SSE formatted chunks from the streaming engine.
    """
    try:
        # Send initial message
        yield 'data: {"status": "started"}\n\n'
        
        # Stream the chunks
        for chunk in engine.stream():
            if chunk:
                if chunk.startswith("Error:"):
                    # If the chunk is an error message, send an error event
                    error_msg = {"error": chunk[7:], "status": "error"}
                    yield f'data: {json.dumps(error_msg)}\n\n'
                    break
                else:
                    # Otherwise, send the chunk
                    yield f'data: {json.dumps({"chunk": chunk})}\n\n'
                
        # Send completion message
        yield 'data: [DONE]\n\n'
        
    except Exception as e:
        current_app.logger.error(f"Stream generator error: {type(e).__name__} - {e}")
        current_app.logger.error(traceback.format_exc())
        error_msg = {"error": str(e), "status": "error"}
        yield f'data: {json.dumps(error_msg)}\n\n'
        yield 'data: [DONE]\n\n'
