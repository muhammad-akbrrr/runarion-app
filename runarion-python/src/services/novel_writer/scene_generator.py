"""
Stage 2: Prose Generation for the novel writer pipeline.
Generates full novel prose chapter-by-chapter using scene data, entity profiles,
author style, and LLM generation.
"""

import time
import logging
from typing import Dict, Any

from .base_stage import BasePipelineStage, PipelineStageContext, PipelineStageResult
from .story_context import StoryContext, GeneratedChapter
from .prompt_template import NovelWriterPrompts
from utils.llm_retry import call_llm_with_retry

logger = logging.getLogger(__name__)


class ProseGenerationStage(BasePipelineStage):
    """
    Stage 2: Generate novel prose chapter by chapter.

    Reads from: context.metadata['story_context'] (loaded by Stage 1)
    Produces: Populated story_context.generated_chapters
    """

    def __init__(self, db_pool, generation_engine):
        super().__init__(db_pool, "ProseGenerationStage", generation_engine)

    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        story_context: StoryContext = context.get('story_context')
        if not story_context:
            return PipelineStageResult.error_result(
                self.stage_name,
                error="StoryContext not found. Stage 1 must complete first."
            )

        draft_id = context.draft_id
        target_chapter_length = context.config.get('target_chapter_length', 2500)
        total_chapters = story_context.get_total_chapter_count()

        chapters_generated = 0
        chapters_failed = 0
        total_words = 0

        for chapter_idx, chapter in enumerate(story_context.chapters):
            chapter_number = chapter.get('chapter_number', chapter_idx + 1)
            chapter_title = chapter.get('title', f'Chapter {chapter_number}')

            self.logger.info(f"Generating chapter {chapter_number}/{total_chapters}: {chapter_title}")

            try:
                # Get context for this chapter
                chapter_context = story_context.get_chapter_context(chapter_number)
                if not chapter_context:
                    self.logger.warning(f"No context available for chapter {chapter_number}, using fallback")
                    chapters_failed += 1
                    self._store_fallback_chapter(story_context, chapter, chapter_number, chapter_title)
                    continue

                # Build the generation prompt
                prompt = self._build_generation_prompt(
                    story_context, chapter_context, chapter_number,
                    chapter_title, total_chapters, target_chapter_length
                )

                # Generate chapter prose
                chapter_content = self._generate_chapter(prompt, target_chapter_length)

                if not chapter_content:
                    self.logger.warning(f"Generation failed for chapter {chapter_number}, using fallback")
                    chapters_failed += 1
                    self._store_fallback_chapter(story_context, chapter, chapter_number, chapter_title)
                    continue

                word_count = len(chapter_content.split())

                # Generate chapter summary for continuity
                summary = self._generate_chapter_summary(chapter_content, chapter_number)

                # Determine source scenes
                start_scene = chapter.get('start_scene', 0)
                end_scene = chapter.get('end_scene', 0)
                source_scenes = list(range(start_scene, end_scene + 1))

                # Store generated chapter
                story_context.generated_chapters[chapter_number] = GeneratedChapter(
                    chapter_number=chapter_number,
                    title=chapter_title,
                    content=chapter_content,
                    word_count=word_count,
                    summary=summary,
                    source_scenes=source_scenes,
                )

                chapters_generated += 1
                total_words += word_count

                self.logger.info(
                    f"Chapter {chapter_number} generated: {word_count} words"
                )

                # Update draft metadata with progress
                self.update_draft_metadata(draft_id, {
                    'nw_chapters_generated': chapters_generated,
                    'nw_total_chapters': total_chapters,
                    'nw_total_words': total_words,
                })

            except Exception as e:
                self.logger.error(f"Error generating chapter {chapter_number}: {e}")
                chapters_failed += 1
                self._store_fallback_chapter(story_context, chapter, chapter_number, chapter_title)

        # Validate: at least 80% of chapters must generate
        success_rate = chapters_generated / max(total_chapters, 1)
        if success_rate < 0.8:
            return PipelineStageResult.error_result(
                self.stage_name,
                error=(
                    f"Only {chapters_generated}/{total_chapters} chapters generated successfully "
                    f"({success_rate*100:.0f}%). Minimum 80% required."
                ),
                chapters_generated=chapters_generated,
                chapters_failed=chapters_failed,
                total_words=total_words,
            )

        return PipelineStageResult.success_result(
            self.stage_name,
            chapters_generated=chapters_generated,
            chapters_failed=chapters_failed,
            total_chapters=total_chapters,
            total_words=total_words,
        )

    def _build_generation_prompt(self, story_context: StoryContext,
                                  chapter_context: Dict[str, Any],
                                  chapter_number: int, chapter_title: str,
                                  total_chapters: int, target_word_count: int) -> str:
        """Build the full prose generation prompt for a chapter."""
        position = chapter_context.get('chapter_position', {})

        # Author style instructions
        author_style_instructions = NovelWriterPrompts.get_author_style_instruction(
            story_context.author_style
        )

        # Previous chapter summaries
        prev_summaries = chapter_context.get('previous_summaries', [])
        if prev_summaries:
            summaries_text = "\n".join([
                f"Chapter {s['chapter']} ({s['title']}): {s['summary']}"
                for s in prev_summaries
            ])
        else:
            summaries_text = "This is the first chapter - no previous context."

        # Character profiles
        characters = chapter_context.get('characters', {})
        if characters:
            char_parts = []
            for name, profile in characters.items():
                parts = [f"- {name}"]
                if profile.role:
                    parts.append(f"  Role: {profile.role}")
                if profile.traits:
                    parts.append(f"  Traits: {', '.join(profile.traits[:5])}")
                if profile.arc_summary:
                    parts.append(f"  Arc: {profile.arc_summary[:200]}")
                if profile.relationships:
                    rel_strs = [f"{r['target']} ({r['type']})" for r in profile.relationships[:3]]
                    parts.append(f"  Relationships: {', '.join(rel_strs)}")
                char_parts.append("\n".join(parts))
            character_text = "\n".join(char_parts)
        else:
            character_text = "No specific character profiles available."

        # Location profiles
        locations = chapter_context.get('locations', {})
        if locations:
            loc_parts = []
            for name, profile in locations.items():
                parts = [f"- {name}"]
                if profile.description:
                    parts.append(f"  Description: {profile.description[:200]}")
                if profile.atmosphere:
                    parts.append(f"  Atmosphere: {profile.atmosphere[:150]}")
                loc_parts.append("\n".join(parts))
            location_text = "\n".join(loc_parts)
        else:
            location_text = "No specific location profiles available."

        # Active plot threads
        threads = chapter_context.get('active_plot_threads', [])
        if threads:
            thread_parts = []
            for thread in threads[:5]:
                subject = thread.get('report_subject', 'Unknown thread')
                content = thread.get('content_json', {})
                description = content.get('description', '') if isinstance(content, dict) else str(content)[:200]
                thread_parts.append(f"- {subject}: {description[:200]}")
            threads_text = "\n".join(thread_parts)
        else:
            threads_text = "No specific plot threads identified."

        # Scene content (source material)
        scenes = chapter_context.get('scenes', [])
        scene_parts = []
        for scene in scenes:
            scene_num = scene.get('scene_number', '?')
            title = scene.get('title', 'Untitled')
            summary = scene.get('summary', '')
            setting = scene.get('setting', '')
            chars = scene.get('characters', [])
            # Prefer enhanced_content, fall back to original
            content = scene.get('enhanced_content') or scene.get('original_content', '')

            part = f"--- Scene {scene_num}: {title} ---"
            if setting:
                part += f"\nSetting: {setting}"
            if chars:
                char_list = chars if isinstance(chars, list) else [chars]
                part += f"\nCharacters: {', '.join(char_list)}"
            if summary:
                part += f"\nSummary: {summary}"
            if content:
                part += f"\nContent:\n{content}"
            scene_parts.append(part)

        scene_text = "\n\n".join(scene_parts) if scene_parts else "No scene content available."

        # Chapter position guidance
        position_guidance = NovelWriterPrompts.get_chapter_position_guidance(
            is_first=position.get('is_first', False),
            is_last=position.get('is_last', False),
            chapter_number=chapter_number,
            total_chapters=total_chapters,
        )

        # Build final prompt
        prompt_template = NovelWriterPrompts.get_prose_generation_prompt()
        return prompt_template.format(
            chapter_number=chapter_number,
            total_chapters=total_chapters,
            chapter_title=chapter_title,
            chapter_position_guidance=position_guidance,
            author_style_instructions=author_style_instructions,
            previous_chapter_summaries=summaries_text,
            character_profiles=character_text,
            location_profiles=location_text,
            active_plot_threads=threads_text,
            scene_content=scene_text,
            target_word_count=target_word_count,
        )

    def _generate_chapter(self, prompt: str, target_word_count: int,
                           max_retries: int = 2) -> str:
        """Generate a chapter using the LLM with retry logic."""
        # Estimate max tokens: ~1.5 tokens per word, with headroom
        max_output_tokens = max(target_word_count * 2, 4000)

        for attempt in range(max_retries + 1):
            try:
                self.generation_engine.request.prompt = prompt
                self.generation_engine.request.instruction = (
                    "You are a master novelist. Write immersive, vivid novel prose. "
                    "Show, don't tell. Use varied sentence structure and strong verbs."
                )
                self.generation_engine.request.generation_config.max_output_tokens = max_output_tokens

                response = call_llm_with_retry(
                    lambda: self.generation_engine.generate(skip_quota=True)
                )

                # Handle truncation
                if (response.success and hasattr(response, 'metadata')
                        and response.metadata.finish_reason == 'length'):
                    new_limit = int(max_output_tokens * 1.5)
                    self.logger.warning(
                        f"Generation truncated. Increasing tokens from {max_output_tokens} to {new_limit}"
                    )
                    max_output_tokens = new_limit
                    self.generation_engine.request.generation_config.max_output_tokens = new_limit
                    response = call_llm_with_retry(
                        lambda: self.generation_engine.generate(skip_quota=True)
                    )

                if response.success:
                    content = response.text.strip()
                    word_count = len(content.split())

                    # Validate minimum length
                    if word_count < 500:
                        self.logger.warning(
                            f"Generated content too short ({word_count} words). "
                            f"Attempt {attempt + 1}/{max_retries + 1}"
                        )
                        if attempt < max_retries:
                            time.sleep(2 ** attempt)
                            continue

                    return content
                else:
                    error_msg = getattr(response, 'error_message', 'Unknown error')
                    self.logger.warning(f"Generation failed: {error_msg}. Attempt {attempt + 1}")
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                        continue

            except Exception as e:
                self.logger.error(f"Generation exception: {e}. Attempt {attempt + 1}")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue

        return ""

    def _generate_chapter_summary(self, chapter_content: str, chapter_number: int) -> str:
        """Generate a brief summary of a chapter for continuity context."""
        try:
            # Truncate content if very long to avoid exceeding context window
            content_for_summary = chapter_content[:8000] if len(chapter_content) > 8000 else chapter_content

            prompt = NovelWriterPrompts.get_chapter_summary_prompt().format(
                chapter_content=content_for_summary,
                chapter_number=chapter_number,
            )

            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = "Provide a concise chapter summary."
            self.generation_engine.request.generation_config.max_output_tokens = 500

            response = call_llm_with_retry(
                lambda: self.generation_engine.generate(skip_quota=True)
            )

            if response.success:
                return response.text.strip()
            else:
                self.logger.warning(f"Summary generation failed for chapter {chapter_number}")
                return f"Chapter {chapter_number} content generated."

        except Exception as e:
            self.logger.warning(f"Summary generation error for chapter {chapter_number}: {e}")
            return f"Chapter {chapter_number} content generated."

    def _store_fallback_chapter(self, story_context: StoryContext,
                                 chapter: Dict[str, Any],
                                 chapter_number: int, chapter_title: str) -> None:
        """Store a fallback chapter using enhanced scene content when generation fails."""
        start_scene = chapter.get('start_scene', 0)
        end_scene = chapter.get('end_scene', 0)
        source_scenes = list(range(start_scene, end_scene + 1))

        # Concatenate enhanced content from scenes
        parts = []
        for scene in story_context.scenes:
            if start_scene <= scene.get('scene_number', 0) <= end_scene:
                content = scene.get('enhanced_content') or scene.get('original_content', '')
                if content:
                    parts.append(content)

        fallback_content = "\n\n".join(parts) if parts else f"[Chapter {chapter_number} generation failed]"
        word_count = len(fallback_content.split())

        story_context.generated_chapters[chapter_number] = GeneratedChapter(
            chapter_number=chapter_number,
            title=chapter_title,
            content=fallback_content,
            word_count=word_count,
            summary=f"Chapter {chapter_number} (fallback - original scene content used).",
            source_scenes=source_scenes,
        )

        self.logger.info(f"Stored fallback chapter {chapter_number}: {word_count} words from enhanced scenes")
