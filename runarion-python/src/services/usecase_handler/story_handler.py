# services/usecase_handler/story_handler.py

from services.usecase_handler.base_handler import UseCaseHandler
from utils.story_instruction_builder import InstructionBuilder
from models.request import BaseGenerationRequest, GenerationConfig, CallerInfo
from models.story_generation.prompt_config import PromptConfig
from flask import current_app

class StoryHandler(UseCaseHandler):
    """
    A handler class for processing story generation requests into structured story generation
    requests. It processes the input configuration and builds appropriate instructions for
    story generation using the InstructionBuilder.
    """
    def build_request(self, raw_json: dict) -> BaseGenerationRequest:
        try:
            prompt_config_data = raw_json.get("prompt_config", {})
            prompt_config = PromptConfig(**prompt_config_data)

            builder = InstructionBuilder(config=prompt_config)
            prompt = raw_json.get("prompt", "")
            
            # Determine if this is a continuation or a new story
            if prompt:
                instruction = builder.build()
            else:
                instruction = builder.build_from_scratch()

            # Extract generation config with defaults
            generation_config_data = raw_json.get("generation_config", {})
            generation_config = GenerationConfig(**generation_config_data)
            generation_config.stream = raw_json.get("stream", False)
            
            # Extract caller info
            caller_data = raw_json.get("caller", {})
            caller = CallerInfo(**caller_data)
            
            # Create the request
            return BaseGenerationRequest(
                usecase=raw_json.get("usecase", "story"),
                provider=raw_json.get("provider", "openai"),
                model=raw_json.get("model"),
                prompt=prompt,
                instruction=instruction,
                generation_config=generation_config,
                caller=caller,
            )
        except Exception as e:
            current_app.logger.error(f"Error building story request: {e}")
            raise
