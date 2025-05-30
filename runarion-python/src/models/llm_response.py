# src/models/llm_response.py
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class LLMUsageMetadata:
    """Standardized structure for token usage."""
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    processing_time_ms: Optional[int] = None

@dataclass
class LLMResponse:
    """
    A standardized structure for responses from LLM providers.
    """
    status: str  # e.g., "success", "error"
    text: str  # The primary generated text output
    model_used: str  # The actual model identifier that generated the response
    
    finish_reason: Optional[str] = None # e.g., "stop", "length", "content_filter", "tool_calls"
    usage: Optional[LLMUsageMetadata] = None # Token usage information
    
    error_message: Optional[str] = None # If an error occurred during generation by the provider

    def has_error(self) -> bool:
        return self.error_message is not None