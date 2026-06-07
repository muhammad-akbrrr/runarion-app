"""
Unit tests for the novel writer service layer.
Tests pure logic with no database or LLM dependencies:
- StoryContext data structures and methods
- Prompt template generation
- Quality assessment scoring and parsing
- Status model validation
- Entity profiler merging logic
"""

import sys
import json
import logging

import pytest


from src.services.novel_writer.story_context import (
    StoryContext, CharacterProfile, LocationProfile, GeneratedChapter
)
from src.services.novel_writer.prompt_template import NovelWriterPrompts
from src.services.novel_writer.stage_3_quality import (
    DIMENSION_WEIGHTS, ALL_DIMENSIONS, QualityAssessmentStage
)
from src.services.novel_writer.stage_4_improvement import REVISION_ACTIONS
from src.services.novel_writer.base_stage import (
    PipelineStageContext, PipelineStageResult
)
from src.models.novel_writer.status import NovelWriterStatus
from src.models.deconstructor.status import DraftStatus


@pytest.fixture(autouse=True)
def _silence_expected_test_logs(set_logger_level):
    set_logger_level("test", logging.ERROR)


# ─── StoryContext Tests ────────────────────────────────────────────────────────

def test_story_context_initialization():
    """Test StoryContext initializes with empty collections."""
    ctx = StoryContext()

    assert ctx.scenes == []
    assert ctx.chapters == []
    assert ctx.character_profiles == {}
    assert ctx.location_profiles == {}
    assert ctx.relationships == []
    assert ctx.themes == []
    assert ctx.plot_threads == []
    assert ctx.narrative_overview == {}
    assert ctx.plot_issues == []
    assert ctx.author_style is None
    assert ctx.generated_chapters == {}

    print("  StoryContext initialization: OK")


def test_story_context_get_chapter_context_empty():
    """Test get_chapter_context returns empty dict when no chapters loaded."""
    ctx = StoryContext()

    result = ctx.get_chapter_context(1)
    assert result == {}

    print("  get_chapter_context (empty): OK")


def test_story_context_get_chapter_context_out_of_range():
    """Test get_chapter_context returns empty dict for invalid chapter number."""
    ctx = StoryContext()
    ctx.chapters = [{'chapter_number': 1, 'start_scene': 1, 'end_scene': 2}]

    assert ctx.get_chapter_context(0) == {}
    assert ctx.get_chapter_context(5) == {}

    print("  get_chapter_context (out of range): OK")


def test_story_context_get_chapter_context_full():
    """Test get_chapter_context returns complete context for a valid chapter."""
    ctx = StoryContext()

    # Set up scenes
    ctx.scenes = [
        {'scene_number': 1, 'title': 'Opening', 'characters': ['Alice', 'Bob'], 'setting': 'Castle'},
        {'scene_number': 2, 'title': 'Confrontation', 'characters': ['Alice'], 'setting': 'Forest'},
        {'scene_number': 3, 'title': 'Resolution', 'characters': ['Bob', 'Eve'], 'setting': 'Castle'},
    ]

    # Set up chapters
    ctx.chapters = [
        {'chapter_number': 1, 'start_scene': 1, 'end_scene': 2},
        {'chapter_number': 2, 'start_scene': 3, 'end_scene': 3},
    ]

    # Set up character profiles
    ctx.character_profiles = {
        'Alice': CharacterProfile(name='Alice', role='protagonist', traits=['brave']),
        'Bob': CharacterProfile(name='Bob', role='antagonist'),
        'Eve': CharacterProfile(name='Eve'),
    }

    # Set up location profiles
    ctx.location_profiles = {
        'Castle': LocationProfile(name='Castle', atmosphere='dark'),
        'Forest': LocationProfile(name='Forest', atmosphere='mystical'),
    }

    # Set up a previous generated chapter for continuity
    ctx.generated_chapters[1] = GeneratedChapter(
        chapter_number=1, title='The Beginning',
        content='Chapter one content...', word_count=100,
        summary='Alice arrived at the castle.', source_scenes=[1, 2]
    )

    # Test chapter 1 context
    ch1_ctx = ctx.get_chapter_context(1)

    assert ch1_ctx != {}
    assert len(ch1_ctx['scenes']) == 2
    assert 'Alice' in ch1_ctx['characters']
    assert 'Bob' in ch1_ctx['characters']
    assert 'Eve' not in ch1_ctx['characters']
    assert 'Castle' in ch1_ctx['locations']
    assert 'Forest' in ch1_ctx['locations']
    assert ch1_ctx['chapter_position']['is_first'] is True
    assert ch1_ctx['chapter_position']['is_last'] is False
    assert ch1_ctx['previous_summaries'] == []

    # Test chapter 2 context
    ch2_ctx = ctx.get_chapter_context(2)

    assert len(ch2_ctx['scenes']) == 1
    assert 'Bob' in ch2_ctx['characters']
    assert 'Eve' in ch2_ctx['characters']
    assert 'Alice' not in ch2_ctx['characters']
    assert 'Castle' in ch2_ctx['locations']
    assert ch2_ctx['chapter_position']['is_first'] is False
    assert ch2_ctx['chapter_position']['is_last'] is True
    assert len(ch2_ctx['previous_summaries']) == 1
    assert ch2_ctx['previous_summaries'][0]['chapter'] == 1

    print("  get_chapter_context (full): OK")


def test_story_context_previous_summaries_max_3():
    """Test that previous_summaries returns at most 3 entries."""
    ctx = StoryContext()
    ctx.chapters = [
        {'chapter_number': i, 'start_scene': i, 'end_scene': i}
        for i in range(1, 6)
    ]
    ctx.scenes = [{'scene_number': i} for i in range(1, 6)]

    for i in range(1, 5):
        ctx.generated_chapters[i] = GeneratedChapter(
            chapter_number=i, title=f'Ch {i}',
            content='...', word_count=10,
            summary=f'Summary {i}', source_scenes=[i]
        )

    ch5_ctx = ctx.get_chapter_context(5)
    assert len(ch5_ctx['previous_summaries']) == 3
    assert ch5_ctx['previous_summaries'][0]['chapter'] == 2
    assert ch5_ctx['previous_summaries'][-1]['chapter'] == 4

    print("  previous_summaries (max 3): OK")


def test_story_context_active_threads():
    """Test _get_active_threads filters by scene range."""
    ctx = StoryContext()

    ctx.plot_threads = [
        {'report_subject': 'Thread A', 'content_json': {'scenes': [1, 2, 3]}},
        {'report_subject': 'Thread B', 'content_json': {'scenes': [4, 5]}},
        {'report_subject': 'Thread C', 'content_json': {}},  # No scenes = always active
    ]

    # Scenes 1-3 should match Thread A and Thread C
    active = ctx._get_active_threads(1, 3)
    subjects = [t['report_subject'] for t in active]
    assert 'Thread A' in subjects
    assert 'Thread C' in subjects
    assert 'Thread B' not in subjects

    # Scenes 4-5 should match Thread B and Thread C
    active = ctx._get_active_threads(4, 5)
    subjects = [t['report_subject'] for t in active]
    assert 'Thread B' in subjects
    assert 'Thread C' in subjects
    assert 'Thread A' not in subjects

    print("  _get_active_threads: OK")


def test_story_context_helper_methods():
    """Test helper methods (get_all_character_names, etc)."""
    ctx = StoryContext()
    ctx.character_profiles = {
        'Alice': CharacterProfile(name='Alice'),
        'Bob': CharacterProfile(name='Bob'),
    }
    ctx.location_profiles = {
        'Castle': LocationProfile(name='Castle'),
    }
    ctx.scenes = [{'scene_number': 1}, {'scene_number': 2}]
    ctx.chapters = [{'chapter_number': 1}]

    assert set(ctx.get_all_character_names()) == {'Alice', 'Bob'}
    assert ctx.get_all_location_names() == ['Castle']
    assert ctx.get_total_scene_count() == 2
    assert ctx.get_total_chapter_count() == 1

    print("  Helper methods: OK")


def test_story_context_string_characters():
    """Test get_chapter_context handles characters as string instead of list."""
    ctx = StoryContext()
    ctx.scenes = [
        {'scene_number': 1, 'characters': 'Solo Character', 'setting': ''},
    ]
    ctx.chapters = [{'chapter_number': 1, 'start_scene': 1, 'end_scene': 1}]
    ctx.character_profiles = {'Solo Character': CharacterProfile(name='Solo Character')}

    ch_ctx = ctx.get_chapter_context(1)
    assert 'Solo Character' in ch_ctx['characters']

    print("  String characters handling: OK")


# ─── Dataclass Tests ───────────────────────────────────────────────────────────

def test_character_profile_defaults():
    """Test CharacterProfile default field values."""
    cp = CharacterProfile(name='Test')

    assert cp.name == 'Test'
    assert cp.traits == []
    assert cp.role == ''
    assert cp.arc_summary == ''
    assert cp.motivations == {}
    assert cp.relationships == []
    assert cp.first_appearance_scene == 0
    assert cp.scenes_present == []
    assert cp.graph_properties == {}

    print("  CharacterProfile defaults: OK")


def test_location_profile_defaults():
    """Test LocationProfile default field values."""
    lp = LocationProfile(name='Test')

    assert lp.name == 'Test'
    assert lp.description == ''
    assert lp.atmosphere == ''
    assert lp.significance == ''
    assert lp.scenes_present == []
    assert lp.graph_properties == {}

    print("  LocationProfile defaults: OK")


def test_generated_chapter_defaults():
    """Test GeneratedChapter fields."""
    gc = GeneratedChapter(
        chapter_number=1, title='Intro',
        content='Content here', word_count=2
    )

    assert gc.chapter_number == 1
    assert gc.title == 'Intro'
    assert gc.content == 'Content here'
    assert gc.word_count == 2
    assert gc.summary == ''
    assert gc.source_scenes == []

    print("  GeneratedChapter defaults: OK")


# ─── Prompt Template Tests ─────────────────────────────────────────────────────

def test_prose_generation_prompt_placeholders():
    """Test that prose generation prompt has all required placeholders."""
    prompt = NovelWriterPrompts.get_prose_generation_prompt()

    required_placeholders = [
        '{chapter_number}', '{total_chapters}', '{chapter_title}',
        '{chapter_position_guidance}', '{author_style_instructions}',
        '{previous_chapter_summaries}', '{character_profiles}',
        '{location_profiles}', '{active_plot_threads}',
        '{scene_content}', '{target_word_count}',
    ]

    for ph in required_placeholders:
        assert ph in prompt, f"Missing placeholder: {ph}"

    print("  Prose generation prompt placeholders: OK")


def test_chapter_summary_prompt_placeholders():
    """Test that chapter summary prompt has required placeholders."""
    prompt = NovelWriterPrompts.get_chapter_summary_prompt()

    assert '{chapter_content}' in prompt
    assert '{chapter_number}' in prompt

    print("  Chapter summary prompt placeholders: OK")


def test_quality_assessment_prompt_placeholders():
    """Test that quality assessment prompt has required placeholders."""
    prompt = NovelWriterPrompts.get_quality_assessment_prompt()

    assert '{chapter_content}' in prompt
    assert '{author_style_reference}' in prompt
    assert '{scene_coverage_checklist}' in prompt
    # Should contain all 10 dimension names
    for dim in ALL_DIMENSIONS:
        assert dim in prompt, f"Missing dimension in assessment prompt: {dim}"

    print("  Quality assessment prompt placeholders: OK")


def test_improvement_prompt_placeholders():
    """Test that improvement prompt has required placeholders."""
    prompt = NovelWriterPrompts.get_improvement_prompt()

    assert '{chapter_content}' in prompt
    assert '{quality_feedback}' in prompt
    assert '{weak_dimensions}' in prompt
    assert '{expansion_guidance}' in prompt
    assert '{revision_mode_guidance}' in prompt
    assert '{author_style_examples}' in prompt

    print("  Improvement prompt placeholders: OK")


def test_author_style_instruction_none():
    """Test author style instruction with None returns default."""
    result = NovelWriterPrompts.get_author_style_instruction(None)

    assert 'No author style profile available' in result
    assert isinstance(result, str)

    print("  Author style instruction (None): OK")


def test_author_style_examples_none():
    """Test author style examples with None returns default."""
    result = NovelWriterPrompts.get_author_style_examples(None, 'dialogue')

    assert 'No author style examples' in result

    print("  Author style examples (None): OK")


def test_chapter_position_guidance_first():
    """Test position guidance for first chapter."""
    result = NovelWriterPrompts.get_chapter_position_guidance(
        is_first=True, is_last=False, chapter_number=1, total_chapters=10
    )

    assert 'OPENING' in result
    assert 'initial cadence' in result.lower()

    print("  Chapter position guidance (first): OK")


def test_chapter_position_guidance_last():
    """Test position guidance for last chapter."""
    result = NovelWriterPrompts.get_chapter_position_guidance(
        is_first=False, is_last=True, chapter_number=10, total_chapters=10
    )

    assert 'FINAL' in result
    assert 'ending logic' in result.lower()

    print("  Chapter position guidance (last): OK")


def test_chapter_position_guidance_middle():
    """Test position guidance for middle chapters."""
    early = NovelWriterPrompts.get_chapter_position_guidance(
        is_first=False, is_last=False, chapter_number=2, total_chapters=10
    )
    assert 'EARLY' in early

    mid = NovelWriterPrompts.get_chapter_position_guidance(
        is_first=False, is_last=False, chapter_number=5, total_chapters=10
    )
    assert 'MIDDLE' in mid

    late = NovelWriterPrompts.get_chapter_position_guidance(
        is_first=False, is_last=False, chapter_number=8, total_chapters=10
    )
    assert 'LATE' in late

    print("  Chapter position guidance (middle stages): OK")


def test_prose_prompt_formats_cleanly():
    """Test that prose generation prompt can be formatted without errors."""
    prompt_template = NovelWriterPrompts.get_prose_generation_prompt()

    formatted = prompt_template.format(
        chapter_number=1,
        total_chapters=5,
        chapter_title='The Beginning',
        chapter_position_guidance='OPENING CHAPTER REQUIREMENTS...',
        rewrite_policy_guidance='Preserve source structure.',
        negative_constraints='- avoid melodrama',
        author_style_weight='Use author style as a balanced surface influence.',
        author_style_instructions='Write in a literary style.',
        writing_perspective_instruction='Use FIRST PERSON throughout.',
        previous_chapter_summaries='This is the first chapter.',
        character_profiles='- Alice: protagonist',
        location_profiles='- Castle: dark atmosphere',
        active_plot_threads='- Main conflict thread',
        scene_content='Scene 1 content here...',
        target_word_count=2500,
    )

    assert 'Chapter 1' in formatted or 'chapter_number' not in formatted
    assert len(formatted) > 100

    print("  Prose prompt formatting: OK")


# ─── Quality Assessment Logic Tests ───────────────────────────────────────────

def test_quality_dimensions_complete():
    """Test that all current quality dimensions are defined."""
    assert len(ALL_DIMENSIONS) == 14
    assert len(DIMENSION_WEIGHTS) == 14

    expected = {
        'opening_hook', 'ending_impact', 'character_descriptions',
        'location_atmosphere', 'dialogue_depth', 'action_pacing',
        'thematic_depth', 'show_dont_tell', 'author_style', 'scene_coverage',
        'pov_consistency', 'perspective_continuity', 'chapter_break_integrity',
        'redundancy_control',
    }
    assert set(ALL_DIMENSIONS) == expected

    print("  Quality dimensions complete: OK")


def test_dimension_weights_positive():
    """Test that all dimension weights are positive numbers."""
    for dim, weight in DIMENSION_WEIGHTS.items():
        assert isinstance(weight, (int, float)), f"Weight for {dim} is not numeric"
        assert weight > 0, f"Weight for {dim} must be positive"

    print("  Dimension weights positive: OK")


def test_revision_actions_defined():
    """Test that policy-aware revision actions are defined for key dimensions."""
    assert len(REVISION_ACTIONS) > 0

    for dim, action in REVISION_ACTIONS.items():
        assert isinstance(action, str), f"Revision action for {dim} is not text"
        assert action.strip(), f"Revision action for {dim} must not be empty"

    print("  Revision actions defined: OK")


def test_expansion_factors_defined():
    """Backward-compatible alias for the revision actions completeness check."""
    test_revision_actions_defined()


def test_quality_assessment_json_parsing():
    """Test parsing of a well-formed assessment JSON response."""
    # Instantiate with mock deps to access _parse_assessment_response
    class FakePool:
        pass

    class FakeEngine:
        pass

    stage = QualityAssessmentStage.__new__(QualityAssessmentStage)
    stage.logger = __import__('logging').getLogger('test')

    # Simulate a valid LLM JSON response
    valid_response = json.dumps({
        "scores": {
            "opening_hook": 7,
            "ending_impact": 6,
            "character_descriptions": 8,
            "location_atmosphere": 5,
            "dialogue_depth": 4,
            "action_pacing": 7,
            "thematic_depth": 6,
            "show_dont_tell": 8,
            "author_style": 7,
            "scene_coverage": 9,
        },
        "feedback": {
            "opening_hook": "Strong hook.",
            "ending_impact": "Decent ending.",
            "character_descriptions": "Well drawn.",
            "location_atmosphere": "Needs work.",
            "dialogue_depth": "Too shallow.",
            "action_pacing": "Good pacing.",
            "thematic_depth": "Adequate.",
            "show_dont_tell": "Excellent showing.",
            "author_style": "Mostly on target.",
            "scene_coverage": "All scenes covered.",
        },
        "overall_score": 6.7,
        "top_issues": ["Dialogue depth", "Location atmosphere", "Ending impact"]
    })

    result = stage._parse_assessment_response(valid_response)

    assert result is not None
    assert 'scores' in result
    assert 'overall_score' in result
    assert 'weak_dimensions' in result
    assert isinstance(result['overall_score'], float)
    # Dimensions scoring below 6 should be flagged as weak
    weak_names = [w['dimension'] for w in result['weak_dimensions']]
    assert 'dialogue_depth' in weak_names
    assert 'location_atmosphere' in weak_names

    print("  Quality assessment JSON parsing: OK")


def test_quality_assessment_json_with_markdown_fences():
    """Test parsing JSON wrapped in markdown code fences."""
    stage = QualityAssessmentStage.__new__(QualityAssessmentStage)
    stage.logger = __import__('logging').getLogger('test')

    fenced_response = '```json\n{"scores": {"opening_hook": 5}, "feedback": {}, "overall_score": 5.0, "top_issues": []}\n```'

    result = stage._parse_assessment_response(fenced_response)
    assert result is not None
    assert result['scores']['opening_hook'] == 5

    print("  Quality assessment markdown fence handling: OK")


def test_quality_assessment_json_invalid():
    """Test parsing returns None for invalid JSON."""
    stage = QualityAssessmentStage.__new__(QualityAssessmentStage)
    stage.logger = __import__('logging').getLogger('test')

    result = stage._parse_assessment_response("This is not JSON at all")
    assert result is None

    print("  Quality assessment invalid JSON: OK")


# ─── Status Model Tests ───────────────────────────────────────────────────────

def test_draft_status_novel_writer_values():
    """Test that DraftStatus contains all novel writer status values."""
    nw_values = [
        'novel_writing', 'nw_stage_1_complete', 'nw_stage_2_complete',
        'nw_stage_3_complete', 'nw_stage_4_complete',
        'nw_completed', 'nw_failed',
    ]

    for val in nw_values:
        assert DraftStatus.is_valid(val), f"DraftStatus missing value: {val}"

    print("  DraftStatus novel writer values: OK")


def test_novel_writer_status_references_draft_status():
    """Test that NovelWriterStatus values match DraftStatus values."""
    assert NovelWriterStatus.NOVEL_WRITING == 'novel_writing'
    assert NovelWriterStatus.STAGE_1_COMPLETE == 'nw_stage_1_complete'
    assert NovelWriterStatus.STAGE_2_COMPLETE == 'nw_stage_2_complete'
    assert NovelWriterStatus.STAGE_3_COMPLETE == 'nw_stage_3_complete'
    assert NovelWriterStatus.STAGE_4_COMPLETE == 'nw_stage_4_complete'
    assert NovelWriterStatus.COMPLETED == 'nw_completed'
    assert NovelWriterStatus.FAILED == 'nw_failed'

    print("  NovelWriterStatus references: OK")


def test_novel_writer_processing_statuses():
    """Test that novel writer processing statuses are included."""
    processing = DraftStatus.get_processing_statuses()

    assert 'novel_writing' in processing
    assert 'nw_stage_1_complete' in processing
    assert 'nw_stage_4_complete' in processing

    print("  Novel writer processing statuses: OK")


def test_novel_writer_final_statuses():
    """Test that novel writer final statuses are included."""
    final = DraftStatus.get_final_statuses()

    assert 'nw_completed' in final
    assert 'nw_failed' in final

    print("  Novel writer final statuses: OK")


def test_novel_writer_is_novel_writing():
    """Test NovelWriterStatus.is_novel_writing helper."""
    assert NovelWriterStatus.is_novel_writing('novel_writing') is True
    assert NovelWriterStatus.is_novel_writing('nw_stage_2_complete') is True
    assert NovelWriterStatus.is_novel_writing('nw_completed') is False
    assert NovelWriterStatus.is_novel_writing('processing') is False

    print("  NovelWriterStatus.is_novel_writing: OK")


# ─── PipelineStageResult Tests ────────────────────────────────────────────────

def test_pipeline_result_success():
    """Test PipelineStageResult.success_result."""
    result = PipelineStageResult.success_result('TestStage', chapters=5)

    assert result.success is True
    assert result.stage_name == 'TestStage'
    assert result.data['chapters'] == 5

    d = result.to_dict()
    assert d['success'] is True
    assert d['stage_name'] == 'TestStage'
    assert d['chapters'] == 5
    assert 'timestamp' in d

    print("  PipelineStageResult success: OK")


def test_pipeline_result_error():
    """Test PipelineStageResult.error_result."""
    result = PipelineStageResult.error_result('TestStage', error='Something broke')

    assert result.success is False
    assert result.data['error'] == 'Something broke'

    d = result.to_dict()
    assert d['success'] is False
    assert d['error'] == 'Something broke'

    print("  PipelineStageResult error: OK")


def test_pipeline_result_add_data():
    """Test PipelineStageResult.add_data."""
    result = PipelineStageResult.success_result('TestStage')
    result.add_data(extra='value', count=42)

    d = result.to_dict()
    assert d['extra'] == 'value'
    assert d['count'] == 42

    print("  PipelineStageResult add_data: OK")


# ─── PipelineStageContext Tests ───────────────────────────────────────────────

def test_pipeline_context_metadata():
    """Test PipelineStageContext metadata get/set."""
    ctx = PipelineStageContext(
        draft_id='test-123',
        config={'quality_threshold': 7.0}
    )

    assert ctx.draft_id == 'test-123'
    assert ctx.config.get('quality_threshold') == 7.0
    assert ctx.get('nonexistent') is None
    assert ctx.get('nonexistent', 'default') == 'default'

    ctx.set('story_context', {'key': 'value'})
    assert ctx.get('story_context') == {'key': 'value'}

    ctx.update(a=1, b=2)
    assert ctx.get('a') == 1
    assert ctx.get('b') == 2

    print("  PipelineStageContext metadata: OK")


def test_pipeline_context_connection_passthrough():
    """Test that connection kwarg is stored in metadata."""
    fake_conn = object()
    ctx = PipelineStageContext(
        draft_id='test-456',
        connection=fake_conn,
    )

    assert ctx.get('connection') is fake_conn

    print("  PipelineStageContext connection: OK")


# ─── Runner ───────────────────────────────────────────────────────────────────

def run_all_unit_tests():
    """Run all novel writer unit tests."""
    print("=" * 60)
    print("NOVEL WRITER - UNIT TESTS")
    print("=" * 60)

    all_tests = [
        # StoryContext
        ("StoryContext init", test_story_context_initialization),
        ("get_chapter_context (empty)", test_story_context_get_chapter_context_empty),
        ("get_chapter_context (range)", test_story_context_get_chapter_context_out_of_range),
        ("get_chapter_context (full)", test_story_context_get_chapter_context_full),
        ("Previous summaries max 3", test_story_context_previous_summaries_max_3),
        ("Active threads filtering", test_story_context_active_threads),
        ("Helper methods", test_story_context_helper_methods),
        ("String characters", test_story_context_string_characters),

        # Dataclasses
        ("CharacterProfile defaults", test_character_profile_defaults),
        ("LocationProfile defaults", test_location_profile_defaults),
        ("GeneratedChapter defaults", test_generated_chapter_defaults),

        # Prompt templates
        ("Prose prompt placeholders", test_prose_generation_prompt_placeholders),
        ("Summary prompt placeholders", test_chapter_summary_prompt_placeholders),
        ("Quality prompt placeholders", test_quality_assessment_prompt_placeholders),
        ("Improvement prompt placeholders", test_improvement_prompt_placeholders),
        ("Author style instruction (None)", test_author_style_instruction_none),
        ("Author style examples (None)", test_author_style_examples_none),
        ("Position guidance (first)", test_chapter_position_guidance_first),
        ("Position guidance (last)", test_chapter_position_guidance_last),
        ("Position guidance (middle)", test_chapter_position_guidance_middle),
        ("Prose prompt formatting", test_prose_prompt_formats_cleanly),

        # Quality assessment
        ("Quality dimensions complete", test_quality_dimensions_complete),
        ("Dimension weights positive", test_dimension_weights_positive),
        ("Expansion factors defined", test_expansion_factors_defined),
        ("Assessment JSON parsing", test_quality_assessment_json_parsing),
        ("Assessment markdown fences", test_quality_assessment_json_with_markdown_fences),
        ("Assessment invalid JSON", test_quality_assessment_json_invalid),

        # Status model
        ("DraftStatus NW values", test_draft_status_novel_writer_values),
        ("NovelWriterStatus refs", test_novel_writer_status_references_draft_status),
        ("NW processing statuses", test_novel_writer_processing_statuses),
        ("NW final statuses", test_novel_writer_final_statuses),
        ("is_novel_writing helper", test_novel_writer_is_novel_writing),

        # Pipeline result/context
        ("PipelineResult success", test_pipeline_result_success),
        ("PipelineResult error", test_pipeline_result_error),
        ("PipelineResult add_data", test_pipeline_result_add_data),
        ("PipelineContext metadata", test_pipeline_context_metadata),
        ("PipelineContext connection", test_pipeline_context_connection_passthrough),
    ]

    failed = []
    for name, test_fn in all_tests:
        try:
            test_fn()
        except Exception as e:
            print(f"  FAILED: {name} - {e}")
            failed.append(name)

    # Summary
    total = len(all_tests)
    passed = total - len(failed)

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} passed")
    print("=" * 60)

    if not failed:
        print("All novel writer unit tests passed.")
    else:
        for name in failed:
            print(f"  FAILED: {name}")

    return len(failed) == 0


if __name__ == "__main__":
    success = run_all_unit_tests()
    sys.exit(0 if success else 1)
