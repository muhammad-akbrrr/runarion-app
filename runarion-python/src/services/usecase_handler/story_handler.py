# services/usecase_handler/story_handler.py

from services.usecase_handler.base_handler import UseCaseHandler
from utils.story_instruction_builder import InstructionBuilder
from models.request import BaseGenerationRequest, GenerationConfig, CallerInfo
from models.story_generation.prompt_config import PromptConfig

class StoryHandler(UseCaseHandler):
    """
    A handler class for processing story generation requests into structured story generation
    requests. It processes the input configuration and builds appropriate instructions for
    story generation using the InstructionBuilder.
    """
    def build_request(self, raw_json: dict) -> BaseGenerationRequest:
        prompt_config_data = raw_json.get("prompt_config", {})
        prompt_config = PromptConfig(**prompt_config_data)

        builder = InstructionBuilder(config=prompt_config)
        prompt = raw_json.get("prompt", "")
        if prompt:
            instruction = builder.build()
        else:
            instruction = builder.build_from_scratch()

        return BaseGenerationRequest(
            provider=raw_json.get("provider", "openai"),
            model=raw_json.get("model"),
            prompt=prompt,
            instruction=instruction,
            generation_config=GenerationConfig(**raw_json["generation_config"]),
            caller=CallerInfo(**raw_json["caller"])
        )