# utils/story_instruction_builder.py

from models.story_generation.prompt_config import PromptConfig


class InstructionBuilder:
    """Builds instructions for creative writing tasks based on the provided configuration."""

    def __init__(self, config: PromptConfig):
        self.config = config

    def build(self) -> str:
        """Build instruction assuming this is a continuation of an existing work."""
        parts = ["You are an accomplished creative writer and storytelling expert. Your task is to seamlessly continue an existing story while maintaining consistency in style, tone, and narrative flow."]
        # Enforce no additional text
        parts.append("DO NOT WRITE ANYTHING ELSE. DO NOT WRITE A TITLE. DO NOT WRITE A SUMMARY. DO NOT WRITE A SYNOPSIS. DO NOT WRITE A TAGLINE. DO NOT START THE GENERATION WITH DOTS. JUST CONTINUE THE STORY FROM THE NEXT WORD.")

        if self.config.context:
            parts.append(
                f"The context of the writing is:\n{self.config.context.strip()}")

        if self.config.genre:
            parts.append(
                f"The story belongs to the **{self.config.genre.strip()}** genre.")

        if self.config.tone:
            parts.append(f"The tone should be **{self.config.tone.strip()}**.")

        # TODO : Implement lookup to use example of author's writing style
        if self.config.pov:
            parts.append(
                f"The story should follow a **{self.config.pov.strip()}** point of view.")

        if self.config.author_profile:
            parts.append(
                f"You're expected to write in a style similar to the original author:\n{self.config.author_profile.strip()}")

        parts.append(
            "Please continue the writing professionally, following the guidance above from the given input.")
        return "\n\n".join(parts)

    def build_from_scratch(self) -> str:
        """Build instruction assuming the story is being generated from the beginning."""
        parts = ["You are an accomplished creative writer specializing in fiction. Create an engaging story opening based on the provided specifications."]
        # Enforce no additional text
        parts.append("DO NOT WRITE ANYTHING ELSE. DO NOT WRITE A TITLE. DO NOT WRITE A SUMMARY. DO NOT WRITE A SYNOPSIS. DO NOT WRITE A TAGLINE. DO NOT START WITH DOTS. JUST START THE STORY BEGINNING.")

        if self.config.context:
            parts.append(
                f"The story should be set in the following context:\n{self.config.context.strip()}")

        if self.config.genre:
            parts.append(
                f"The genre of the story is **{self.config.genre.strip()}**.")

        if self.config.tone:
            parts.append(
                f"The tone of the story should be **{self.config.tone.strip()}**.")

        if self.config.pov:
            parts.append(
                f"The story should be written from a **{self.config.pov.strip()}** point of view.")

        # TODO : Implement lookup to use example of author's writing style
        if self.config.author_profile:
            parts.append(
                f"Emulate the writing style of the following author profile:\n{self.config.author_profile.strip()}")

        parts.append(
            "Create a compelling story beginning that establishes character, setting, and conflict setting up to a masterpiece story.")
        return "\n\n".join(parts)
