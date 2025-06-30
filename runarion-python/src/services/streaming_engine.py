import time
import uuid
from typing import Generator, Dict, Any, Optional, Type
from flask import current_app

from models.streaming import StreamingRequest, StreamingResponse, StreamingError
from models.request import BaseGenerationRequest
from services.generation_engine import GenerationEngine

class StreamingEngine:
    """
    Engine for handling streaming text generation.
    
    This class manages the streaming process, including provider selection,
    error handling, and quota management.
    """
    
    def __init__(self, request: StreamingRequest):
        self.request = request
        self.base_request = request.base_request
        self.session_id = request.session_id
        self.provider_name = self.base_request.provider.lower()
        self.start_time = time.time()
        
        # Ensure the generation config has stream set to True
        self.base_request.generation_config.stream = True
        
        # Create the provider using the GenerationEngine
        engine = GenerationEngine(self.base_request)
        self.provider = engine.provider_instance
        
    def stream(self) -> Generator[str, None, None]:
        """
        Stream text generation from the provider.
        
        Yields:
            str: Text chunks as they are generated.
        """
        try:
            # Log the start of streaming
            current_app.logger.info(f"Starting streaming for session {self.session_id}")
            current_app.logger.info(f"Provider: {self.provider_name}, Model: {self.provider.model}")
            
            # Stream from the provider
            chunk_index = 0
            for chunk in self.provider.generate_stream():
                if chunk:
                    if chunk.startswith("Error:"):
                        # If the chunk is an error message, log it and yield it
                        current_app.logger.error(f"Streaming error: {chunk}")
                        yield chunk
                        return
                    else:
                        # Otherwise, yield the chunk
                        yield chunk
                        chunk_index += 1
            
            # Log completion
            elapsed_time = time.time() - self.start_time
            current_app.logger.info(f"Streaming completed for session {self.session_id}")
            current_app.logger.info(f"Generated {chunk_index} chunks in {elapsed_time:.2f} seconds")
                
        except Exception as e:
            current_app.logger.error(f"Streaming error: {e}")
            yield f"Error: {str(e)}"
