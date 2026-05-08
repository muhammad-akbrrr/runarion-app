"""
Prompt templates for the novel writer pipeline.
"""


class NovelWriterPrompts:
    @staticmethod
    def get_prose_generation_prompt() -> str:
        return """You are rewriting source material into finished chapter prose while preserving structural fidelity.

CHAPTER: {chapter_number} of {total_chapters} - "{chapter_title}"

CHAPTER FUNCTION GUIDANCE:
{chapter_position_guidance}

REWRITE POLICY:
{rewrite_policy_guidance}

NEGATIVE CONSTRAINTS:
{negative_constraints}

AUTHOR STYLE WEIGHT:
{author_style_weight}

AUTHOR STYLE GUIDANCE:
{author_style_instructions}

WRITING PERSPECTIVE (HARD CONSTRAINT):
{writing_perspective_instruction}

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
1. Preserve all source events, scene order, and chapter boundaries.
2. Target approximately {target_word_count} words without forcing expansion.
3. Rewrite into cohesive prose that follows the compiled rewrite policy.
4. Keep continuity with previous chapters and explicit story facts.
5. Use only portable author-style traits when style transfer is requested.
6. Obey every negative constraint.
7. Keep narrative perspective consistent with the required writing perspective.

CRITICAL RULES:
- Do NOT skip any source scene.
- Do NOT invent new plot events, settings, or character decisions.
- Do NOT override manuscript structure with author-style quirks.
- Do NOT add meta-commentary or section headers.
- Do NOT introduce forbidden style markers from the negative constraints.

Write the complete chapter prose:"""

    @staticmethod
    def get_chapter_summary_prompt() -> str:
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
        return """You are a policy-aware chapter assessor. Evaluate this chapter against 14 dimensions using the rewrite policy and structural requirements, not generic literary defaults.

CHAPTER CONTENT:
{chapter_content}

REWRITE POLICY:
{rewrite_policy_guidance}

NEGATIVE CONSTRAINTS:
{negative_constraints}

AUTHOR STYLE REFERENCE:
{author_style_reference}

REQUIRED WRITING PERSPECTIVE:
{writing_perspective_instruction}

SCENE COVERAGE CHECKLIST (all must be present):
{scene_coverage_checklist}

SCORING MODEL:
- HARD INVARIANTS: scene coverage, POV consistency, perspective continuity, chapter-break integrity, redundancy control
- POLICY-ALIGNED STYLE FIT: opening/ending force, description density, dialogue depth, atmosphere, thematic depth, exposition balance, author-style transfer

EVALUATE EACH DIMENSION (score 1-10 with specific feedback):

1. OPENING_HOOK: Does the chapter opening suit the intended policy and chapter function, whether restrained or dramatic?
2. ENDING_IMPACT: Does the chapter ending fit the intended policy and chapter function, whether quiet or forceful?
3. CHARACTER_DESCRIPTIONS: Are character portrayals clear, distinct, and appropriate to the requested style balance?
4. LOCATION_ATMOSPHERE: Are setting details clear and policy-aligned without forcing ornamental excess?
5. DIALOGUE_DEPTH: Does dialogue fit the requested tone, clarity, and speaker differentiation?
6. ACTION_PACING: Does scene motion fit the intended tempo without distortion?
7. THEMATIC_DEPTH: Are themes handled at the depth appropriate for the rewrite policy and source material?
8. SHOW_DONT_TELL: Does exposition balance with scene rendering in a policy-appropriate way?
9. AUTHOR_STYLE: Does the surface writing follow the allowed portable author-style traits and avoid transfer risks?
10. SCENE_COVERAGE: Are ALL source scenes fully represented in the prose?
11. POV_CONSISTENCY: Does the chapter consistently maintain the required narrative person (first/second/third)?
12. PERSPECTIVE_CONTINUITY: Does viewpoint control remain stable without unjustified drift or head-hopping?
13. CHAPTER_BREAK_INTEGRITY: Do chapter transitions preserve source momentum and logic?
14. REDUNDANCY_CONTROL: Is prose controlled and non-repetitive according to the rewrite policy?

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
        "scene_coverage": <1-10>,
        "pov_consistency": <1-10>,
        "perspective_continuity": <1-10>,
        "chapter_break_integrity": <1-10>,
        "redundancy_control": <1-10>
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
        "scene_coverage": "specific feedback",
        "pov_consistency": "specific feedback",
        "perspective_continuity": "specific feedback",
        "chapter_break_integrity": "specific feedback",
        "redundancy_control": "specific feedback"
    }},
    "overall_score": <weighted average>,
    "top_issues": ["list of 3 most critical issues to address"]
}}"""

    @staticmethod
    def get_improvement_prompt() -> str:
        return """You are revising a generated chapter to satisfy a compiled rewrite policy.

CURRENT CHAPTER:
{chapter_content}

REWRITE POLICY:
{rewrite_policy_guidance}

NEGATIVE CONSTRAINTS:
{negative_constraints}

QUALITY ISSUES TO ADDRESS:
{quality_feedback}

WEAKEST DIMENSIONS (focus improvement here):
{weak_dimensions}

REVISION GUIDANCE:
{expansion_guidance}

REVISION MODE:
{revision_mode_guidance}

AUTHOR STYLE EXAMPLES (portable traits only):
{author_style_examples}

REQUIRED WRITING PERSPECTIVE:
{writing_perspective_instruction}

IMPROVEMENT REQUIREMENTS:
1. Address the listed policy and craft issues only.
2. Preserve all plot points, character actions, and story events.
3. Preserve chapter structure, continuity, and perspective.
4. Use author style only within the allowed policy boundaries.
5. Respect every negative constraint.
6. Tighten, preserve, or expand only as required by the feedback.

CRITICAL RULES:
- Do NOT add ornamental prose just to sound literary.
- Do NOT inject melodrama, archaism, or tonal escalation unless explicitly requested.
- Do NOT remove required source content.
- Do NOT add meta-commentary or section markers.

Return the improved chapter in its entirety:"""

    @staticmethod
    def get_author_style_instruction(author_style, compiled_policy=None) -> str:
        if author_style is None:
            return (
                "No author style profile available. Preserve manuscript-native style characteristics "
                "instead of inventing a new default voice."
            )

        techniques = author_style.techniques
        parts = []

        if techniques.voice.diction:
            parts.append(f"VOICE DICTION: {techniques.voice.diction}")
        if techniques.voice.syntax:
            parts.append(f"VOICE SYNTAX: {techniques.voice.syntax}")
        if techniques.voice.rhythm:
            parts.append(f"VOICE RHYTHM: {techniques.voice.rhythm}")
        if techniques.voice.register:
            parts.append(f"VOICE REGISTER: {techniques.voice.register}")
        if techniques.voice.figurative_language:
            parts.append(f"FIGURATIVE LANGUAGE: {techniques.voice.figurative_language}")

        if techniques.dialogue.conversation_style:
            parts.append(f"DIALOGUE STRUCTURE: {techniques.dialogue.conversation_style}")
        if techniques.dialogue.speaker_differentiation:
            parts.append(f"SPEAKER DIFFERENTIATION: {techniques.dialogue.speaker_differentiation}")
        if techniques.dialogue.dialogue_narration_balance:
            parts.append(f"DIALOGUE/NARRATION BALANCE: {techniques.dialogue.dialogue_narration_balance}")

        if techniques.description.description_density:
            parts.append(f"DESCRIPTION DENSITY: {techniques.description.description_density}")
        if techniques.description.sensory_focus:
            parts.append(f"SENSORY FOCUS: {techniques.description.sensory_focus}")
        if techniques.description.atmosphere_strategy:
            parts.append(f"ATMOSPHERE STRATEGY: {techniques.description.atmosphere_strategy}")

        if techniques.exposition.exposition_strategy:
            parts.append(f"EXPOSITION STRATEGY: {techniques.exposition.exposition_strategy}")
        if techniques.exposition.context_integration:
            parts.append(f"CONTEXT INTEGRATION: {techniques.exposition.context_integration}")
        if techniques.exposition.terminology_handling:
            parts.append(f"TERMINOLOGY HANDLING: {techniques.exposition.terminology_handling}")

        if techniques.pacing.scene_tempo:
            parts.append(f"SCENE TEMPO: {techniques.pacing.scene_tempo}")
        if techniques.pacing.transition_style:
            parts.append(f"TRANSITION STYLE: {techniques.pacing.transition_style}")
        if techniques.pacing.tension_pattern:
            parts.append(f"TENSION PATTERN: {techniques.pacing.tension_pattern}")

        if techniques.narrative.pov_tendency:
            parts.append(f"POV TENDENCY: {techniques.narrative.pov_tendency}")
        if techniques.narrative.narrative_distance:
            parts.append(f"NARRATIVE DISTANCE: {techniques.narrative.narrative_distance}")
        if techniques.narrative.redundancy_avoidance:
            parts.append(f"REDUNDANCY AVOIDANCE: {techniques.narrative.redundancy_avoidance}")

        if author_style.adaptation.portable_traits:
            parts.append(
                "PORTABLE TRAITS:\n" +
                "\n".join(f"- {item}" for item in author_style.adaptation.portable_traits)
            )
        if author_style.adaptation.non_portable_markers:
            parts.append(
                "NON-PORTABLE MARKERS TO AVOID OVER-APPLYING:\n" +
                "\n".join(f"- {item}" for item in author_style.adaptation.non_portable_markers)
            )
        if author_style.adaptation.transfer_risks:
            parts.append(
                "TRANSFER RISKS:\n" +
                "\n".join(f"- {item}" for item in author_style.adaptation.transfer_risks)
            )
        if author_style.adaptation.suppression_guidance:
            parts.append(
                "SUPPRESSION GUIDANCE:\n" +
                "\n".join(f"- {item}" for item in author_style.adaptation.suppression_guidance)
            )

        if compiled_policy is not None:
            parts.append(f"AUTHOR STYLE WEIGHT: {compiled_policy.author_style_weight}")

        return "\n".join(parts) if parts else (
            "No author style profile available. Preserve manuscript-native style characteristics."
        )

    @staticmethod
    def get_writing_perspective_instruction(writing_perspective: str) -> str:
        mapping = {
            'first_person': (
                "Use FIRST PERSON throughout (I/me/my). "
                "The narrator is the viewpoint character. Never switch to third or second person."
            ),
            'second_person': (
                "Use SECOND PERSON throughout (you/your). "
                "Address the protagonist as 'you'. Never switch to first or third person."
            ),
            'third_person_limited': (
                "Use THIRD PERSON LIMITED throughout (he/she/they). "
                "Stay anchored to one viewpoint character's internal access at a time. "
                "Do not shift into omniscient narration."
            ),
            'third_person_omniscient': (
                "Use THIRD PERSON OMNISCIENT throughout. "
                "Narrator may access multiple characters' internal states, "
                "but keep tense and person stable."
            ),
        }
        return mapping.get(writing_perspective, mapping['third_person_limited'])

    @staticmethod
    def get_author_style_examples(author_style, category: str, max_examples: int = 3) -> str:
        if author_style is None:
            return "No author style examples available."

        category_examples = getattr(author_style.examples, category, [])
        if not category_examples:
            return f"No {category} examples available from author style profile."

        selected = category_examples[:max_examples]
        parts = [f"AUTHOR STYLE EXAMPLES ({category.upper()}):"]
        for i, example in enumerate(selected, 1):
            parts.append(f"\nExample {i}:\n{example}")
        return "\n".join(parts)

    @staticmethod
    def get_chapter_position_guidance(
        is_first: bool,
        is_last: bool,
        chapter_number: int,
        total_chapters: int,
    ) -> str:
        if is_first:
            return (
                "OPENING CHAPTER: Preserve the manuscript's initial cadence and framing. "
                "Establish only what the source material actually establishes."
            )
        if is_last:
            return (
                "FINAL CHAPTER: Preserve the manuscript's ending logic and emotional scale. "
                "Do not force a bigger ending than the source supports."
            )

        position_pct = chapter_number / max(total_chapters, 1)
        if position_pct < 0.3:
            return "EARLY CHAPTER: Preserve source setup and pacing without forcing extra escalation."
        if position_pct < 0.7:
            return "MIDDLE CHAPTER: Preserve source momentum and transitions without artificial inflation."
        return "LATE CHAPTER: Preserve source convergence and urgency only where the material supports it."
