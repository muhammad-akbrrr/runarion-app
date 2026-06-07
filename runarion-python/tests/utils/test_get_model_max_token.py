
# Add src to Python path for imports

import pytest
from src.utils.get_model_max_token import get_safe_model_max_tokens


class TestGetSafeModelMaxTokens:
    """Test suite for get_safe_model_max_tokens function."""

    def test_gemini_model_no_margin(self):
        """Test Gemini model with no safety margin."""
        result = get_safe_model_max_tokens(
            "gemini", "gemini-2.5-flash", safety_margin=0
        )
        assert isinstance(result, int)
        assert result > 0

    def test_gemini_model_float_margin(self):
        """Test Gemini model with float safety margin."""
        result = get_safe_model_max_tokens(
            "gemini", "gemini-2.5-flash", safety_margin=0.1
        )
        assert isinstance(result, int)
        assert result > 0

    def test_gemini_model_int_margin(self):
        """Test Gemini model with integer safety margin."""
        result = get_safe_model_max_tokens(
            "gemini", "gemini-2.5-flash", safety_margin=10000
        )
        assert isinstance(result, int)
        assert result > 0

    def test_gemini_model_negative_margin_raises_error(self):
        """Test that negative integer safety margin raises ValueError."""
        with pytest.raises(
            ValueError, match="Integer safety margin must be a non-negative integer"
        ):
            get_safe_model_max_tokens("gemini", "gemini-2.5-flash", safety_margin=-1)

    def test_gemini_model_float_margin_out_of_range_raises_error(self):
        """Test that float safety margin >= 1.0 raises ValueError."""
        with pytest.raises(
            ValueError, match="Float safety margin must be between 0 and 1"
        ):
            get_safe_model_max_tokens("gemini", "gemini-2.5-flash", safety_margin=100.0)

    def test_openai_model_no_margin(self):
        """Test OpenAI model with no safety margin."""
        result = get_safe_model_max_tokens("openai", "gpt-4.1-nano", safety_margin=0)
        assert isinstance(result, int)
        assert result > 0

    def test_other_provider_roberta(self):
        """Test other provider (HuggingFace) with roberta-base model."""
        result = get_safe_model_max_tokens("other", "roberta-base", safety_margin=0)
        assert isinstance(result, int)
        assert result > 0

    def test_other_provider_deepseek(self):
        """Test other provider (HuggingFace) with DeepSeek model."""
        result = get_safe_model_max_tokens(
            "other", "deepseek-ai/DeepSeek-R1-Distill-Llama-8B", safety_margin=0
        )
        assert isinstance(result, int)
        assert result > 0