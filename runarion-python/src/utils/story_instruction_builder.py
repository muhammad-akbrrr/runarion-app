# utils/story_instruction_builder.py

from models.story_generation.prompt_config import PromptConfig
from typing import List, Optional


class InstructionBuilder:
    """Builds instructions for creative writing tasks based on the provided configuration."""

    def __init__(self, config: PromptConfig):
        self.config = config

    def build(self, writing_guidance: Optional[List[str]] = None) -> str:
        """Build instruction assuming this is a continuation of an existing work.
        
        Args:
            writing_guidance: Optional list of writing guidance instructions extracted from parentheses
            
        Returns:
            Complete instruction string for the AI model
        """
        parts = [
            "You are an accomplished creative writer and storytelling expert.",
            "Your task is to seamlessly continue an existing story while maintaining consistency in style, tone, and narrative flow."
        ]
        
        # CRITICAL INSTRUCTIONS for generation quality and completeness
        parts.append(
            "CRITICAL INSTRUCTIONS:\n"
            "1. Continue generating until you reach the maximum token limit - do not stop early\n"
            "2. DO NOT rewrite, repeat, or paraphrase the provided context text\n"
            "3. Begin your generation immediately after the last word of the context\n"
            "4. Ensure seamless narrative flow from the context to your generation\n"
            "5. DO NOT write titles, summaries, synopses, taglines, or meta-commentary\n"
            "6. DO NOT start with ellipsis (...) or other continuation markers\n"
            "7. Format your response using Markdown for rich presentation where appropriate"
        )
        
        # Add writing guidance if provided
        if writing_guidance and len(writing_guidance) > 0:
            guidance_text = "\n".join(f"- {g.strip()}" for g in writing_guidance)
            parts.append(
                f"WRITING GUIDANCE (follow these instructions but do not include them in your output):\n{guidance_text}"
            )

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

        # Enhanced quality instructions
        parts.append(
            "Continue the story professionally, maintaining high literary quality that exceeds "
            "general-purpose AI chat responses. Focus on vivid descriptions, natural dialogue, "
            "compelling narrative progression, and immersive storytelling. Your writing should "
            "demonstrate mastery of the craft with attention to pacing, character development, "
            "and atmospheric detail."
        )
        
        return "\n\n".join(parts)

    def build_from_scratch(self, writing_guidance: Optional[List[str]] = None) -> str:
        """Build instruction assuming the story is being generated from the beginning.
        
        Args:
            writing_guidance: Optional list of writing guidance instructions extracted from parentheses
            
        Returns:
            Complete instruction string for the AI model
        """
        parts = [
            "You are an accomplished creative writer specializing in fiction.",
            "Create an engaging story opening based on the provided specifications."
        ]
        
        # CRITICAL INSTRUCTIONS for generation quality
        parts.append(
            "CRITICAL INSTRUCTIONS:\n"
            "1. Generate until you reach the maximum token limit - do not stop early\n"
            "2. DO NOT write titles, summaries, synopses, taglines, or meta-commentary\n"
            "3. DO NOT start with ellipsis (...) or other markers\n"
            "4. JUST START THE STORY BEGINNING directly\n"
            "5. Format your response using Markdown for rich presentation where appropriate"
        )
        
        # Add writing guidance if provided
        if writing_guidance and len(writing_guidance) > 0:
            guidance_text = "\n".join(f"- {g.strip()}" for g in writing_guidance)
            parts.append(
                f"WRITING GUIDANCE (follow these instructions but do not include them in your output):\n{guidance_text}"
            )

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

        # Enhanced quality instructions
        parts.append(
            "Create a compelling story beginning that establishes character, setting, and conflict. "
            "Your writing should demonstrate high literary quality that exceeds general-purpose AI chat responses. "
            "Focus on vivid descriptions, natural dialogue, immersive atmosphere, and engaging narrative hooks. "
            "Write with mastery of the craft, paying attention to pacing, sensory details, and emotional resonance."
        )
        
        return "\n\n".join(parts)