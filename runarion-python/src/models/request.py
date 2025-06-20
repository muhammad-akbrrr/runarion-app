# models/request.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, List


class CallerInfo(BaseModel):
    user_id: str
    workspace_id: str
    project_id: str
    api_keys: Dict[str, Optional[str]]

class GenerationConfig(BaseModel):
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    repetition_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    min_output_tokens: int = Field(50, ge=1)
    max_output_tokens: int = Field(300, ge=1)
    nucleus_sampling: float = Field(1.0, ge=0.0, le=1.0)
    tail_free_sampling: float = Field(1.0, ge=0.0, le=1.0)
    top_a: float = Field(0.0, ge=0.0)
    top_k: float = Field(0.0, ge=0.0)
    phrase_bias: Optional[List[Dict[str, float]]] = None
    banned_tokens: Optional[List[int]] = None
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False

class BaseGenerationRequest(BaseModel):
    usecase: str = "mock"
    provider: str = "openai"
    model: Optional[str] = None
    prompt: Optional[str] = None
    instruction: Optional[object] = None
    generation_config: GenerationConfig
    caller: CallerInfo
