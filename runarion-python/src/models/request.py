# models/request.py

from pydantic import BaseModel
from typing import Optional, Dict

class CallerInfo(BaseModel):
    user_id: str
    workspace_id: str
    project_id: str
    api_keys: Dict[str, Optional[str]]  # e.g., {"openai": "", "gemini": "", "deepseek": "sk-..."}

class BaseGenerationRequest(BaseModel):
    provider: str = "openai"
    model: Optional[str] = None
    caller: CallerInfo
