import functools

import google.generativeai as genai
from transformers import AutoTokenizer

# Based on https://platform.openai.com/docs/models/{model_name}
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


# Call to Gemini API, cache the output
@functools.lru_cache(maxsize=None)
def list_gemini_model_max_token() -> dict[str, int]:
    output = {}
    models = genai.list_models()  # type: ignore
    for model in models:
        if not hasattr(model, "name") or not hasattr(model, "input_token_limit"):
            continue
        output[model.name[7:]] = model.input_token_limit
    return output


# Create a tokenizer for the model to get its max token limit, cache it
@functools.lru_cache(maxsize=64)
def get_huggingface_model_max_token(model_name: str) -> int | None:
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if hasattr(tokenizer, "model_max_length") and tokenizer.model_max_length < int(
        1e30
    ):
        return tokenizer.model_max_length
    else:
        return None


def get_model_max_token(provider: str, model_name: str) -> int:
    if provider == "openai":
        max_token = openai_model_max_tokens.get(model_name)
    elif provider == "gemini":
        max_token = list_gemini_model_max_token().get(model_name)
    else:
        max_token = get_huggingface_model_max_token(model_name)

    if max_token is None:
        raise ValueError(
            f"Max token limit for model {model_name} not found in the records."
        )
    return max_token
