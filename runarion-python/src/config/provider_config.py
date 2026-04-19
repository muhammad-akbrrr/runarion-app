"""
Provider-Aware Output Token Budget Configuration.

Centralized max_output_tokens budgets per provider and task type.
The GeminiProvider adds thinking_budget ON TOP of these values (unchanged).
"""


class ProviderOutputBudgetConfig:
    """
    Provider-specific max_output_tokens budgets for different generation task types.

    Task types:
        json_analytical: JSON structured output (scene detection, analysis, reports, coherence, chaptering)
        text_generation: Plain text creative output (text cleaning, scene enhancement)
        short_text: Very short output (titles, labels)

    The GeminiProvider internally adds thinking_budget ON TOP of max_output_tokens.
    These values represent the DESIRED OUTPUT budget only.
    """

    _BUDGETS = {
        "openai": {
            "json_analytical": 4096,
            "text_generation": 4096,
            "short_text": 200,
        },
        "gemini": {
            "json_analytical": 8192,
            "text_generation": 8192,
            "short_text": 500,
        },
        "deepseek": {
            "json_analytical": 4096,
            "text_generation": 4096,
            "short_text": 200,
        },
    }

    _DEFAULT_BUDGET = {
        "json_analytical": 4096,
        "text_generation": 4096,
        "short_text": 200,
    }

    VALID_TASK_TYPES = ("json_analytical", "text_generation", "short_text")

    @classmethod
    def get_budget(cls, provider: str, task_type: str) -> int:
        """
        Get the output token budget for a given provider and task type.

        Args:
            provider: Provider name (e.g., "openai", "gemini", "deepseek")
            task_type: One of "json_analytical", "text_generation", "short_text"

        Returns:
            max_output_tokens value appropriate for this provider+task combination
        """
        if task_type not in cls.VALID_TASK_TYPES:
            raise ValueError(
                f"Unknown task_type '{task_type}'. Valid types: {cls.VALID_TASK_TYPES}"
            )

        provider_key = provider.lower().strip()
        provider_budgets = cls._BUDGETS.get(provider_key, cls._DEFAULT_BUDGET)
        return provider_budgets[task_type]

    @classmethod
    def get_provider_summary(cls, provider: str) -> dict:
        """Get all budgets for a specific provider."""
        provider_key = provider.lower().strip()
        return dict(cls._BUDGETS.get(provider_key, cls._DEFAULT_BUDGET))
