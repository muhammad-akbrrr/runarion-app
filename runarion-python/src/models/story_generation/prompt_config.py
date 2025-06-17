# models/story_generation/prompt_config.py

from pydantic import BaseModel
from typing import Optional

class PromptConfig(BaseModel):
    author_profile: Optional[str] = ""
    context: Optional[str] = ""
    genre: Optional[str] = ""
    tone: Optional[str] = ""
    pov: Optional[str] = ""  # point of view