# utils/story_instruction_builder.py

from models.story_generation.prompt_config import PromptConfig
from typing import List, Optional


# Words and phrases that are overused by AI and should be avoided for natural-sounding prose
# Based on CoAuth's implementation and industry best practices
BANNED_AI_CLICHES = [
    "tapestry", "symphony", "delve", "underscore", "vibrant", "testament",
    "crucible", "nuance", "landscape", "realm", "foster", "invaluable",
    "game-changer", "unleash", "elevate", "cutting-edge", "robust",
    "transformative", "pivot", "synergy", "paradigm", "stark contrast",
    "rich history", "testament to", "serves as", "a sense of", "palpable",
    "whispered promises", "dance of", "symphony of", "tapestry of",
    "echoed through", "myriad of", "plethora of", "in the realm of",
    "journey of discovery", "nestled in", "bathed in", "shrouded in",
    "a testament to", "the very fabric of", "in the heart of"
]


# Preset-based writing style configurations
# These define how the AI should approach different types of writing
# TODO: These presets could be moved to database or made user-configurable
WRITING_PRESETS = {
    "story-telling": {
        "persona": "You are an accomplished storyteller and narrative craftsman.",
        "focus": "Focus on engaging narrative flow, vivid characters, and immersive world-building. "
                 "Prioritize emotional resonance and reader engagement over technical precision.",
        "style_notes": "Use varied pacing, build tension naturally, and create memorable moments."
    },
    "creative-writing": {
        "persona": "You are a literary fiction writer with mastery over language and form.",
        "focus": "Focus on artistic expression, unique voice, and literary techniques. "
                 "Experiment with structure, metaphor, and subtext.",
        "style_notes": "Prioritize originality, depth of meaning, and stylistic innovation."
    },
    "technical-writing": {
        "persona": "You are a clear, precise technical writer.",
        "focus": "Focus on clarity, accuracy, and logical structure. "
                 "Ensure information is accessible and well-organized.",
        "style_notes": "Use concise language, avoid ambiguity, maintain consistent terminology."
    },
}


class InstructionBuilder:
    """Builds instructions for creative writing tasks based on the provided configuration.
    
    Enhanced with anti-AI-slop measures and humanization techniques based on
    best practices for creative AI writing.
    
    Supports:
    - Writing presets (story-telling, creative-writing, technical-writing)
    - Author style DNA (from AuthorStyle analyzer or custom text)
    - User-defined context (memory), genre, tone, POV
    - Writing guidance extracted from parentheses in user content
    
    NOTE: Author profiles should come from the AuthorStyle analyzer system.
    The style analyzer creates structured style data stored in the database.
    When integrated, the author_profile field should contain the formatted
    style DNA from AuthorStyleTechniques + AuthorStyleExamples.
    """

    def __init__(self, config: PromptConfig):
        self.config = config
    
    def _get_preset_config(self) -> dict:
        """Get preset configuration based on current_preset setting."""
        preset_key = (self.config.current_preset or "story-telling").lower().strip()
        return WRITING_PRESETS.get(preset_key, WRITING_PRESETS["story-telling"])
    
    def _get_author_style(self) -> Optional[str]:
        """
        Get author style DNA text for the prompt.
        
        This should receive the formatted AuthorStyle data from the style analyzer.
        The AuthorStyle contains:
        - techniques: dialogue, action, worldbuilding, descriptions, literary
        - examples: sample snippets for each category
        
        For now, if author_profile contains any text, use it directly as style DNA.
        
        TODO: When fully integrated, this will receive pre-formatted style DNA
        from Laravel after it looks up the AuthorStyle from the database.
        """
        if not self.config.author_profile:
            return None
        
        profile_text = self.config.author_profile.strip()
        if profile_text:
            return profile_text
        
        return None

    def _build_negative_constraints(self) -> str:
        """Build negative constraints section to avoid AI clichés and robotic patterns."""
        constraints = [
            "NEGATIVE CONSTRAINTS (Strictly AVOID these patterns):",
            f"- Do NOT use these overused AI words/phrases: {', '.join(BANNED_AI_CLICHES[:15])}",
            "- Avoid perfectly balanced sentence structures - vary rhythm aggressively",
            "- Do NOT moralize or summarize at the end of scenes",
            "- Avoid filter words like 'he saw', 'she felt', 'it seemed' - describe the sensation directly",
            "- Do NOT use overly flowery or purple prose",
            "- Avoid repetitive sentence starters within the same paragraph",
            "- Do NOT write in an overly polished, synthetic tone - embrace natural imperfection"
        ]
        return "\n".join(constraints)

    def _build_humanization_instructions(self) -> str:
        """Build instructions for more human-like, natural prose."""
        return (
            "HUMANIZATION GUIDELINES:\n"
            "- Vary sentence length aggressively: mix short punchy sentences with longer flowing ones\n"
            "- Use occasional sentence fragments for impact and rhythm\n"
            "- Focus on concrete, sensory details rather than abstract descriptions\n"
            "- Write dialogue that sounds like actual speech, with interruptions and trailing off\n"
            "- Show emotions through physical reactions and actions, not labels\n"
            "- Let subtext do the work - not everything needs to be stated explicitly"
        )

    def build(self, writing_guidance: Optional[List[str]] = None) -> str:
        """Build instruction assuming this is a continuation of an existing work.
        
        Args:
            writing_guidance: Optional list of writing guidance instructions extracted from parentheses
            
        Returns:
            Complete instruction string for the AI model
        """
        # Get preset configuration
        preset = self._get_preset_config()
        
        parts = [
            preset["persona"],
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
        
        # Add preset-specific focus
        parts.append(f"WRITING FOCUS:\n{preset['focus']}")
        
        # Add writing guidance if provided (from parentheses in user content)
        if writing_guidance and len(writing_guidance) > 0:
            guidance_text = "\n".join(f"- {g.strip()}" for g in writing_guidance)
            parts.append(
                f"WRITING GUIDANCE (follow these instructions but do not include them in your output):\n{guidance_text}"
            )

        # Memory / Story context from sidebar
        if self.config.context:
            parts.append(
                f"STORY CONTEXT (remember this information):\n{self.config.context.strip()}")

        # Story metadata from sidebar
        if self.config.genre:
            parts.append(f"GENRE: **{self.config.genre.strip()}**")

        if self.config.tone:
            parts.append(f"TONE: **{self.config.tone.strip()}**")

        if self.config.pov:
            parts.append(f"POINT OF VIEW: **{self.config.pov.strip()}**")

        # Author style DNA (lookup or custom)
        author_style = self._get_author_style()
        if author_style:
            parts.append(f"STYLE DNA (strictly adhere to this writing style):\n{author_style}")

        # Add negative constraints to avoid AI clichés
        parts.append(self._build_negative_constraints())
        
        # Add humanization guidelines
        parts.append(self._build_humanization_instructions())

        # Enhanced quality instructions with preset style notes
        parts.append(
            f"QUALITY STANDARDS:\n"
            f"Continue the story with high literary quality. {preset['style_notes']} "
            f"Focus on vivid, concrete descriptions; natural-sounding dialogue; "
            f"compelling narrative progression; and immersive storytelling. "
            f"Write prose that feels distinctly human, with texture, grit, and emotional authenticity."
        )
        
        return "\n\n".join(parts)

    def build_from_scratch(self, writing_guidance: Optional[List[str]] = None) -> str:
        """Build instruction assuming the story is being generated from the beginning.
        
        Args:
            writing_guidance: Optional list of writing guidance instructions extracted from parentheses
            
        Returns:
            Complete instruction string for the AI model
        """
        # Get preset configuration
        preset = self._get_preset_config()
        
        parts = [
            preset["persona"],
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
        
        # Add preset-specific focus
        parts.append(f"WRITING FOCUS:\n{preset['focus']}")
        
        # Add writing guidance if provided (from parentheses in user content)
        if writing_guidance and len(writing_guidance) > 0:
            guidance_text = "\n".join(f"- {g.strip()}" for g in writing_guidance)
            parts.append(
                f"WRITING GUIDANCE (follow these instructions but do not include them in your output):\n{guidance_text}"
            )

        # Memory / Story context from sidebar
        if self.config.context:
            parts.append(
                f"STORY CONTEXT (remember this information):\n{self.config.context.strip()}")

        # Story metadata from sidebar
        if self.config.genre:
            parts.append(f"GENRE: **{self.config.genre.strip()}**")

        if self.config.tone:
            parts.append(f"TONE: **{self.config.tone.strip()}**")

        if self.config.pov:
            parts.append(f"POINT OF VIEW: **{self.config.pov.strip()}**")

        # Author style DNA (lookup or custom)
        author_style = self._get_author_style()
        if author_style:
            parts.append(f"STYLE DNA (strictly adhere to this writing style):\n{author_style}")

        # Add negative constraints to avoid AI clichés
        parts.append(self._build_negative_constraints())
        
        # Add humanization guidelines
        parts.append(self._build_humanization_instructions())

        # Enhanced quality instructions with preset style notes
        parts.append(
            f"QUALITY STANDARDS:\n"
            f"Create a compelling story beginning that establishes character, setting, and conflict. "
            f"{preset['style_notes']} Focus on vivid, concrete descriptions; natural-sounding dialogue; "
            f"immersive atmosphere; and engaging narrative hooks. Write prose that feels distinctly human - "
            f"with texture, grit, and emotional authenticity."
        )
        
        return "\n\n".join(parts)