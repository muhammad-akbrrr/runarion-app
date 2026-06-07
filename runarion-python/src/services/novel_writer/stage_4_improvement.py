"""
Stage 4: Scene Improvement for the novel writer pipeline.
Iteratively improves flagged chapters based on quality assessment feedback.
"""

import logging
from typing import Dict, Any

from .base_stage import BasePipelineStage, PipelineStageContext, PipelineStageResult
from .story_context import StoryContext, GeneratedChapter
from .prompt_template import NovelWriterPrompts
from src.utils.llm_retry import call_llm_with_retry

logger = logging.getLogger(__name__)

REVISION_ACTIONS = {
    'dialogue_depth': "Clarify speaker differentiation, line flow, and dialogue-to-beat balance.",
    'character_descriptions': "Restore missing character cues and sharpen distinctions without padding.",
    'action_pacing': "Correct rushed or muddy action beats while keeping source tempo intact.",
    'location_atmosphere': "Reinstate necessary setting anchors and atmosphere only where the source supports them.",
    'thematic_depth': "Surface the source's existing thematic signals without forcing extra symbolism.",
    'show_dont_tell': "Rebalance exposition and dramatized beats only where the assessment identified drift.",
    'opening_hook': "Adjust the opening to fit chapter function and policy, not a universal dramatic ideal.",
    'ending_impact': "Adjust the ending to fit source momentum and closure level, not a universal dramatic ideal.",
    'author_style': "Improve portable trait transfer while suppressing non-portable markers and clash risks.",
    'scene_coverage': "Restore omitted source beats and scene logic before making any stylistic refinements.",
    'pov_consistency': "Repair narrative person drift and viewpoint leakage immediately.",
    'perspective_continuity': "Stabilize viewpoint handling and remove unjustified head-hopping.",
    'chapter_break_integrity': "Repair chapter edge logic and transition continuity without inventing new structure.",
    'redundancy_control': "Tighten repetitive phrasing and preserve controlled prose density.",
}

REVISION_MODE_INTENTS = {
    'preserve_and_tighten': "Prefer tightening, restoration, and local clarification over expansion.",
    'balanced_rewrite': "Use a balanced mix of preservation, targeted expansion, and tightening.",
    'strong_transfer_with_guardrails': "Allow stronger portable style transfer, but keep revisions targeted and structurally faithful.",
}


class SceneImprovementStage(BasePipelineStage):
    """
    Stage 4: Improve flagged chapters based on quality feedback.

    Reads from:
        context.metadata['story_context'] (generated_chapters + author_style)
        context.metadata['quality_assessments']
    Produces:
        Updated generated_chapters in story_context
    """

    def __init__(self, db_pool, generation_engine):
        super().__init__(db_pool, "SceneImprovementStage", generation_engine)

    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        story_context: StoryContext = context.get('story_context')
        if not story_context:
            return PipelineStageResult.error_result(
                self.stage_name,
                error="StoryContext not found."
            )

        quality_assessments = context.get('quality_assessments')
        if not quality_assessments:
            return PipelineStageResult.error_result(
                self.stage_name,
                error="Quality assessments not found. Stage 3 must complete first."
            )

        max_passes = context.config.get('max_improvement_passes', 2)

        # Filter chapters that need improvement
        chapters_to_improve = {
            ch_num: assessment
            for ch_num, assessment in quality_assessments.items()
            if assessment.get('needs_improvement', False)
        }

        if not chapters_to_improve:
            self.logger.info("No chapters flagged for improvement, skipping stage")
            return PipelineStageResult.success_result(
                self.stage_name,
                chapters_improved=0,
                chapters_skipped=len(quality_assessments),
                improvement_passes=0,
            )

        self.logger.info(
            f"{len(chapters_to_improve)} chapters flagged for improvement "
            f"(max {max_passes} passes each)"
        )

        chapters_improved = 0
        chapters_failed = 0
        total_passes = 0
        improvement_details = []

        for chapter_number, assessment in sorted(chapters_to_improve.items()):
            chapter = story_context.generated_chapters.get(chapter_number)
            if not chapter:
                self.logger.warning(f"Chapter {chapter_number} not found in generated chapters")
                chapters_failed += 1
                continue

            original_score = assessment.get('overall_score', 0)
            self.logger.info(
                f"Improving chapter {chapter_number} (score: {original_score:.1f})"
            )

            improved = False
            current_content = chapter.content
            current_score = original_score
            passes_used = 0

            for pass_num in range(max_passes):
                passes_used += 1
                total_passes += 1

                try:
                    improved_content = self._improve_chapter(
                        story_context, current_content,
                        assessment, chapter_number
                    )

                    if not improved_content:
                        self.logger.warning(
                            f"Improvement pass {pass_num + 1} failed for chapter {chapter_number}"
                        )
                        break

                    # Lightweight re-assessment (check overall score)
                    new_score = self._quick_score_check(
                        improved_content, story_context
                    )

                    self.logger.info(
                        f"Chapter {chapter_number} pass {pass_num + 1}: "
                        f"{current_score:.1f} -> {new_score:.1f}"
                    )

                    if new_score > current_score:
                        current_content = improved_content
                        current_score = new_score
                        improved = True
                    else:
                        self.logger.info(
                            f"Score did not improve for chapter {chapter_number} "
                            f"on pass {pass_num + 1}, keeping previous version"
                        )
                        break

                except Exception as e:
                    self.logger.error(
                        f"Improvement error for chapter {chapter_number} "
                        f"pass {pass_num + 1}: {e}"
                    )
                    break

            if improved:
                # Update the generated chapter with improved content
                word_count = len(current_content.split())
                story_context.generated_chapters[chapter_number] = GeneratedChapter(
                    chapter_number=chapter_number,
                    title=chapter.title,
                    content=current_content,
                    word_count=word_count,
                    summary=chapter.summary,
                    source_scenes=chapter.source_scenes,
                )
                chapters_improved += 1

                improvement_details.append({
                    'chapter': chapter_number,
                    'original_score': original_score,
                    'final_score': current_score,
                    'passes_used': passes_used,
                    'improved': True,
                })
            else:
                chapters_failed += 1
                improvement_details.append({
                    'chapter': chapter_number,
                    'original_score': original_score,
                    'final_score': current_score,
                    'passes_used': passes_used,
                    'improved': False,
                })

        return PipelineStageResult.success_result(
            self.stage_name,
            chapters_improved=chapters_improved,
            chapters_failed=chapters_failed,
            total_passes=total_passes,
            improvement_details=improvement_details,
        )

    def _improve_chapter(self, story_context: StoryContext,
                         chapter_content: str, assessment: Dict[str, Any],
                         chapter_number: int) -> str:
        """Generate an improved version of a chapter."""

        # Build quality feedback text
        weak_dimensions = assessment.get('weak_dimensions', [])
        feedback = assessment.get('feedback', {})

        quality_feedback_parts = []
        for wd in weak_dimensions:
            dim = wd.get('dimension', '')
            score = wd.get('score', 0)
            fb = feedback.get(dim, wd.get('feedback', ''))
            quality_feedback_parts.append(f"- {dim} (score: {score}/10): {fb}")

        quality_feedback = '\n'.join(quality_feedback_parts) if quality_feedback_parts else 'General improvement needed.'

        # Build weak dimensions summary
        weak_dims_text = ', '.join(
            f"{wd['dimension']} ({wd['score']}/10)" for wd in weak_dimensions
        ) if weak_dimensions else 'No specific weak dimensions identified.'

        # Build revision guidance keyed off the compiled policy mode
        compiled_policy = getattr(story_context, 'compiled_rewrite_policy', None)
        mode_name = getattr(compiled_policy, 'improvement_mode', 'balanced_rewrite')
        mode_intent = REVISION_MODE_INTENTS.get(
            mode_name,
            REVISION_MODE_INTENTS['balanced_rewrite'],
        )

        expansion_parts = [f"- Mode intent: {mode_intent}"]
        for wd in weak_dimensions:
            dim = wd.get('dimension', '')
            action = REVISION_ACTIONS.get(
                dim,
                "Make the smallest revision that fully resolves the reported issue.",
            )
            expansion_parts.append(f"- {dim}: {action}")
        expansion_guidance = '\n'.join(expansion_parts) if expansion_parts else 'Focus on overall quality improvement.'

        # Get author style examples for weak areas
        style_example_parts = []
        weak_categories = set()
        for wd in weak_dimensions:
            dim = wd.get('dimension', '')
            # Map dimensions to style categories
            category_map = {
                'dialogue_depth': 'dialogue',
                'character_descriptions': 'description',
                'action_pacing': 'pacing',
                'location_atmosphere': 'description',
                'thematic_depth': 'voice',
                'show_dont_tell': 'exposition',
                'author_style': 'voice',
                'pov_consistency': 'voice',
                'perspective_continuity': 'voice',
                'chapter_break_integrity': 'pacing',
                'redundancy_control': 'voice',
            }
            cat = category_map.get(dim)
            if cat and cat not in weak_categories:
                weak_categories.add(cat)
                examples = NovelWriterPrompts.get_author_style_examples(
                    story_context.author_style, cat, max_examples=2
                )
                if 'No' not in examples[:10]:
                    style_example_parts.append(examples)

        author_style_examples = '\n\n'.join(style_example_parts) if style_example_parts else \
            'No specific author style examples available for weak areas.'

        # Build the improvement prompt
        prompt_template = NovelWriterPrompts.get_improvement_prompt()
        writing_perspective_instruction = NovelWriterPrompts.get_writing_perspective_instruction(
            getattr(story_context, 'writing_perspective', 'third_person_limited')
        )
        prompt = prompt_template.format(
            chapter_content=chapter_content,
            rewrite_policy_guidance=compiled_policy.improvement_guidance if compiled_policy else (
                "Repair only identified structural and stylistic issues."
            ),
            negative_constraints=compiled_policy.negative_constraints_block if compiled_policy else (
                "No explicit negative style constraints."
            ),
            quality_feedback=quality_feedback,
            weak_dimensions=weak_dims_text,
            expansion_guidance=expansion_guidance,
            revision_mode_guidance=compiled_policy.improvement_mode_guidance if compiled_policy else (
                "Use BALANCED_REWRITE mode. Keep revisions targeted and structurally faithful."
            ),
            author_style_examples=author_style_examples,
            writing_perspective_instruction=writing_perspective_instruction,
        )

        # Estimate tokens needed (chapter content + expansion)
        current_words = len(chapter_content.split())
        max_output_tokens = max(current_words * 2, 6000)

        try:
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = (
                "Revise the chapter to satisfy the compiled rewrite policy and the listed quality issues. "
                "Return the complete improved chapter."
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
                    f"Improvement truncated. Increasing tokens to {new_limit}"
                )
                self.generation_engine.request.generation_config.max_output_tokens = new_limit
                response = call_llm_with_retry(
                    lambda: self.generation_engine.generate(skip_quota=True)
                )

            if response.success:
                improved = response.text.strip()
                # Validate the improvement isn't drastically shorter
                improved_words = len(improved.split())
                if improved_words < current_words * 0.7:
                    self.logger.warning(
                        f"Improved version too short ({improved_words} vs {current_words} words), "
                        f"rejecting improvement"
                    )
                    return ""
                return improved
            else:
                error_msg = getattr(response, 'error_message', 'Unknown error')
                self.logger.warning(f"Improvement generation failed: {error_msg}")
                return ""

        except Exception as e:
            self.logger.error(f"Improvement generation exception: {e}")
            return ""

    def _quick_score_check(self, chapter_content: str,
                           story_context: StoryContext) -> float:
        """Do a lightweight overall quality score check."""
        try:
            compiled_policy = getattr(story_context, 'compiled_rewrite_policy', None)
            prompt = (
                "Rate how well this chapter satisfies the rewrite policy on a scale of 1-10. "
                "Consider structural fidelity, policy alignment, negative-constraint compliance, "
                "perspective stability, and controlled prose.\n\n"
                f"REWRITE POLICY:\n{compiled_policy.assessment_guidance if compiled_policy else 'Preserve structure and explicit constraints.'}\n\n"
                f"CHAPTER:\n{chapter_content[:8000]}\n\n"
                "Return ONLY a single number (1-10):"
            )

            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = (
                "Return only a single number between 1 and 10."
            )
            self.generation_engine.request.generation_config.max_output_tokens = 50

            response = call_llm_with_retry(
                lambda: self.generation_engine.generate(skip_quota=True)
            )

            if response.success:
                text = response.text.strip()
                # Extract number from response
                for token in text.split():
                    try:
                        score = float(token.replace(',', '').replace('.', '', token.count('.') - 1))
                        if 1 <= score <= 10:
                            return score
                    except ValueError:
                        continue

            # Default to moderate score on failure
            return 5.0

        except Exception as e:
            self.logger.warning(f"Quick score check failed: {e}")
            return 5.0
