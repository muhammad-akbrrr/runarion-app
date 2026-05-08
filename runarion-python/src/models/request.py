# models/request.py

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class CallerInfo(BaseModel):
    user_id: str
    workspace_id: str
    project_id: str
    api_keys: Dict[str, Optional[str]]
    session_id: Optional[str] = None


class RewritePolicy(BaseModel):
    style_transfer_strength: Literal["low", "medium", "high"] = "medium"
    style_source_priority: Literal[
        "preserve_manuscript", "balanced", "favor_author"
    ] = "balanced"
    negative_constraints: List[str] = Field(default_factory=list, max_length=5)

    @field_validator("negative_constraints", mode="before")
    @classmethod
    def _normalize_negative_constraints(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            raise TypeError("negative_constraints must be a list of strings")

        normalized = []
        seen = set()
        for item in value:
            if item is None:
                continue
            text = str(item).strip()
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(text)
        return normalized

class GenerationConfig(BaseModel):
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    repetition_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    min_output_tokens: int = Field(50, ge=1)
    max_output_tokens: int = Field(300, ge=1)
    nucleus_sampling: float = Field(1.0, ge=0.0, le=1.0)
    tail_free_sampling: float = Field(1.0, ge=0.0, le=1.0)
    top_a: float = Field(0.0, ge=0.0)
    top_k: float = Field(0.0, ge=0.0)
    phrase_bias: Optional[List[Dict[str, float]]] = None
    banned_tokens: Optional[List[str]] = None
    stop_sequences: Optional[List[str]] = None
    stream: bool = False
    # Gemini structured output - when set to "application/json", Gemini guarantees valid JSON output
    # Set to None for plain text stages (e.g. text cleaning, enhancement, title generation)
    response_mime_type: Optional[str] = None
    # Gemini thinking config - allows configurable thinking budget for supported models
    # Set to None to use model-specific defaults, 0 to disable, or a positive value for custom budget
    thinking_budget: Optional[int] = None
    include_thinking: Optional[bool] = False

class BaseGenerationRequest(BaseModel):
    usecase: str = "mock"
    provider: str = "gemini"
    model: Optional[str] = None
    prompt: Optional[str] = None
    instruction: Optional[object] = None
    generation_config: GenerationConfig
    caller: CallerInfo


def rewrite_policy_to_dict(policy: Optional[RewritePolicy | dict]) -> dict:
    if policy is None:
        return RewritePolicy().model_dump(mode="json")
    if isinstance(policy, RewritePolicy):
        return policy.model_dump(mode="json")
    return RewritePolicy(**policy).model_dump(mode="json")
