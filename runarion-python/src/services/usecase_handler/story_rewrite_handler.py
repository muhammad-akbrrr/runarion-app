from typing import Literal, Optional, TypedDict, List, Dict
from models.request import BaseGenerationRequest, CallerInfo, GenerationConfig
from models.deconstructor.story_rewrite import ContentRewriteConfig
from services.usecase_handler.base_handler import UseCaseHandler

# Prompt template for story rewriting by chapter using structured author style
STORY_REWRITE_TEMPLATE = """
You are a skilled fiction writer. Your task is to rewrite the given chapter of a story in the style of a specific author, following the provided structured author style analysis and adapting to the specified writing perspective and chapter breakdown.

STRUCTURED AUTHOR STYLE (JSON):
{author_style_json}

CHAPTER BREAKDOWN:
- Chapter Name: {chapter_name}
- Chapter Summary: {chapter_summary}
- Key Plot Points: {chapter_plot_points}

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

ORIGINAL CHAPTER TEXT:
{original_text}

INSTRUCTIONS:
1. Carefully study the structured author style JSON and apply its patterns and techniques throughout the rewrite.
2. Use the chapter breakdown to ensure the rewrite matches the intended structure, summary, and plot points.
3. Adapt the narrative perspective as specified.
4. Preserve the key elements and match the target length and tone requirements.
5. Apply the style with the specified intensity level.

Return only the rewritten chapter text, without any explanations or formatting.
"""

# Prompt template for story structure analysis
STORY_STRUCTURE_PROMPT = """
You are a literary analyst. Your task is to analyze the provided story draft and break it down into a structured outline of chapters. For each chapter, provide:
- Chapter name (creative, concise)
- Chapter summary (2-3 sentences)
- Key plot points (bulleted list)
- The start and end indices of the text span (or paragraph numbers) that make up the chapter

IMPORTANT:
- The start_idx and end_idx for each chapter MUST be integers within the range of the provided paragraphs (0 to N-1, where N is the total number of paragraphs).
- NEVER set start_idx or end_idx to a value less than 0 or greater than N-1.
- Ensure start_idx <= end_idx for each chapter.
- Do not invent content; base your breakdown only on the provided text.

Return a JSON array, where each item is an object with:
- chapter_name: str
- summary: str
- plot_points: list[str]
- start_idx: int (paragraph or chunk index, inclusive)
- end_idx: int (paragraph or chunk index, inclusive)

Analyze the story for natural breaks, changes in scene, time, or major events. Do not invent content; base your breakdown only on the provided text.

STORY DRAFT:
{text}

INSTRUCTIONS:
- Carefully read the story draft.
- Divide it into logical chapters.
- For each chapter, fill out the required fields.
- Return only the JSON array, no explanations or extra text.
"""


class StoryRewriteRequest(TypedDict):
    mode: Literal["rewrite"]
    provider: Optional[str]
    model: Optional[str]
    original_text: str
    author_style_json: dict
    chapter_name: str
    chapter_summary: str
    chapter_plot_points: List[str]
    rewrite_config: ContentRewriteConfig
    generation_config: GenerationConfig
    caller: CallerInfo


class StoryStructureRequest(TypedDict):
    mode: Literal["structure"]
    provider: Optional[str]
    model: Optional[str]
    text: str
    generation_config: GenerationConfig
    caller: CallerInfo


class StoryRewriteHandler(UseCaseHandler):
    """
    A handler class to prepare generation requests for story rewriting by chapter using structured author style.
    """

    def build_request(self, raw_json: StoryRewriteRequest) -> BaseGenerationRequest:
        config = raw_json["rewrite_config"]
        author_style_json = raw_json["author_style_json"]
        chapter_name = raw_json["chapter_name"]
        chapter_summary = raw_json["chapter_summary"]
        chapter_plot_points = ", ".join(
            raw_json["chapter_plot_points"]) if raw_json["chapter_plot_points"] else ""

        prompt = STORY_REWRITE_TEMPLATE.format(
            author_style_json=author_style_json,
            chapter_name=chapter_name,
            chapter_summary=chapter_summary,
            chapter_plot_points=chapter_plot_points,
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
            instruction="Rewrite the given chapter in the specified author's style and perspective, following the chapter breakdown.",
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


class StoryStructureHandler(UseCaseHandler):
    """
    Handler to prepare generation requests for story structure/chapter breakdown analysis.
    """

    def build_request(self, raw_json: StoryStructureRequest) -> BaseGenerationRequest:
        prompt = STORY_STRUCTURE_PROMPT.format(text=raw_json["text"])
        # Use a strict instruction to avoid markdown/code blocks or extra text
        instruction = (
            "Analyze the story draft and return a structured JSON array of chapters as described. "
            "Return only the JSON array, no explanations, no markdown, no extra text. "
            "Do not wrap the output in code blocks."
        )
        return BaseGenerationRequest(
            provider=raw_json.get("provider") or "openai",
            model=raw_json.get("model"),
            prompt=prompt,
            instruction=instruction,
            generation_config=raw_json["generation_config"],
            caller=raw_json["caller"],
        )
