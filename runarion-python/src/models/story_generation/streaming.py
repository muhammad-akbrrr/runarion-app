from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Generator
from models.request import BaseGenerationRequest

class StreamingRequest(BaseModel):
    """
    Model for streaming text generation requests.
    
    This extends the base generation request with streaming-specific fields.
    """
    base_request: BaseGenerationRequest
    session_id: str = Field(..., description="Unique session ID for this streaming request")
    
    class Config:
        arbitrary_types_allowed = True

class StreamingResponse(BaseModel):
    """
    Model for streaming text generation responses.
    
    This is used for individual chunks in the stream.
    """
    chunk: str
    chunk_index: int
    session_id: str
    finish_reason: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True

class StreamingError(BaseModel):
    """
    Model for streaming errors.
    """
    error: str
    session_id: str
    
    class Config:
        arbitrary_types_allowed = True
