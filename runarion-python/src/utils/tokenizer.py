# utils/tokenizer.py

import tiktoken
from typing import List, Dict, Union, Optional
from flask import current_app

class TokenizerManager:
    """
    A utility class for handling tokenization of text for different LLM providers.
    This class provides methods to convert strings to token IDs and vice versa.
    """
    
    # Mapping of model prefixes to encoding names
    MODEL_ENCODINGS = {
        # o200k_base — used by gpt-4o and gpt-4o-mini
        "gpt-4o": "o200k_base",
        "gpt-4o-mini": "o200k_base",

        # cl100k_base — used by GPT-4, GPT-3.5-turbo, and embeddings
        "gpt-4": "cl100k_base",
        "gpt-4-turbo": "cl100k_base",
        "gpt-3.5": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "text-embedding-ada-002": "cl100k_base",
        "text-embedding-3-small": "cl100k_base",
        "text-embedding-3-large": "cl100k_base",
        
        # Gemini Models
        "gemini-2.0-flash": "cl100k_base",
        
        # Default for other models
        "default": "cl100k_base"
    }
    
    @classmethod
    def get_encoding_for_model(cls, model_name: str) -> tiktoken.Encoding:
        """
        Get the appropriate encoding for a given model name.

        Args:
            model_name: The name of the model

        Returns:
            A tiktoken Encoding object
        """
        try:
            # Try to find a matching model prefix in MODEL_ENCODINGS
            for prefix, encoding_name in cls.MODEL_ENCODINGS.items():
                if model_name.startswith(prefix):
                    return tiktoken.get_encoding(encoding_name)

            # Fall back to default encoding
            current_app.logger.warning(f"No specific encoding found for model {model_name}, using default encoding")
            return tiktoken.get_encoding(cls.MODEL_ENCODINGS["default"])

        except Exception as e:
            current_app.logger.error(f"Error getting encoding for model {model_name}: {e}")
            # Fall back to default encoding
            return tiktoken.get_encoding(cls.MODEL_ENCODINGS["default"])
    
    @classmethod
    def tokenize_string(cls, text: str, model_name: str) -> List[int]:
        """
        Convert a string to a list of token IDs.
        
        Args:
            text: The text to tokenize
            model_name: The name of the model to use for tokenization
            
        Returns:
            A list of token IDs
        """
        encoding = cls.get_encoding_for_model(model_name)
        return encoding.encode(text)
    
    @classmethod
    def tokenize_phrase_bias(cls, phrase_bias: List[Dict[str, float]], model_name: str) -> List[Dict[str, float]]:
        """
        Convert a list of phrase bias dictionaries to token-based bias dictionaries.
        
        Args:
            phrase_bias: A list of dictionaries mapping phrases to bias values
            model_name: The name of the model to use for tokenization
            
        Returns:
            A list of dictionaries mapping token IDs to bias values
        """
        if not phrase_bias:
            return []
        
        result = []
        encoding = cls.get_encoding_for_model(model_name)
        
        for bias_item in phrase_bias:
            for phrase, bias_value in bias_item.items():
                # Tokenize the phrase
                token_ids = encoding.encode(phrase)
                
                # Create a new bias item for each token
                for token_id in token_ids:
                    result.append({str(token_id): bias_value})
        
        return result
    
    @classmethod
    def tokenize_banned_tokens(cls, banned_tokens: List[str], model_name: str) -> List[int]:
        """
        Convert a list of banned token strings to a list of token IDs.
        
        Args:
            banned_tokens: A list of strings to ban
            model_name: The name of the model to use for tokenization
            
        Returns:
            A list of token IDs to ban
        """
        if not banned_tokens:
            return []
        
        result = []
        encoding = cls.get_encoding_for_model(model_name)
        
        for token_str in banned_tokens:
            # Tokenize each string
            token_ids = encoding.encode(token_str)
            # Add all token IDs to the result
            result.extend(token_ids)
        
        return result
    
    @classmethod
    def decode_tokens(cls, tokens: List[int], model_name: str) -> str:
        """
        Convert a list of token IDs back to a string.
        
        Args:
            tokens: A list of token IDs
            model_name: The name of the model to use for decoding
            
        Returns:
            The decoded string
        """
        encoding = cls.get_encoding_for_model(model_name)
        return encoding.decode(tokens)