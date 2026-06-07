import logging

# Add src to Python path for imports

import pytest
from src.utils.token_counter import TokenCounter


@pytest.fixture(autouse=True)
def _silence_expected_token_counter_logs(set_logger_level):
    set_logger_level("src.utils.token_counter", logging.ERROR)


class TestTokenCounter:
    """Test suite for TokenCounter class."""

    def test_gemini_token_counter_initialization(self):
        """Test TokenCounter initialization with Gemini provider."""
        counter = TokenCounter("gemini", "gemini-2.5-flash")
        assert counter.tokenizer is not None

    def test_gemini_token_counter_count(self):
        """Test token counting with valid Gemini model."""
        counter = TokenCounter("gemini", "gemini-2.5-flash")
        result = counter.count("Hello world!")
        assert isinstance(result, int)
        assert result > 0

    def test_gemini_nonexistent_model_initialization(self):
        """Test TokenCounter initialization with non-existent Gemini model."""
        counter = TokenCounter("gemini", "not-exist")
        # Should initialize without error, tokenizer will be GenerativeModel
        assert counter.tokenizer is not None

    def test_gemini_nonexistent_model_count_raises_error(self):
        """Test that counting with non-existent Gemini model raises an error."""
        counter = TokenCounter("gemini", "not-exist")
        with pytest.raises(Exception):
            counter.count("Hello world!")

    def test_gemini_nonexistent_model_safe_count(self):
        """Test safe_count falls back gracefully for non-existent Gemini model."""
        counter = TokenCounter("gemini", "not-exist")
        result = counter.safe_count("Hello world!")
        # Should return estimated count without raising error
        assert isinstance(result, int)
        assert result > 0

    def test_openai_token_counter_initialization(self):
        """Test TokenCounter initialization with OpenAI provider."""
        counter = TokenCounter("openai", "gpt-4o")
        assert counter.tokenizer is not None

    def test_openai_token_counter_count(self):
        """Test token counting with valid OpenAI model."""
        counter = TokenCounter("openai", "gpt-4o")
        result = counter.count("Hello world!")
        assert isinstance(result, int)
        assert result > 0

    def test_openai_nonexistent_model_fallback(self):
        """Test TokenCounter initialization with non-existent OpenAI model falls back."""
        counter = TokenCounter("openai", "not-exist")
        # Should fallback to cl100k_base encoding
        assert counter.tokenizer is not None

    def test_openai_nonexistent_model_count(self):
        """Test token counting with non-existent OpenAI model using fallback."""
        counter = TokenCounter("openai", "not-exist")
        result = counter.count("Hello world!")
        assert isinstance(result, int)
        assert result > 0

    def test_other_provider_token_counter_initialization(self):
        """Test TokenCounter initialization with other provider (HuggingFace)."""
        counter = TokenCounter("other", "roberta-base")
        assert counter.tokenizer is not None

    def test_other_provider_token_counter_count(self):
        """Test token counting with other provider."""
        counter = TokenCounter("other", "roberta-base")
        result = counter.count("Hello world!")
        assert isinstance(result, int)
        assert result > 0

    def test_other_provider_nonexistent_model_initialization(self):
        """Test TokenCounter initialization with non-existent model for other provider."""
        counter = TokenCounter("other", "not-exist")
        # Should set tokenizer to None after failing to load
        assert counter.tokenizer is None

    def test_other_provider_nonexistent_model_count(self):
        """Test token counting with non-existent model falls back to estimation."""
        counter = TokenCounter("other", "not-exist")
        result = counter.count("Hello world!")
        # Should use character-based estimation
        assert isinstance(result, int)
        assert result > 0
