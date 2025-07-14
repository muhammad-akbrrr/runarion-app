import logging
import os

import google.generativeai as genai
import tiktoken
from dotenv import load_dotenv
from transformers import AutoTokenizer
from vertexai.preview import tokenization
from vertexai.tokenization._tokenizers import PreviewTokenizer

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN_ESTIMATE = 4  # Approximate character-to-token ratio
TIKTOKEN_FALLBACK_ENCODING = (
    "cl100k_base"  # Fallback to cl100k_base encoding (used by GPT-4, GPT-3.5-turbo)
)


class TokenCounter:
    """
    A class to count tokens in a given text based on the specified model provider and model name.
    """

    def __init__(self, provider: str, model: str):
        """
        Initialize a tokenizer for counting tokens based on the specified provider and model name.
        The tokenizer is resolved based on the provider:
        - openai: `tiktoken`
        - gemini: `tokenization` from `vertexai` if available, otherwise call gemini API
        - other: `AutoTokenizer` from Hugging Face `transformers`

        Args:
            provider (str): The model provider (e.g., "openai", "gemini").
            model (str): The name of the model to use for tokenization.
        """
        if provider == "openai":
            try:
                self.tokenizer = tiktoken.encoding_for_model(model)
            except KeyError:
                logger.warning(
                    f"Model {model} not found in tiktoken. Falling back to {TIKTOKEN_FALLBACK_ENCODING} encoding."
                )
                self.tokenizer = tiktoken.get_encoding(TIKTOKEN_FALLBACK_ENCODING)
        elif provider == "gemini":
            try:
                self.tokenizer = tokenization.get_tokenizer_for_model(model)
            except ValueError:
                load_dotenv()
                GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
                genai.configure(api_key=GEMINI_API_KEY)  # type: ignore
                self.tokenizer = genai.GenerativeModel(model)  # type: ignore
        else:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model)
            except Exception:
                logger.warning(
                    f"Model {model} not found in Hugging Face. Falling back to character-based estimation."
                )
                self.tokenizer = None

    def count(self, text: str) -> int:
        if isinstance(self.tokenizer, tiktoken.Encoding):
            return len(self.tokenizer.encode(text))
        elif isinstance(self.tokenizer, PreviewTokenizer):
            return self.tokenizer.count_tokens(text).total_tokens
        elif isinstance(self.tokenizer, genai.GenerativeModel):  # type: ignore
            return self.tokenizer.count_tokens(text).total_tokens
        elif isinstance(self.tokenizer, AutoTokenizer):
            return len(self.tokenizer.encode(text, add_special_tokens=False))  # type: ignore
        else:
            return len(text) // CHARS_PER_TOKEN_ESTIMATE

    def safe_count(self, text: str) -> int:
        """
        Count the number of tokens in the given text.

        Args:
            text (str): The input text to count tokens for.

        Returns:
            int: The number of tokens in the text.
        """
        try:
            return self.count(text)
        except Exception:
            logger.warning(
                "Failed to count tokens using the tokenizer. Falling back to character-based estimation."
            )
            return len(text) // CHARS_PER_TOKEN_ESTIMATE

    def estimate_tokens_from_chat_messages(self, messages: list) -> int:
        """
        Estimate token count for a list of messages (chat format).

        Args:
            messages: List of message dictionaries with 'role' and 'content'

        Returns:
            Estimated total tokens
        """
        total_tokens = 0

        if isinstance(self.tokenizer, tiktoken.Encoding):
            # OpenAI chat format overhead
            total_tokens += 3  # Base overhead for chat format

            for message in messages:
                # Count tokens for role and content
                role_tokens = len(self.tokenizer.encode(message.get("role", "")))
                content_tokens = len(self.tokenizer.encode(message.get("content", "")))

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
            total_tokens = self.safe_count(all_text)

        return total_tokens
