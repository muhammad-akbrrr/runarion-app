from pydantic import BaseModel, Field
from typing import Literal, Optional

class UsageMetadata(BaseModel):
    finish_reason: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    processing_time_ms: int


class QuotaMetadata(BaseModel):
    user_id: str
    workspace_id: str
    project_id: str
    generation_count: int


class GenerationResponse(BaseModel):
    success: bool = True
    text: str
    provider: str
    model_used: str
    key_used: Literal["own", "default"]
    request_id: str
    provider_request_id: Optional[str] = None
    metadata: UsageMetadata
    quota: QuotaMetadata
    error_message: Optional[str] = None
