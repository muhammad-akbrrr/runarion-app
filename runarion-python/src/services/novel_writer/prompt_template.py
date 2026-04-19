"""
Prompt templates for the novel writer pipeline.
Contains specialized prompts for prose generation, quality assessment, and improvement.
"""


class NovelWriterPrompts:
    """
    Collection of prompt templates for novel generation stages.
    All methods are static and return format-string templates with {placeholders}.
    """

    @staticmethod
    def get_prose_generation_prompt() -> str:
        """
        Prompt for Stage 2: Chapter prose generation.

        Placeholders:
            {author_style_instructions} - Author style techniques and guidelines
            {previous_chapter_summaries} - Summaries of previous chapters for continuity
            {character_profiles} - Character profiles relevant to this chapter
            {location_profiles} - Location profiles relevant to this chapter
            {active_plot_threads} - Plot threads active in this chapter's scene range
            {scene_content} - Enhanced scene content (source material)
            {chapter_position_guidance} - Guidance for opening/closing chapters
            {target_word_count} - Target word count for the chapter
            {chapter_title} - Title of the chapter
            {chapter_number} - Chapter number
            {total_chapters} - Total number of chapters
        """
        return """You are a master novelist writing a chapter of a novel. Your task is to transform the scene analysis and summaries below into rich, immersive novel prose.

CHAPTER: {chapter_number} of {total_chapters} - "{chapter_title}"

{chapter_position_guidance}

AUTHOR STYLE GUIDELINES:
{author_style_instructions}

STORY CONTINUITY (previous chapters):
{previous_chapter_summaries}

CHARACTERS IN THIS CHAPTER:
{character_profiles}

LOCATIONS IN THIS CHAPTER:
{location_profiles}

ACTIVE PLOT THREADS:
{active_plot_threads}

SOURCE MATERIAL (scene summaries and enhanced content to transform into prose):
{scene_content}

WRITING REQUIREMENTS:
1. Transform ALL source material into vivid, immersive novel prose
2. Target approximately {target_word_count} words
3. Show, don't tell - bring every moment to life through action, dialogue, and sensory detail
4. Give each character a distinct voice and physicality
5. Create rich atmospheric descriptions for each setting
6. Include meaningful dialogue with subtext and character revelation
7. Maintain perfect continuity with previous chapters
8. Use varied sentence structure and strong verbs
9. Build tension and emotional depth throughout
10. Develop all key events from the source material fully

CRITICAL RULES:
- Do NOT summarize events - expand them into full scenes with dialogue, action, and description
- Do NOT skip any scene from the source material
- Do NOT add meta-commentary or section headers
- Write continuous prose as it would appear in a published novel
- Maintain the author's established style throughout

Write the complete chapter prose:"""

    @staticmethod
    def get_chapter_summary_prompt() -> str:
        """
        Prompt for generating a chapter summary (used for continuity context).

        Placeholders:
            {chapter_content} - The generated chapter content
            {chapter_number} - Chapter number
        """
        return """Summarize Chapter {chapter_number} in 3-5 sentences, capturing:
1. Key events and plot developments
2. Character actions and emotional arcs
3. Any reveals, conflicts, or turning points
4. The chapter's ending state (what's unresolved)

CHAPTER CONTENT:
{chapter_content}

SUMMARY:"""

    @staticmethod
    def get_quality_assessment_prompt() -> str:
        """
        Prompt for Stage 3: Quality assessment of generated chapters.

        Placeholders:
            {chapter_content} - The generated chapter content
            {author_style_reference} - Author style techniques for comparison
            {scene_coverage_checklist} - List of scenes that should be covered
        """
        return """You are a ruthlessly thorough literary quality assessor. Evaluate this chapter against 10 quality dimensions.

CHAPTER CONTENT:
{chapter_content}

AUTHOR STYLE REFERENCE:
{author_style_reference}

SCENE COVERAGE CHECKLIST (all must be present):
{scene_coverage_checklist}

EVALUATE EACH DIMENSION (score 1-10 with specific feedback):

1. OPENING_HOOK: Does the chapter open with an attention-grabbing hook?
2. ENDING_IMPACT: Does the chapter end with strong impact or anticipation?
3. CHARACTER_DESCRIPTIONS: Are characters physically described and distinct? Do they have consistent voices?
4. LOCATION_ATMOSPHERE: Are settings vividly described with sensory detail and atmosphere?
5. DIALOGUE_DEPTH: Does dialogue have depth, subtext, and back-and-forth flow? Are voices distinct?
6. ACTION_PACING: Are action sequences dynamic, detailed, and well-paced?
7. THEMATIC_DEPTH: Are philosophical and thematic elements explored with genuine depth?
8. SHOW_DONT_TELL: Is the prose active and experiential rather than expository?
9. AUTHOR_STYLE: Does the writing match the author's established style and techniques?
10. SCENE_COVERAGE: Are ALL source scenes fully developed in the prose?

Return a JSON object with this EXACT structure:
{{
    "scores": {{
        "opening_hook": <1-10>,
        "ending_impact": <1-10>,
        "character_descriptions": <1-10>,
        "location_atmosphere": <1-10>,
        "dialogue_depth": <1-10>,
        "action_pacing": <1-10>,
        "thematic_depth": <1-10>,
        "show_dont_tell": <1-10>,
        "author_style": <1-10>,
        "scene_coverage": <1-10>
    }},
    "feedback": {{
        "opening_hook": "specific feedback",
        "ending_impact": "specific feedback",
        "character_descriptions": "specific feedback",
        "location_atmosphere": "specific feedback",
        "dialogue_depth": "specific feedback",
        "action_pacing": "specific feedback",
        "thematic_depth": "specific feedback",
        "show_dont_tell": "specific feedback",
        "author_style": "specific feedback",
        "scene_coverage": "specific feedback"
    }},
    "overall_score": <weighted average>,
    "top_issues": ["list of 3 most critical issues to address"]
}}"""

    @staticmethod
    def get_improvement_prompt() -> str:
        """
        Prompt for Stage 4: Targeted chapter improvement.

        Placeholders:
            {chapter_content} - Current chapter text
            {quality_feedback} - Specific feedback from quality assessment
            {weak_dimensions} - Dimensions that scored below threshold
            {expansion_guidance} - Guidance on expansion factors for weak areas
            {author_style_examples} - Relevant author style examples
        """
        return """You are a master literary editor. Improve this chapter to address the specific quality issues identified.

CURRENT CHAPTER:
{chapter_content}

QUALITY ISSUES TO ADDRESS:
{quality_feedback}

WEAKEST DIMENSIONS (focus improvement here):
{weak_dimensions}

EXPANSION GUIDANCE:
{expansion_guidance}

AUTHOR STYLE EXAMPLES (match this voice):
{author_style_examples}

IMPROVEMENT REQUIREMENTS:
1. Address EVERY issue listed in the quality feedback
2. Expand and enrich the weakest dimensions significantly
3. Maintain all existing plot points, character actions, and story events
4. Preserve continuity with the rest of the novel
5. Match the author's established style throughout
6. Do NOT reduce word count - expansions should ADD richness
7. Show don't tell - convert any remaining expository passages to active scenes

CRITICAL RULES:
- Do NOT remove any existing content - only enhance and expand
- Do NOT change character names, settings, or plot events
- Do NOT add meta-commentary or section markers
- Write as continuous novel prose

Return the improved chapter in its entirety:"""

    @staticmethod
    def get_author_style_instruction(author_style) -> str:
        """
        Build a system instruction from an AuthorStyle object.

        Args:
            author_style: AuthorStyle Pydantic model (or None)

        Returns:
            Formatted string incorporating technique descriptions.
        """
        if author_style is None:
            return "No specific author style profile available. Write in a rich, literary style."

        techniques = author_style.techniques
        parts = []

        if techniques.dialogue.conversation_style:
            parts.append(f"DIALOGUE STYLE: {techniques.dialogue.conversation_style}")
        if techniques.dialogue.dialogue_balance:
            parts.append(f"DIALOGUE BALANCE: {techniques.dialogue.dialogue_balance}")
        if techniques.dialogue.character_voices:
            parts.append(f"CHARACTER VOICES: {techniques.dialogue.character_voices}")

        if techniques.action.action_sequences:
            parts.append(f"ACTION SEQUENCES: {techniques.action.action_sequences}")
        if techniques.action.tension:
            parts.append(f"TENSION BUILDING: {techniques.action.tension}")
        if techniques.action.fight_scenes:
            parts.append(f"FIGHT SCENES: {techniques.action.fight_scenes}")

        if techniques.worldbuilding.world_reveals:
            parts.append(f"WORLD REVEALS: {techniques.worldbuilding.world_reveals}")
        if techniques.worldbuilding.exposition:
            parts.append(f"EXPOSITION STYLE: {techniques.worldbuilding.exposition}")
        if techniques.worldbuilding.history_magic:
            parts.append(f"HISTORY/MAGIC: {techniques.worldbuilding.history_magic}")

        if techniques.descriptions.character_descriptions:
            parts.append(f"CHARACTER DESCRIPTIONS: {techniques.descriptions.character_descriptions}")
        if techniques.descriptions.scene_painting:
            parts.append(f"SCENE PAINTING: {techniques.descriptions.scene_painting}")
        if techniques.descriptions.atmosphere:
            parts.append(f"ATMOSPHERE: {techniques.descriptions.atmosphere}")

        if techniques.literary.devices:
            parts.append(f"LITERARY DEVICES: {techniques.literary.devices}")
        if techniques.literary.metaphors:
            parts.append(f"METAPHORS: {techniques.literary.metaphors}")
        if techniques.literary.pacing:
            parts.append(f"PACING: {techniques.literary.pacing}")
        if techniques.literary.scene_structure:
            parts.append(f"SCENE STRUCTURE: {techniques.literary.scene_structure}")
        if techniques.literary.transitions:
            parts.append(f"TRANSITIONS: {techniques.literary.transitions}")

        if not parts:
            return "No specific author style profile available. Write in a rich, literary style."

        return "\n".join(parts)

    @staticmethod
    def get_author_style_examples(author_style, category: str, max_examples: int = 3) -> str:
        """
        Extract relevant examples from AuthorStyle for few-shot prompting.

        Args:
            author_style: AuthorStyle Pydantic model (or None)
            category: One of 'dialogue', 'action', 'worldbuilding', 'descriptions', 'literary'
            max_examples: Maximum number of examples to include

        Returns:
            Formatted string with numbered examples.
        """
        if author_style is None:
            return "No author style examples available."

        examples = author_style.examples
        category_examples = getattr(examples, category, [])

        if not category_examples:
            return f"No {category} examples available from author style profile."

        selected = category_examples[:max_examples]
        parts = [f"AUTHOR STYLE EXAMPLES ({category.upper()}):"]
        for i, example in enumerate(selected, 1):
            parts.append(f"\nExample {i}:\n{example}")

        return "\n".join(parts)

    @staticmethod
    def get_chapter_position_guidance(is_first: bool, is_last: bool,
                                      chapter_number: int, total_chapters: int) -> str:
        """
        Generate position-aware guidance for chapter generation.

        Args:
            is_first: Whether this is the first chapter
            is_last: Whether this is the last chapter
            chapter_number: Current chapter number
            total_chapters: Total number of chapters
        """
        parts = []

        if is_first:
            parts.append(
                "OPENING CHAPTER REQUIREMENTS:\n"
                "- MUST open with an extremely strong hook that grabs the reader immediately\n"
                "- Establish tone, atmosphere, and the central conflict early\n"
                "- Introduce key characters with rich, memorable descriptions\n"
                "- Ground the reader in the world with vivid sensory detail\n"
                "- Create immediate narrative momentum"
            )
        elif is_last:
            parts.append(
                "FINAL CHAPTER REQUIREMENTS:\n"
                "- MUST build toward a powerful, satisfying conclusion\n"
                "- Resolve or meaningfully address the central conflicts\n"
                "- Provide emotional payoff for character arcs\n"
                "- End with strong impact - a resonant final image or moment\n"
                "- Leave a lasting impression on the reader"
            )
        else:
            position_pct = chapter_number / total_chapters
            if position_pct < 0.3:
                parts.append(
                    "EARLY CHAPTER: Continue building the world, deepening characters, "
                    "and establishing stakes. Maintain rising tension."
                )
            elif position_pct < 0.7:
                parts.append(
                    "MIDDLE CHAPTER: Escalate conflicts, deepen relationships, "
                    "deliver on established promises. Maintain strong pacing."
                )
            else:
                parts.append(
                    "LATE CHAPTER: Build toward climax, increase tension and stakes, "
                    "begin resolving plot threads. Maintain urgency."
                )

        return "\n".join(parts)
