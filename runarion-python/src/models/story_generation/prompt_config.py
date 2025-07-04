# models/story_generation/prompt_config.py

from pydantic import BaseModel
from typing import Optional

from models.deconstructor import AuthorStyle

class PromptConfig(BaseModel):
    author_profile: Optional[AuthorStyle] = None
    context: Optional[str] = ""
    genre: Optional[str] = ""
    tone: Optional[str] = ""
    pov: Optional[str] = ""  # point of view