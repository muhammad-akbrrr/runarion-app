import functools
from typing import Optional, Union

import google.generativeai as genai
import tiktoken
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


@functools.lru_cache(maxsize=None)
def list_gemini_model_max_token() -> dict[str, int]:
    """
    List the max token limit for all Gemini models using the Gemini API.
    The output is cached to avoid repeated API calls.
    """
    output = {}
    models = genai.list_models()  # type: ignore
    for model in models:
        if not hasattr(model, "name") or not hasattr(model, "input_token_limit"):
            continue
        output[model.name[7:]] = model.input_token_limit
    return output


@functools.lru_cache(maxsize=64)
def get_huggingface_model_max_token(model_name: str) -> Optional[int]:
    """
    Get the max token limit for a Hugging Face model using the model's tokenizer.
    The output is cached to avoid repeated loading of the tokenizer.
    """
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if hasattr(tokenizer, "model_max_length") and tokenizer.model_max_length < int(
        1e30
    ):
        return tokenizer.model_max_length
    else:
        return None


@functools.lru_cache(maxsize=64)
def get_openai_tokenizer(model_name: str) -> tiktoken.Encoding:
    """
    Get the tiktoken encoder for an OpenAI model.
    The output is cached to avoid repeated loading.
    """
    try:
        # Try to get the encoding for the specific model
        return tiktoken.encoding_for_model(model_name)
    except KeyError:
        # Fallback to cl100k_base encoding (used by GPT-4, GPT-3.5-turbo)
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, provider: str, model_name: str) -> int:
    """
    Count tokens in text using the appropriate tokenizer for the provider/model.
    
    Args:
        text: Text to count tokens for
        provider: AI provider ('openai', 'gemini', etc.)
        model_name: Specific model name
        
    Returns:
        Number of tokens in the text
    """
    if provider == "openai":
        tokenizer = get_openai_tokenizer(model_name)
        return len(tokenizer.encode(text))
    elif provider == "gemini":
        # Gemini uses SentencePiece tokenizer - approximate with tiktoken for now
        # For more accuracy, you could use Google's sentencepiece library
        tokenizer = get_openai_tokenizer("gpt-4")  # Fallback approximation
        return len(tokenizer.encode(text))
    else:
        # For Hugging Face models, use their tokenizer
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            tokens = tokenizer.encode(text, add_special_tokens=True)
            return len(tokens)
        except Exception:
            # Final fallback - rough approximation (1 token ≈ 4 characters)
            return len(text) // 4


def estimate_tokens_from_messages(messages: list, provider: str, model_name: str) -> int:
    """
    Estimate token count for a list of messages (chat format).
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        provider: AI provider ('openai', 'gemini', etc.)
        model_name: Specific model name
        
    Returns:
        Estimated total tokens
    """
    total_tokens = 0
    
    if provider == "openai":
        tokenizer = get_openai_tokenizer(model_name)
        
        # OpenAI chat format overhead
        total_tokens += 3  # Base overhead for chat format
        
        for message in messages:
            # Count tokens for role and content
            role_tokens = len(tokenizer.encode(message.get('role', '')))
            content_tokens = len(tokenizer.encode(message.get('content', '')))
            
            # Add overhead per message (varies by model, but ~4 is typical)
            message_overhead = 4
            total_tokens += role_tokens + content_tokens + message_overhead
    else:
        # For other providers, count all text content
        all_text = ""
        for message in messages:
            all_text += f"{message.get('role', '')}: {message.get('content', '')}\n"
        
        total_tokens = count_tokens(all_text, provider, model_name)
    
    return total_tokens


def get_safe_max_tokens(provider: str, model_name: str, safety_margin: float = 0.1) -> int:
    """
    Get the safe maximum tokens for a model, accounting for safety margin.
    
    Args:
        provider: AI provider
        model_name: Model name
        safety_margin: Percentage to reserve (0.1 = 10% safety margin)
        
    Returns:
        Safe maximum token count
    """
    max_tokens = get_model_max_token(provider, model_name)
    return int(max_tokens * (1 - safety_margin))


def chunk_text_by_tokens(text: str, max_tokens: int, provider: str, model_name: str, 
                        overlap_tokens: int = 50) -> list[str]:
    """
    Split text into chunks based on token count rather than character count.
    
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk
        provider: AI provider
        model_name: Model name
        overlap_tokens: Number of tokens to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if provider == "openai":
        tokenizer = get_openai_tokenizer(model_name)
        tokens = tokenizer.encode(text)
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            # Move start position, accounting for overlap
            start = end - overlap_tokens
            if start >= len(tokens):
                break
                
        return chunks
    else:
        # Fallback to character-based chunking with token estimation
        estimated_chars_per_token = 4
        max_chars = max_tokens * estimated_chars_per_token
        overlap_chars = overlap_tokens * estimated_chars_per_token
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunk = text[start:end]
            
            # Try to break at word boundaries
            if end < len(text) and not text[end].isspace():
                last_space = chunk.rfind(' ')
                if last_space > len(chunk) // 2:  # Don't break too early
                    end = start + last_space
                    chunk = text[start:end]
            
            chunks.append(chunk)
            start = end - overlap_chars
            if start >= len(text):
                break
                
        return chunks


def get_model_max_token(provider: str, model_name: str) -> int:
    """
    Get the max token limit for a model based on the provider and model name.
    The provider can be "openai", "gemini", or other (Hugging Face).
    """
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
