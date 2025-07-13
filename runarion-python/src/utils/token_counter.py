import google.generativeai as genai
import tiktoken
from transformers import AutoTokenizer
from vertexai.preview import tokenization

# Constants
CHARS_PER_TOKEN_ESTIMATE = 4  # Approximate character-to-token ratio
TIKTOKEN_FALLBACK_MODEL = "gpt-4"  # Model to use for tiktoken fallback


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


def count_tokens_gemini_exact(text: str, model_name: str) -> int:
    """
    Count tokens using Gemini's exact CountTokens API.

    Args:
        text: Text to count tokens for
        model_name: Gemini model name

    Returns:
        Exact number of tokens

    Raises:
        Exception: If API call fails
    """
    try:
        try:
            # Use tokenizer from vertexai if available
            tokenizer = tokenization.get_tokenizer_for_model(model_name)
            return tokenizer.count_tokens(text).total_tokens
        except ValueError:
            # Fallback to API call if tokenizer not available for the model
            response = genai.count_tokens(model=model_name, contents=[text])
            return response.total_tokens
    except Exception as e:
        # Re-raise to allow fallback handling in caller
        raise Exception(f"Gemini token counting failed: {str(e)}")


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
        try:
            return count_tokens_gemini_exact(text, model_name)
        except Exception:
            # Fallback to tiktoken approximation if API fails
            tokenizer = get_openai_tokenizer(TIKTOKEN_FALLBACK_MODEL)
            return len(tokenizer.encode(text))
    else:
        # For Hugging Face models, use their tokenizer
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            tokens = tokenizer.encode(text, add_special_tokens=True)
            return len(tokens)
        except Exception:
            # Final fallback - rough approximation
            return len(text) // CHARS_PER_TOKEN_ESTIMATE


def estimate_tokens_from_messages(
    messages: list, provider: str, model_name: str
) -> int:
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
            role_tokens = len(tokenizer.encode(message.get("role", "")))
            content_tokens = len(tokenizer.encode(message.get("content", "")))

            # Add overhead per message (varies by model, but ~4 is typical)
            message_overhead = 4
            total_tokens += role_tokens + content_tokens + message_overhead
    else:
        # For Gemini and other providers, format messages into a single text
        formatted_messages = []
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            formatted_messages.append(f"{role}: {content}")

        all_text = "\n".join(formatted_messages)
        total_tokens = count_tokens(all_text, provider, model_name)

    return total_tokens
