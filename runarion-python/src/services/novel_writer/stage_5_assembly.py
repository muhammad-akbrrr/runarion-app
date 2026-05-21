"""
Stage 5: Manuscript Assembly for the novel writer pipeline.
Writes final chapters and assembled manuscript to the database.
Zero LLM calls - pure data assembly and persistence.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from .base_stage import BasePipelineStage, PipelineStageContext, PipelineStageResult
from .story_context import StoryContext

logger = logging.getLogger(__name__)


class ManuscriptAssemblyStage(BasePipelineStage):
    """
    Stage 5: Assemble and persist the final manuscript.

    Reads from:
        context.metadata['story_context'] (generated_chapters)
        context.metadata['quality_assessments']
    Produces:
        Rows in `chapters` and `final_manuscripts` tables.
    """

    def __init__(self, db_pool):
        super().__init__(db_pool, "ManuscriptAssemblyStage")

    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        story_context: StoryContext = context.get('story_context')
        if not story_context:
            return PipelineStageResult.error_result(
                self.stage_name,
                error="StoryContext not found."
            )

        if not story_context.generated_chapters:
            return PipelineStageResult.error_result(
                self.stage_name,
                error="No generated chapters found."
            )

        draft_id = context.draft_id
        quality_assessments = context.get('quality_assessments', {})
        conn = context.get('connection')

        try:
            if conn:
                cursor = conn.cursor()
                result = self._assemble_and_persist(
                    cursor, draft_id, story_context, quality_assessments, context
                )
                cursor.close()
            else:
                from src.utils.database_utils import utf8_database_connection
                with utf8_database_connection(self.db_pool) as db_conn:
                    cursor = db_conn.cursor()
                    result = self._assemble_and_persist(
                        cursor, draft_id, story_context, quality_assessments, context
                    )
                    cursor.close()

            return result

        except Exception as e:
            self.logger.error(f"Manuscript assembly failed for draft {draft_id}: {e}")
            return PipelineStageResult.error_result(
                self.stage_name,
                error=str(e)
            )

    def _assemble_and_persist(self, cursor, draft_id: str,
                               story_context: StoryContext,
                               quality_assessments: Dict[str, Any],
                               context: PipelineStageContext) -> PipelineStageResult:
        """Assemble the manuscript and write to DB."""
        from src.utils.database_utils import clean_text_for_database, ensure_utf8_json
        from ulid import ULID

        # Step 1: Delete existing novel_writer chapters for this draft
        cursor.execute("DELETE FROM chapters WHERE draft_id = %s", (draft_id,))
        deleted_chapters = cursor.rowcount
        if deleted_chapters > 0:
            self.logger.info(f"Deleted {deleted_chapters} existing chapters for draft {draft_id}")

        # Step 2: Insert generated chapters
        chapters_stored = 0
        total_word_count = 0
        chapter_summaries = []

        for chapter_number, chapter in sorted(story_context.generated_chapters.items()):
            chapter_id = str(ULID())
            cleaned_content = clean_text_for_database(
                chapter.content,
                preserve_line_breaks=True,
            )
            word_count = len(cleaned_content.split())

            # Get source chapter data from deconstructor
            source_chapter = next(
                (c for c in story_context.chapters if c.get('chapter_number') == chapter_number),
                {}
            )

            start_scene = source_chapter.get('start_scene', 0)
            end_scene = source_chapter.get('end_scene', 0)
            scene_count = source_chapter.get('scene_count', len(chapter.source_scenes))
            scene_titles = source_chapter.get('scene_titles', [])

            cursor.execute("""
                INSERT INTO chapters (id, draft_id, chapter_number, title, content,
                                     word_count, start_scene, end_scene, scene_count, scene_titles)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                chapter_id, draft_id, chapter_number, chapter.title,
                cleaned_content, word_count, start_scene, end_scene,
                scene_count, ensure_utf8_json(scene_titles),
            ))

            chapters_stored += 1
            total_word_count += word_count

            chapter_summaries.append({
                'chapter_number': chapter_number,
                'title': chapter.title,
                'word_count': word_count,
            })

            self.logger.debug(f"Stored chapter {chapter_number}: {word_count} words")

        # Step 3: Build final manuscript content
        manuscript_parts = []
        for chapter_number, chapter in sorted(story_context.generated_chapters.items()):
            header = f"Chapter {chapter_number}: {chapter.title}"
            manuscript_parts.append(f"\n{'=' * len(header)}\n{header}\n{'=' * len(header)}\n")
            manuscript_parts.append(
                clean_text_for_database(
                    chapter.content,
                    preserve_line_breaks=True,
                )
            )

        final_content = '\n\n'.join(manuscript_parts)
        final_word_count = len(final_content.split())

        # Step 4: Build processing summary
        processing_summary = self._build_processing_summary(
            story_context, quality_assessments, context,
            chapters_stored, total_word_count
        )

        # Step 5: Delete existing final_manuscripts for this draft
        cursor.execute("DELETE FROM final_manuscripts WHERE draft_id = %s", (draft_id,))

        # Step 6: Insert final manuscript
        manuscript_id = str(ULID())
        generated_by = context.get_user_id(self.db_pool)
        cursor.execute("""
            INSERT INTO final_manuscripts (id, draft_id, final_content, word_count,
                                           generated_at, generated_by, processing_summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            manuscript_id, draft_id,
            clean_text_for_database(
                final_content,
                preserve_line_breaks=True,
            ),
            final_word_count,
            datetime.now(),
            generated_by,
            ensure_utf8_json(processing_summary),
        ))

        self.logger.info(
            f"Manuscript assembled: {chapters_stored} chapters, "
            f"{final_word_count} total words"
        )

        # Validate
        if chapters_stored == 0:
            return PipelineStageResult.error_result(
                self.stage_name,
                error="No chapters were stored in the database."
            )

        if final_word_count == 0:
            return PipelineStageResult.error_result(
                self.stage_name,
                error="Final manuscript has zero words."
            )

        return PipelineStageResult.success_result(
            self.stage_name,
            chapters_stored=chapters_stored,
            total_word_count=total_word_count,
            manuscript_word_count=final_word_count,
            manuscript_id=manuscript_id,
            chapter_summaries=chapter_summaries,
        )

    def _build_processing_summary(self, story_context: StoryContext,
                                   quality_assessments: Dict[str, Any],
                                   context: PipelineStageContext,
                                   chapters_stored: int,
                                   total_word_count: int) -> Dict[str, Any]:
        """Build a processing summary for the final manuscript record."""
        # Quality score summary
        quality_summary = {}
        if quality_assessments:
            scores = [
                a.get('overall_score', 0)
                for a in quality_assessments.values()
                if isinstance(a, dict)
            ]
            if scores:
                quality_summary = {
                    'average_score': round(sum(scores) / len(scores), 2),
                    'min_score': round(min(scores), 2),
                    'max_score': round(max(scores), 2),
                    'chapters_assessed': len(scores),
                    'chapters_improved': sum(
                        1 for a in quality_assessments.values()
                        if isinstance(a, dict) and a.get('needs_improvement', False)
                    ),
                }

        # Chapter word counts
        chapter_word_counts = {
            ch_num: ch.word_count
            for ch_num, ch in story_context.generated_chapters.items()
        }

        return {
            'pipeline_version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'chapters_generated': chapters_stored,
            'total_word_count': total_word_count,
            'chapter_word_counts': chapter_word_counts,
            'quality_summary': quality_summary,
            'source_scenes_count': len(story_context.scenes),
            'source_chapters_count': len(story_context.chapters),
            'has_author_style': story_context.author_style is not None,
            'characters_profiled': len(story_context.character_profiles),
            'locations_profiled': len(story_context.location_profiles),
            'config': {
                'target_chapter_length': context.config.get('target_chapter_length', 2500),
                'quality_threshold': context.config.get('quality_threshold', 6.0),
                'max_improvement_passes': context.config.get('max_improvement_passes', 2),
            },
        }
