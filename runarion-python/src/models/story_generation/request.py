# models/story_generation/request.py

from pydantic import BaseModel, Field
from typing import Optional
from models.request import BaseGenerationRequest, CallerInfo

class PromptConfig(BaseModel):
    author_profile: Optional[str] = ""
    context: Optional[str] = ""
    genre: Optional[str] = ""
    tone: Optional[str] = ""
    pov: Optional[str] = ""  # point of view

class GenerationConfig(BaseModel):
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    max_output_tokens: int = Field(200, ge=1)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    top_k: float = Field(0.0, ge=0.0)
    repetition_penalty: float = Field(0.0, ge=0.0)

class StoryGenerationRequest(BaseGenerationRequest):
    prompt: Optional[str] = None
    prompt_config: PromptConfig
    generation_config: GenerationConfig