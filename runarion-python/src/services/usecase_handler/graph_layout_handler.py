# services/usecase_handler/graph_layout_handler.py

from src.services.usecase_handler.base_handler import UseCaseHandler
from src.models.request import BaseGenerationRequest, GenerationConfig, CallerInfo


class GraphLayoutHandler(UseCaseHandler):
    """
    A simple pass-through handler for graph layout generation.

    This handler bypasses conversation history entirely, ensuring that
    auto-build requests always generate fresh graphs based solely on
    the current prompt and any existing nodes passed in the request.

    Key differences from StoryHandler:
    - No conversation history loading/saving
    - No instruction building from prompt_config
    - Simple pass-through of the prompt as-is
    """

    def build_request(self, raw_json: dict) -> BaseGenerationRequest:
        # Extract generation config with defaults
        generation_config_data = raw_json.get("generation_config", {})
        generation_config = GenerationConfig(**generation_config_data)
        generation_config.stream = raw_json.get("stream", False)

        # Extract caller info
        caller_data = raw_json.get("caller", {})
        caller = CallerInfo(**caller_data)

        # Create the request - simple pass-through, no instruction building
        return BaseGenerationRequest(
            usecase="graph-layout",
            provider=raw_json.get("provider", "gemini"),
            model=raw_json.get("model"),
            prompt=raw_json.get("prompt", ""),
            instruction=None,  # No additional instruction - prompt contains everything
            generation_config=generation_config,
            caller=caller,
        )
