"""
Stage 3: Quality Assessment for the novel writer pipeline.
Evaluates each generated chapter against quality dimensions using LLM scoring.
"""

import json
import logging
import re
from typing import Dict, Any, List

from .base_stage import BasePipelineStage, PipelineStageContext, PipelineStageResult
from .story_context import StoryContext
from .prompt_template import NovelWriterPrompts
from src.utils.llm_retry import call_llm_with_retry

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
    'pov_consistency': 1.5,
    'perspective_continuity': 1.4,
    'chapter_break_integrity': 1.2,
    'redundancy_control': 1.0,
}

ALL_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())

FIRST_PERSON_PRONOUNS = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves"}
SECOND_PERSON_PRONOUNS = {"you", "your", "yours", "yourself", "yourselves"}
THIRD_PERSON_PRONOUNS = {
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "they", "them", "their", "theirs", "themselves",
}

HARD_DIMENSIONS = (
    'scene_coverage',
    'pov_consistency',
    'perspective_continuity',
    'chapter_break_integrity',
    'redundancy_control',
)


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
        llm_assessment_failures = 0
        fallback_improvement_defaults = 0
        deterministic_downgrades = {
            'scene_coverage': 0,
            'pov_consistency': 0,
            'perspective_continuity': 0,
            'chapter_break_integrity': 0,
            'redundancy_control': 0,
        }
        hard_dimension_failures = []

        for chapter_number, chapter in sorted(story_context.generated_chapters.items()):
            self.logger.info(
                f"Assessing chapter {chapter_number}: {chapter.title}"
            )

            try:
                assessment = self._assess_chapter(
                    story_context, chapter, chapter_number
                )

                if assessment:
                    deterministic_checks = self._run_deterministic_checks(
                        story_context,
                        chapter_number,
                        chapter.content,
                        getattr(story_context, 'writing_perspective', 'third_person_limited')
                    )
                    blend_report = self._blend_deterministic_scores(assessment, deterministic_checks)

                    for dim in blend_report.get('downgraded_dimensions', []):
                        if dim in deterministic_downgrades:
                            deterministic_downgrades[dim] += 1

                    overall_score = assessment.get('overall_score', 0)
                    needs_improvement = overall_score < quality_threshold

                    assessment['needs_improvement'] = needs_improvement
                    assessment['chapter_number'] = chapter_number
                    assessment['chapter_title'] = chapter.title
                    assessment['deterministic_checks'] = deterministic_checks
                    assessment['deterministic_blend'] = blend_report

                    failed_hard_dimensions = [
                        dim for dim in HARD_DIMENSIONS
                        if float((assessment.get('scores') or {}).get(dim, 0.0)) < quality_threshold
                    ]
                    if failed_hard_dimensions:
                        hard_dimension_failures.append({
                            'chapter': chapter_number,
                            'failed_dimensions': failed_hard_dimensions,
                        })

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
                    llm_assessment_failures += 1
                    fallback_improvement_defaults += 1
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
                llm_assessment_failures += 1
                fallback_improvement_defaults += 1

        # Store assessments in context for Stage 4
        context.set('quality_assessments', assessments)

        avg_score = total_score / max(chapters_assessed, 1)
        deterministic_summary = self._summarize_deterministic_checks(assessments)
        degradation_report = {
            'llm_assessment_failures': llm_assessment_failures,
            'fallback_improvement_defaults': fallback_improvement_defaults,
            'deterministic_downgrades': deterministic_downgrades,
        }
        deterministic_gate_outcomes = {
            'threshold': float(quality_threshold),
            'hard_dimensions': list(HARD_DIMENSIONS),
            'chapters_failing': hard_dimension_failures,
            'chapters_failing_count': len(hard_dimension_failures),
            'chapters_passing_count': max(chapters_assessed - len(hard_dimension_failures), 0),
        }
        quality_diagnostics = {
            'degradation_report': degradation_report,
            'deterministic_gate_outcomes': deterministic_gate_outcomes,
            'deterministic_summary': deterministic_summary,
        }
        context.set('quality_diagnostics', quality_diagnostics)

        return PipelineStageResult.success_result(
            self.stage_name,
            chapters_assessed=chapters_assessed,
            chapters_needing_improvement=chapters_needing_improvement,
            average_score=round(avg_score, 2),
            quality_threshold=quality_threshold,
            degradation_report=degradation_report,
            deterministic_gate_outcomes=deterministic_gate_outcomes,
            deterministic_summary=deterministic_summary,
        )

    def _assess_chapter(self, story_context: StoryContext,
                        chapter, chapter_number: int) -> Dict[str, Any]:
        """Assess a single chapter's quality using LLM."""

        # Build author style reference
        compiled_policy = getattr(story_context, 'compiled_rewrite_policy', None)
        author_style_reference = NovelWriterPrompts.get_author_style_instruction(
            story_context.author_style,
            compiled_policy,
        )
        writing_perspective_instruction = NovelWriterPrompts.get_writing_perspective_instruction(
            getattr(story_context, 'writing_perspective', 'third_person_limited')
        )

        # Build scene coverage checklist
        scene_coverage = self._build_scene_checklist(story_context, chapter)

        # Build the assessment prompt
        prompt_template = NovelWriterPrompts.get_quality_assessment_prompt()
        prompt = prompt_template.format(
            chapter_content=chapter.content[:12000],  # Truncate very long chapters
            rewrite_policy_guidance=compiled_policy.assessment_guidance if compiled_policy else (
                "Assess against explicit structural constraints and any provided rewrite policy."
            ),
            negative_constraints=compiled_policy.negative_constraints_block if compiled_policy else (
                "No explicit negative style constraints."
            ),
            author_style_reference=author_style_reference,
            writing_perspective_instruction=writing_perspective_instruction,
            scene_coverage_checklist=scene_coverage,
        )

        try:
            self.generation_engine.request.prompt = prompt
            self.generation_engine.request.instruction = (
                "You are a policy-aware chapter assessor. "
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
        scores = assessment.get('scores', {}) or {}
        feedback = assessment.get('feedback', {}) or {}

        # Ensure all expected dimensions exist to keep downstream gating deterministic.
        for dim in ALL_DIMENSIONS:
            val = scores.get(dim, 5)
            if not isinstance(val, (int, float)):
                val = 5
            scores[dim] = float(val)
            feedback.setdefault(dim, "")

        assessment['scores'] = scores
        assessment['feedback'] = feedback

        # Compute weighted overall score if not provided or seems off
        if scores:
            weighted_sum = 0.0
            weight_sum = 0.0
            for dim, weight in DIMENSION_WEIGHTS.items():
                score = float(scores.get(dim, 5))
                weighted_sum += score * weight
                weight_sum += weight

            if weight_sum > 0:
                computed_overall = weighted_sum / weight_sum
                assessment['overall_score'] = round(computed_overall, 2)

        # Identify weak dimensions
        weak_dimensions = []
        for dim in ALL_DIMENSIONS:
            score = float(scores.get(dim, 5))
            if score < 6:
                weak_dimensions.append({
                    'dimension': dim,
                    'score': score,
                    'feedback': feedback.get(dim, ''),
                })

        assessment['weak_dimensions'] = weak_dimensions

        return assessment

    def _blend_deterministic_scores(
        self,
        assessment: Dict[str, Any],
        checks: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Blend deterministic checks into LLM scores conservatively.

        Uses min(llm_score, deterministic_score) for dimensions we can measure
        deterministically to avoid false positives from optimistic LLM scoring.
        """
        scores = assessment.get('scores', {}) or {}
        feedback = assessment.get('feedback', {}) or {}
        downgraded_dimensions = []

        for dim, det_score in checks.items():
            if dim not in scores:
                continue
            llm_score = float(scores.get(dim, 5))
            blended = min(llm_score, float(det_score))
            if blended < llm_score:
                fb = feedback.get(dim, "")
                det_note = f"[deterministic_check={det_score:.1f}]"
                feedback[dim] = f"{fb} {det_note}".strip()
                downgraded_dimensions.append(dim)
            scores[dim] = blended

        # Recompute overall score after blending.
        weighted_sum = 0.0
        weight_sum = 0.0
        for dim, weight in DIMENSION_WEIGHTS.items():
            score = float(scores.get(dim, 5))
            weighted_sum += score * weight
            weight_sum += weight
        if weight_sum > 0:
            assessment['overall_score'] = round(weighted_sum / weight_sum, 2)

        assessment['scores'] = scores
        assessment['feedback'] = feedback
        return {
            'downgraded_dimensions': downgraded_dimensions,
            'downgrade_count': len(downgraded_dimensions),
        }

    def _run_deterministic_checks(
        self,
        story_context: StoryContext,
        chapter_number: int,
        chapter_content: str,
        writing_perspective: str,
    ) -> Dict[str, float]:
        """
        Run deterministic quality checks to reduce LLM-only scoring noise.
        """
        tokens = re.findall(r"[a-zA-Z']+", chapter_content.lower())
        first_count = sum(1 for t in tokens if t in FIRST_PERSON_PRONOUNS)
        second_count = sum(1 for t in tokens if t in SECOND_PERSON_PRONOUNS)
        third_count = sum(1 for t in tokens if t in THIRD_PERSON_PRONOUNS)
        pronoun_total = first_count + second_count + third_count

        if writing_perspective == 'first_person':
            expected = first_count
            non_expected = second_count + third_count
        elif writing_perspective == 'second_person':
            expected = second_count
            non_expected = first_count + third_count
        else:
            # third_person_limited + third_person_omniscient both expect third-person pronouns
            expected = third_count
            non_expected = first_count + second_count

        if pronoun_total >= 20:
            expected_ratio = expected / max(pronoun_total, 1)
            non_expected_ratio = non_expected / max(pronoun_total, 1)
            pov_consistency = 10.0 - max(0.0, (0.55 - expected_ratio) * 18.0) - (non_expected_ratio * 6.0)
        else:
            # Low pronoun signal; neutral but not perfect.
            pov_consistency = 6.5

        # Perspective continuity by paragraph-level dominant pronoun class.
        perspective_shifts = 0
        dominant_sequence = []
        paragraphs = [p for p in re.split(r"\n\s*\n", chapter_content) if p.strip()]
        for p in paragraphs:
            ptoks = re.findall(r"[a-zA-Z']+", p.lower())
            f = sum(1 for t in ptoks if t in FIRST_PERSON_PRONOUNS)
            s = sum(1 for t in ptoks if t in SECOND_PERSON_PRONOUNS)
            th = sum(1 for t in ptoks if t in THIRD_PERSON_PRONOUNS)
            if f == s == th == 0:
                continue
            dominant = max(
                [('first', f), ('second', s), ('third', th)],
                key=lambda x: x[1],
            )[0]
            dominant_sequence.append(dominant)

        for i in range(1, len(dominant_sequence)):
            if dominant_sequence[i] != dominant_sequence[i - 1]:
                perspective_shifts += 1

        if len(dominant_sequence) <= 1:
            perspective_continuity = 8.0
        else:
            perspective_continuity = 10.0 - (perspective_shifts * 2.2)

        # Redundancy heuristic: repeated trigrams + very low lexical diversity.
        words = [w.lower() for w in re.findall(r"[a-zA-Z']+", chapter_content)]
        total_words = len(words)
        unique_words = len(set(words))
        lexical_diversity = (unique_words / total_words) if total_words else 1.0

        trigrams = {}
        for i in range(max(0, total_words - 2)):
            tri = (words[i], words[i + 1], words[i + 2])
            trigrams[tri] = trigrams.get(tri, 0) + 1
        repeated_trigrams = sum(1 for count in trigrams.values() if count > 1)

        adjacent_duplicates = 0
        for i in range(1, total_words):
            if words[i] == words[i - 1]:
                adjacent_duplicates += 1

        redundancy_control = 10.0
        if lexical_diversity < 0.22:
            redundancy_control -= 2.0
        if repeated_trigrams > 6:
            redundancy_control -= min(4.0, (repeated_trigrams - 6) * 0.4)
        if adjacent_duplicates > 2:
            redundancy_control -= 1.0

        chapter_break_integrity = self._estimate_chapter_break_integrity(
            story_context,
            chapter_number,
            chapter_content,
        )
        scene_coverage = self._estimate_scene_coverage(
            story_context,
            chapter_number,
            chapter_content,
        )

        def _clamp(score: float) -> float:
            return max(1.0, min(10.0, round(score, 2)))

        return {
            'scene_coverage': _clamp(scene_coverage),
            'pov_consistency': _clamp(pov_consistency),
            'perspective_continuity': _clamp(perspective_continuity),
            'chapter_break_integrity': _clamp(chapter_break_integrity),
            'redundancy_control': _clamp(redundancy_control),
        }

    def _estimate_scene_coverage(
        self,
        story_context: StoryContext,
        chapter_number: int,
        chapter_content: str,
    ) -> float:
        """
        Estimate whether the generated chapter still covers all source scenes.

        This is intentionally conservative and uses broad anchor matching so it
        catches likely omissions without forcing a brittle lexical copy.
        """
        chapter = story_context.generated_chapters.get(chapter_number)
        if not chapter or not chapter.source_scenes:
            return 6.5

        chapter_tokens = set(re.findall(r"[a-zA-Z']+", chapter_content.lower()))
        covered = 0

        for scene_num in chapter.source_scenes:
            scene = next(
                (s for s in story_context.scenes if s.get('scene_number') == scene_num),
                None,
            )
            if not scene:
                continue

            character_terms = self._scene_character_terms(scene)
            anchor_terms = self._scene_anchor_terms(scene)

            character_hits = sum(1 for term in character_terms if term in chapter_tokens)
            anchor_hits = sum(1 for term in anchor_terms if term in chapter_tokens)
            min_anchor_hits = 1 if len(anchor_terms) <= 3 else 2

            if character_hits >= 1 and anchor_hits >= 1:
                covered += 1
            elif anchor_hits >= min_anchor_hits:
                covered += 1

        total = max(len(chapter.source_scenes), 1)
        coverage_ratio = covered / total
        return 1.0 + (coverage_ratio * 9.0)

    def _scene_character_terms(self, scene: Dict[str, Any]) -> List[str]:
        characters = scene.get('characters', [])
        if isinstance(characters, str):
            characters = [characters]

        terms = set()
        for character in characters or []:
            for part in re.findall(r"[a-zA-Z']+", str(character).lower()):
                if len(part) >= 3:
                    terms.add(part)
        return sorted(terms)

    def _scene_anchor_terms(self, scene: Dict[str, Any]) -> List[str]:
        stopwords = {
            'the', 'and', 'for', 'with', 'that', 'this', 'from', 'into', 'onto',
            'about', 'while', 'when', 'where', 'there', 'their', 'then', 'them',
            'have', 'has', 'had', 'were', 'was', 'are', 'his', 'her', 'hers',
            'your', 'yours', 'our', 'ours', 'they', 'she', 'him', 'you', 'not',
            'but', 'out', 'over', 'under', 'after', 'before', 'through',
            'scene', 'chapter', 'unknown', 'location',
        }
        fields = [
            scene.get('title', ''),
            scene.get('summary', ''),
            scene.get('setting', ''),
        ]
        terms = []
        for value in fields:
            for token in re.findall(r"[a-zA-Z']+", str(value).lower()):
                if len(token) < 4 or token in stopwords:
                    continue
                terms.append(token)

        # Preserve stable order while deduplicating and cap the anchor set.
        deduped = []
        seen = set()
        for token in terms:
            if token in seen:
                continue
            seen.add(token)
            deduped.append(token)
        return deduped[:12]

    def _estimate_chapter_break_integrity(
        self,
        story_context: StoryContext,
        chapter_number: int,
        chapter_content: str,
    ) -> float:
        """
        Heuristic chapter-boundary integrity check based on chapter edges.
        """
        score = 9.0
        stripped = chapter_content.strip()
        if not stripped:
            return 1.0

        if not re.search(r"[.!?][\"')\\]]?\s*$", stripped):
            score -= 1.8

        if re.search(r"\b(and|or|but|because|while|as|then|so)\s*$", stripped.lower()):
            score -= 1.4

        tail_words = self._edge_words(stripped, take_last=True, window=40)
        current_tail = " ".join(tail_words)

        next_chapter = story_context.generated_chapters.get(chapter_number + 1)
        if next_chapter and next_chapter.content:
            next_text = next_chapter.content.strip()
            if next_text and next_text[0].islower():
                score -= 0.8

            head_words = self._edge_words(next_text, take_last=False, window=40)
            overlap_ratio = self._edge_overlap_ratio(tail_words, head_words)
            if overlap_ratio >= 0.55:
                score -= 1.6

            if (
                self._is_action_dense(current_tail)
                and self._is_action_dense(" ".join(head_words))
                and not self._has_transition_cue(next_text[:160])
            ):
                score -= 1.4

        prev_chapter = story_context.generated_chapters.get(chapter_number - 1)
        if prev_chapter and prev_chapter.content:
            prev_tail = prev_chapter.content.strip()[-140:]
            if prev_tail and prev_tail[-1] not in ".!?\"'":
                score -= 0.5

        return score

    def _edge_words(self, text: str, take_last: bool, window: int = 40) -> List[str]:
        words = re.findall(r"[a-zA-Z']+", text.lower())
        if not words:
            return []
        if take_last:
            return words[-window:]
        return words[:window]

    def _edge_overlap_ratio(self, left_words: List[str], right_words: List[str]) -> float:
        left_set = set(left_words)
        right_set = set(right_words)
        union = left_set | right_set
        if not union:
            return 0.0
        return len(left_set & right_set) / len(union)

    def _is_action_dense(self, text: str) -> bool:
        action_words = {
            'fight', 'battle', 'attack', 'shoot', 'gun', 'gunfire', 'run', 'chase',
            'escape', 'strike', 'kill', 'blood', 'panic', 'explode', 'explosion',
            'crash', 'ambush', 'pursuit', 'confrontation',
        }
        words = re.findall(r"[a-zA-Z']+", text.lower())
        if not words:
            return False
        hits = sum(1 for w in words if w in action_words)
        return (hits / max(len(words), 1)) >= 0.05 or hits >= 3

    def _has_transition_cue(self, text: str) -> bool:
        cue_patterns = [
            r"\blater\b",
            r"\bhours later\b",
            r"\bdays later\b",
            r"\bmeanwhile\b",
            r"\bafterward\b",
            r"\bthe next\b",
            r"\bat dawn\b",
            r"\bby morning\b",
            r"\bback in\b",
        ]
        lowered = text.lower()
        return any(re.search(pattern, lowered) for pattern in cue_patterns)

    def _summarize_deterministic_checks(
        self,
        assessments: Dict[int, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Summarize deterministic check outcomes across assessed chapters."""
        per_dimension_values = {
            'scene_coverage': [],
            'pov_consistency': [],
            'perspective_continuity': [],
            'chapter_break_integrity': [],
            'redundancy_control': [],
        }

        for assessment in assessments.values():
            checks = assessment.get('deterministic_checks', {}) or {}
            for dim in per_dimension_values:
                value = checks.get(dim)
                if isinstance(value, (int, float)):
                    per_dimension_values[dim].append(float(value))

        summary = {}
        for dim, values in per_dimension_values.items():
            if not values:
                summary[dim] = {'avg': 0.0, 'min': 0.0, 'max': 0.0, 'count': 0}
                continue
            summary[dim] = {
                'avg': round(sum(values) / len(values), 2),
                'min': round(min(values), 2),
                'max': round(max(values), 2),
                'count': len(values),
            }

        return summary

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
