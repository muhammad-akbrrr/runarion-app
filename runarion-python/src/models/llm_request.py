from pydantic import BaseModel, Field, AfterValidator
from typing import Optional, Dict, Any, Literal, Annotated

DEFAULT_SYSTEM_PROMPT = "You are a helpful AI Assistant."
DEFAULT_PROVIDER = "openai"

# Validators
def non_empty_prompt(v: str) -> str:
    if not v.strip():
        raise ValueError("Prompt cannot be empty or whitespace.")
    return v

def valid_provider(v: str) -> str:
    if v not in {"openai", "gemini"}:
        raise ValueError("Provider must be either 'openai' or 'gemini'.")
    return v

# Annotated fields with validators
PromptType = Annotated[str, Field(min_length=1, description="The user's prompt for the LLM."), AfterValidator(non_empty_prompt)]
ProviderType = Annotated[Literal["openai", "gemini"], AfterValidator(valid_provider)]

# Pydantic model for LLM request parameters
class BaseRequest(BaseModel):
    prompt: PromptType
    provider: ProviderType = Field(
        default=DEFAULT_PROVIDER,
        description="The LLM provider to use. Defaults to 'openai'."
    )
    model: Optional[str] = Field(
        default=None,
        description="Specific model name to override the provider's default."
    )
    system_prompt: Optional[str] = Field(
        default=DEFAULT_SYSTEM_PROMPT,
        description="Custom system prompt for the LLM. If not provided, the provider's default system prompt will be used."
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific parameters (e.g., temperature, max_tokens)."
    )

# Model Agnostic Class for Request
class LLMRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def from_base_request(cls, base: BaseRequest) -> "LLMRequest":
        return cls(
            prompt=base.prompt,
            model=base.model,
            system_prompt=base.system_prompt,
            params=base.params
        )