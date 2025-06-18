# models/request.py

from pydantic import BaseModel, Field
from typing import Optional, Dict

class CallerInfo(BaseModel):
    user_id: str
    workspace_id: str
    project_id: str
    api_keys: Dict[str, Optional[str]]

class GenerationConfig(BaseModel):
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    max_output_tokens: int = Field(200, ge=1)
    nucleus_sampling: float = Field(1.0, ge=0.0, le=1.0)
    tail_free_sampling: float = Field(1.0, ge=0.0, le=1.0)
    top_k: float = Field(0.0, ge=0.0)
    top_a: float = Field(0.0, ge=0.0)
    phrase_bias: float = Field(0.0, ge=0.0, le=1.0)
    banned_tokens: Optional[list] = None
    stop_sequences: Optional[list] = None
    repetition_penalty: float = Field(0.0, ge=0.0)

class BaseGenerationRequest(BaseModel):
    usecase: str = "mock"
    provider: str = "openai"
    model: Optional[str] = None
    prompt: Optional[str] = None
    instruction: Optional[object] = None
    generation_config: GenerationConfig
    caller: CallerInfo
