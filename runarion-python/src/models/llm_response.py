# src/models/llm_response.py
from dataclasses import dataclass, field, asdict
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
    status: str
    text: str
    model_used: str
    
    finish_reason: Optional[str] = None
    usage: Optional[LLMUsageMetadata] = None
    
    error_message: Optional[str] = None
    
    def has_error(self) -> bool:
        return self.error_message is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to a dictionary."""
        return asdict(self, dict_factory=dict)