from flask import Blueprint, request, current_app, Response, stream_with_context
from pydantic import ValidationError
import json
import time
import traceback

from models.request import BaseGenerationRequest
from models.streaming import StreamingRequest
from services.streaming_engine import StreamingEngine
from services.usecase_handler.story_handler import StoryHandler
from services.usecase_handler.mock_handler import MockHandler

stream_bp = Blueprint("stream", __name__)

USECASE_MAP = {
    "mock": MockHandler(),
    "story": StoryHandler(),
}

@stream_bp.route("/stream", methods=["POST"])
def stream_text_route():
    """
    Endpoint for streaming text generation.
    
    This endpoint accepts a JSON payload with the following structure:
    {
        "usecase": "story",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "prompt": "Once upon a time",
        "instruction": "Continue the story",
        "stream": true,
        "generation_config": {
            "temperature": 0.7,
            ...
        },
        "prompt_config": {
            "context": "...",
            "genre": "...",
            ...
        },
        "caller": {
            "user_id": "123",
            "workspace_id": "456",
            "project_id": "789",
            "session_id": "abc-123",
            "api_keys": {
                "openai": "...",
                ...
            }
        }
    }
    
    Returns a stream of Server-Sent Events (SSE) with the generated text chunks.
    """
    try:
        json_data = request.get_json()
        
        # Validate that stream is set to True
        if not json_data.get("stream", False):
            return {"error": "Stream parameter must be set to true for this endpoint"}, 400
        
        # Force stream to be True
        json_data["stream"] = True
        
        # Get the usecase handler
        usecase = json_data.get("usecase", "mock")
        handler = USECASE_MAP.get(usecase)
        if not handler:
            return {"error": f"Unsupported usecase '{usecase}'."}, 400
        
        # Build the request object
        try:
            req_obj = handler.build_request(json_data)
            
            # Create a streaming request
            streaming_req = StreamingRequest(
                base_request=req_obj,
                session_id=json_data.get("caller", {}).get("session_id", "")
            )
            
            # Create the streaming engine
            engine = StreamingEngine(streaming_req)
            
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
        
    except Exception as e:
        current_app.logger.error(f"Stream error: {type(e).__name__} - {e}")
        current_app.logger.error(traceback.format_exc())
        return {"error": "Failed to process streaming request", "message": str(e)}, 500

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
                    print(f'data: {json.dumps({"chunk": chunk})}\n\n')
                    yield f'data: {json.dumps({"chunk": chunk})}\n\n'
                
        # Send completion message
        yield 'data: [DONE]\n\n'
        
    except Exception as e:
        current_app.logger.error(f"Stream generator error: {type(e).__name__} - {e}")
        current_app.logger.error(traceback.format_exc())
        error_msg = {"error": str(e), "status": "error"}
        yield f'data: {json.dumps(error_msg)}\n\n'
        yield 'data: [DONE]\n\n'
