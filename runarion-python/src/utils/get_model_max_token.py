import functools
from typing import Optional

import google.generativeai as genai
from transformers import AutoTokenizer

# Based on https://platform.openai.com/docs/models/{model}
openai_model_max_tokens = {
    "gpt-3.5-turbo": 16_385,
    "gpt-3.5-turbo-instruct": 4_096,
    "gpt-4": 8_192,
    "gpt-4-turbo": 128_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4.1": 1_047_576,
    "gpt-4.1-mini": 1_047_576,
    "gpt-4.1-nano": 1_047_576,
}

gemini_model_max_tokens_fallback = {
    "gemini-2.5-flash": 1_048_576,
    "gemini-2.5-pro": 1_048_576,
    "gemini-2.0-flash": 1_048_576,
    "gemini-1.5-flash": 1_048_576,
    "gemini-1.5-pro": 2_097_152,
}

huggingface_model_max_tokens_fallback = {
    "roberta-base": 512,
    "deepseek-ai/DeepSeek-R1-Distill-Llama-8B": 131_072,
}

mock_model_max_tokens = {
    "mock-replay-v1": 131_072,
}


@functools.lru_cache(maxsize=None)
def list_gemini_model_max_token() -> dict[str, int]:
    """
    List the max token limit for all Gemini models using the Gemini API.
    The output is cached to avoid repeated API calls.
    """
    output = {}
    try:
        models = genai.list_models()  # type: ignore
        for model in models:
            if not hasattr(model, "name") or not hasattr(model, "input_token_limit"):
                continue
            output[model.name[7:]] = model.input_token_limit
    except Exception:
        output = {}

    if not output:
        return dict(gemini_model_max_tokens_fallback)

    merged = dict(gemini_model_max_tokens_fallback)
    merged.update(output)
    return merged


@functools.lru_cache(maxsize=64)
def get_huggingface_model_max_token(model: str) -> Optional[int]:
    """
    Get the max token limit for a Hugging Face model using the model's tokenizer.
    The output is cached to avoid repeated loading of the tokenizer.
    """
    fallback = huggingface_model_max_tokens_fallback.get(model)
    if fallback is not None:
        return fallback

    try:
        tokenizer = AutoTokenizer.from_pretrained(model)
    except Exception:
        return None

    if hasattr(tokenizer, "model_max_length") and tokenizer.model_max_length < int(1e30):
        return tokenizer.model_max_length
    return None


def get_model_max_tokens(provider: str, model: str) -> int:
    """
    Get the max token limit for a model based on the provider and model name.
    The provider can be "gemini", "openai", or other (Hugging Face).

    Args:
        provider: AI provider ('gemini', 'openai', etc.)
        model: Specific model name

    Returns:
        Maximum token limit for the model

    Raises:
        ValueError: If model not found in records
    """
    if provider == "openai":
        max_token = openai_model_max_tokens.get(model)
    elif provider == "gemini":
        max_token = gemini_model_max_tokens_fallback.get(model)
        if max_token is None:
            max_token = list_gemini_model_max_token().get(model)
    elif provider == "mock":
        max_token = mock_model_max_tokens.get(model, 131_072)
    else:
        max_token = huggingface_model_max_tokens_fallback.get(model)
        if max_token is None:
            max_token = get_huggingface_model_max_token(model)

    if max_token is None:
        raise ValueError(
            f"Max token limit for provider {provider} model {model} not found in the records."
        )
    return max_token


def get_safe_model_max_tokens(
    provider: str, model: str, safety_margin: float | int = 0.1
) -> int:
    """
    Get the safe maximum tokens for a model, accounting for safety margin.

    Args:
        provider: AI provider
        model: Model name
        safety_margin: Portion of tokens to reserve, int means number of tokens, float means ratio of model max tokens

    Returns:
        Safe maximum token count
    """
    max_tokens = get_model_max_tokens(provider, model)
    if isinstance(safety_margin, int):
        if safety_margin < 0:
            raise ValueError("Integer safety margin must be a non-negative integer.")
        return max_tokens - safety_margin
    else:
        if safety_margin < 0 or safety_margin >= 1:
            raise ValueError("Float safety margin must be between 0 and 1.")
        return int(max_tokens * (1 - safety_margin))
