"""
Stage 3: Quality Assessment for the novel writer pipeline.
Evaluates each generated chapter against 10 quality dimensions using LLM scoring.
"""

import json
import logging
from typing import Dict, Any, List

from .base_stage import BasePipelineStage, PipelineStageContext, PipelineStageResult
from .story_context import StoryContext
from .prompt_template import NovelWriterPrompts
from utils.llm_retry import call_llm_with_retry

logger = logging.getLogger(__name__)

# Quality dimension weights for overall score calculation
DIMENSION_WEIGHTS = {
    'opening_hook': 1.0,
    'ending_impact': 1.0,
    'character_descriptions': 1.2,
    'location_atmosphere': 1.0,
    'dialogue_depth': 1.2,
    'action_pacing': 1.0,
    'thematic_depth': 0.8,
    'show_dont_tell': 1.2,
    'author_style': 1.0,
    'scene_coverage': 1.5,
}

ALL_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())


class QualityAssessmentStage(BasePipelineStage):
    """
    Stage 3: Assess the quality of each generated chapter.

    Reads from: context.metadata['story_context'] (generated_chapters + author_style)
    Produces: context.metadata['quality_assessments']
    """

    def __init__(self, db_pool, generation_engine):
        super().__init__(db_pool, "QualityAssessmentStage", generation_engine)

    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        story_context: StoryContext = context.get('story_context')
        if not story_context:
            return PipelineStageResult.error_result(
                self.stage_name,
                error="StoryContext not found. Stage 1 must complete first."
            )

        if not story_context.generated_chapters:
            return PipelineStageResult.error_result(
                self.stage_name,
                error="No generated chapters found. Stage 2 must complete first."
            )

        quality_threshold = context.config.get('quality_threshold', 6.0)
        assessments = {}
        chapters_assessed = 0
        chapters_needing_improvement = 0
        total_score = 0.0

        for chapter_number, chapter in sorted(story_context.generated_chapters.items()):
            self.logger.info(
                f"Assessing chapter {chapter_number}: {chapter.title}"
            )

            try:
                assessment = self._assess_chapter(
                    story_context, chapter, chapter_number
                )

                if assessment:
                    overall_score = assessment.get('overall_score', 0)
                    needs_improvement = overall_score < quality_threshold

                    assessment['needs_improvement'] = needs_improvement
                    assessment['chapter_number'] = chapter_number
                    assessment['chapter_title'] = chapter.title

                    assessments[chapter_number] = assessment
                    chapters_assessed += 1
                    total_score += overall_score

                    if needs_improvement:
                        chapters_needing_improvement += 1

                    self.logger.info(
                        f"Chapter {chapter_number} score: {overall_score:.1f} "
                        f"({'needs improvement' if needs_improvement else 'passed'})"
                    )
                else:
                    # Assessment failed - flag for improvement by default
                    assessments[chapter_number] = {
                        'chapter_number': chapter_number,
                        'chapter_title': chapter.title,
                        'needs_improvement': True,
                        'overall_score': 0,
                        'scores': {},
                        'feedback': {},
                        'top_issues': ['Assessment failed - defaulting to improvement required'],
                        'assessment_error': True,
                    }
                    chapters_assessed += 1
                    chapters_needing_improvement += 1
                    self.logger.warning(
                        f"Assessment failed for chapter {chapter_number}, flagged for improvement"
                    )

            except Exception as e:
                self.logger.error(f"Error assessing chapter {chapter_number}: {e}")
                assessments[chapter_number] = {
                    'chapter_number': chapter_number,
                    'chapter_title': chapter.title,
                    'needs_improvement': True,
                    'overall_score': 0,
                    'scores': {},
                    'feedback': {},
                    'top_issues': [f'Assessment error: {str(e)}'],
                    'assessment_error': True,
                }
                chapters_assessed += 1
                chapters_needing_improvement += 1

        # Store assessments in context for Stage 4
        context.set('quality_assessments', assessments)

        avg_score = total_score / max(chapters_assessed, 1)

        return PipelineStageResult.success_result(
            self.stage_name,
            chapters_assessed=chapters_assessed,
            chapters_needing_improvement=chapters_needing_improvement,
            average_score=round(avg_score, 2),
            quality_threshold=quality_threshold,
        )

    def _assess_chapter(self, story_context: StoryContext,
                        chapter, chapter_number: int) -> Dict[str, Any]:
        """Assess a single chapter's quality using LLM."""

        # Build author style reference
        author_style_reference = NovelWriterPrompts.get_author_style_instruction(
            story_context.author_style
        )

        # Build scene coverage checklist
        scene_coverage = self._build_scene_checklist(story_context, chapter)

        # Build the assessment prompt
        prompt_template = NovelWriterPrompts.get_quality_assessment_prompt()
        prompt = prompt_template.format(
            chapter_content=chapter.content[:12000],  # Truncate very long chapters
            author_style_reference=author_style_reference,
            scene_coverage_checklist=scene_coverage,
        )

        try:
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = (
                "You are a ruthlessly thorough literary quality assessor. "
                "Return ONLY valid JSON with no markdown formatting."
            )
            self.generation_engine.request.generation_config.max_output_tokens = 2000

            response = call_llm_with_retry(
                lambda: self.generation_engine.generate(skip_quota=True)
            )

            if not response.success:
                error_msg = getattr(response, 'error_message', 'Unknown error')
                self.logger.warning(f"Quality assessment LLM call failed: {error_msg}")
                return None

            # Parse the JSON response
            return self._parse_assessment_response(response.text)

        except Exception as e:
            self.logger.error(f"Quality assessment exception for chapter {chapter_number}: {e}")
            return None

    def _parse_assessment_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the LLM's quality assessment JSON response."""
        text = response_text.strip()

        # Strip markdown code fences if present
        if text.startswith('```'):
            lines = text.split('\n')
            # Remove first and last lines (fences)
            lines = [l for l in lines if not l.strip().startswith('```')]
            text = '\n'.join(lines)

        try:
            assessment = json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                try:
                    assessment = json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    self.logger.warning("Could not parse quality assessment JSON")
                    return None
            else:
                self.logger.warning("No JSON found in quality assessment response")
                return None

        # Validate expected structure
        scores = assessment.get('scores', {})
        feedback = assessment.get('feedback', {})

        # Compute weighted overall score if not provided or seems off
        if scores:
            weighted_sum = 0.0
            weight_sum = 0.0
            for dim, weight in DIMENSION_WEIGHTS.items():
                score = scores.get(dim, 5)
                if isinstance(score, (int, float)):
                    weighted_sum += score * weight
                    weight_sum += weight

            if weight_sum > 0:
                computed_overall = weighted_sum / weight_sum
                assessment['overall_score'] = round(computed_overall, 2)

        # Identify weak dimensions
        weak_dimensions = []
        for dim in ALL_DIMENSIONS:
            score = scores.get(dim, 5)
            if isinstance(score, (int, float)) and score < 6:
                weak_dimensions.append({
                    'dimension': dim,
                    'score': score,
                    'feedback': feedback.get(dim, ''),
                })

        assessment['weak_dimensions'] = weak_dimensions

        return assessment

    def _build_scene_checklist(self, story_context: StoryContext,
                               chapter) -> str:
        """Build a checklist of scenes that should be covered in the chapter."""
        parts = []
        for scene_num in chapter.source_scenes:
            scene = next(
                (s for s in story_context.scenes if s.get('scene_number') == scene_num),
                None
            )
            if scene:
                title = scene.get('title', f'Scene {scene_num}')
                summary = scene.get('summary', '')[:150]
                parts.append(f"- Scene {scene_num} ({title}): {summary}")
            else:
                parts.append(f"- Scene {scene_num}: [scene data not found]")

        return '\n'.join(parts) if parts else "No specific scene coverage checklist available."
