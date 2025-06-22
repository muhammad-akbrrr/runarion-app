from typing import Literal, Optional, TypedDict
from models.request import BaseGenerationRequest, CallerInfo, GenerationConfig
from models.deconstructor.story_rewrite import ContentRewriteConfig
from services.usecase_handler.base_handler import UseCaseHandler

# Prompt template for content rewriting
CONTENT_REWRITE_TEMPLATE = """
You are a skilled content rewriter. Your task is to rewrite the given text in the style of a specific author while maintaining the core meaning and adapting to the specified writing perspective.

AUTHOR STYLE ANALYSIS:
{author_style_analysis}

WRITING PERSPECTIVE:
- Type: {perspective_type}
- Narrator Voice: {narrator_voice}
- Character Focus: {character_focus}

ADDITIONAL REQUIREMENTS:
- Target Genre: {target_genre}
- Target Tone: {target_tone}
- Preserve Elements: {preserve_elements}
- Target Length: {target_length}
- Style Intensity: {style_intensity}

ORIGINAL TEXT:
{original_text}

INSTRUCTIONS:
1. Analyze the author's style patterns from the provided analysis
2. Rewrite the text in that author's style while maintaining the core meaning
3. Adapt the narrative perspective as specified
4. Preserve the key elements mentioned
5. Match the target length and tone requirements
6. Apply the style with the specified intensity level

Return only the rewritten text without any explanations or formatting.
"""


class ContentRewriteRequest(TypedDict):
    mode: Literal["rewrite"]
    provider: Optional[str]
    model: Optional[str]
    original_text: str
    rewrite_config: ContentRewriteConfig
    generation_config: GenerationConfig
    caller: CallerInfo


class ContentRewriteHandler(UseCaseHandler):
    """
    A handler class to prepare generation requests for content rewriting.
    """

    def build_request(self, raw_json: ContentRewriteRequest) -> BaseGenerationRequest:
        config = raw_json["rewrite_config"]

        # Format the author style analysis for the prompt
        author_style_analysis = self._format_author_style(config.author_style)

        # Format the writing perspective
        perspective_info = self._format_perspective(config.writing_perspective)

        prompt = CONTENT_REWRITE_TEMPLATE.format(
            author_style_analysis=author_style_analysis,
            perspective_type=config.writing_perspective.type,
            narrator_voice=config.writing_perspective.narrator_voice or "default",
            character_focus=config.writing_perspective.character_focus or "main character",
            target_genre=config.target_genre or "general",
            target_tone=config.target_tone or "neutral",
            preserve_elements=", ".join(
                config.preserve_key_elements) if config.preserve_key_elements else "core meaning",
            target_length=config.target_length,
            style_intensity=config.style_intensity,
            original_text=raw_json["original_text"]
        )

        return BaseGenerationRequest(
            provider=raw_json.get("provider") or "openai",
            model=raw_json.get("model"),
            prompt=prompt,
            instruction="Rewrite the given text in the specified author's style and perspective.",
            generation_config=raw_json["generation_config"],
            caller=raw_json["caller"],
        )

    def _format_author_style(self, author_style) -> str:
        """Format the author style analysis for the prompt"""
        analysis = []

        # Add techniques
        if author_style.techniques.dialogue.conversation_style:
            analysis.append(
                f"Dialogue Style: {author_style.techniques.dialogue.conversation_style}")
        if author_style.techniques.descriptions.scene_painting:
            analysis.append(
                f"Scene Description: {author_style.techniques.descriptions.scene_painting}")
        if author_style.techniques.literary.word_patterns:
            analysis.append(
                f"Word Patterns: {author_style.techniques.literary.word_patterns}")
        if author_style.techniques.literary.pacing:
            analysis.append(
                f"Pacing: {author_style.techniques.literary.pacing}")

        # Add examples
        if author_style.examples.dialogue:
            analysis.append(
                f"Dialogue Examples: {'; '.join(author_style.examples.dialogue[:2])}")
        if author_style.examples.descriptions:
            analysis.append(
                f"Description Examples: {'; '.join(author_style.examples.descriptions[:2])}")

        return "\n".join(analysis) if analysis else "General author style patterns"

    def _format_perspective(self, perspective) -> str:
        """Format the writing perspective for the prompt"""
        perspective_descriptions = {
            "first_person": "Use first-person perspective (I, me, my)",
            "second_person": "Use second-person perspective (you, your)",
            "third_person_omniscient": "Use third-person omniscient perspective (he/she/they with access to all characters' thoughts)",
            "third_person_limited": "Use third-person limited perspective (he/she/they with access to one character's thoughts)"
        }
        return perspective_descriptions.get(perspective.type, "Use third-person limited perspective")
