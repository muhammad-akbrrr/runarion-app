import os

import google.generativeai as genai
import tiktoken
from dotenv import load_dotenv
from transformers import AutoTokenizer
from vertexai.preview import tokenization
from vertexai.tokenization._tokenizers import PreviewTokenizer


class TokenCounter:
    """
    A class to count tokens in a given text based on the specified model provider and model name.
    """

    def __init__(self, provider: str, model_name: str):
        """
        Initialize a tokenizer for counting tokens based on the specified provider and model name.
        The tokenizer is resolved based on the provider:
        - openai: `tiktoken`
        - gemini: `tokenization` from `vertexai` if available, otherwise call gemini API
        - other: `AutoTokenizer` from Hugging Face `transformers`

        Args:
            provider (str): The model provider (e.g., "openai", "gemini").
            model_name (str): The name of the model to use for tokenization.
        """
        if provider == "openai":
            self.tokenizer = tiktoken.encoding_for_model(model_name)
        elif provider == "gemini":
            try:
                self.tokenizer = tokenization.get_tokenizer_for_model(model_name)
            except ValueError:
                load_dotenv()
                GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
                genai.configure(api_key=GEMINI_API_KEY)  # type: ignore
                self.tokenizer = genai.GenerativeModel(model_name)  # type: ignore
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    def count_tokens(self, text: str) -> int:
        if isinstance(self.tokenizer, tiktoken.Encoding):
            return len(self.tokenizer.encode(text))
        elif isinstance(self.tokenizer, PreviewTokenizer):
            return self.tokenizer.count_tokens(text).total_tokens
        elif isinstance(self.tokenizer, genai.GenerativeModel):  # type: ignore
            return self.tokenizer.count_tokens(text).total_tokens
        else:
            return len(self.tokenizer.encode(text, add_special_tokens=False))
