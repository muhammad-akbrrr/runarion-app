"""
Integration tests for the novel writer pipeline.
Tests imports, stage initialization, orchestrator wiring, method signatures,
and entity profiler merging logic.
"""

import sys
import os
import json



# ─── Import Tests ─────────────────────────────────────────────────────────────

def test_all_stage_imports():
    """Test that all novel writer stages can be imported."""
    from src.services.novel_writer.base_stage import (
        BasePipelineStage, PipelineStageContext, PipelineStageResult
    )
    from src.services.novel_writer.story_context import (
        StoryContext, CharacterProfile, LocationProfile, GeneratedChapter
    )
    from src.services.novel_writer.prompt_template import NovelWriterPrompts
    from src.services.novel_writer.entity_profiler import EntityProfilingStage
    from src.services.novel_writer.scene_generator import ProseGenerationStage
    from src.services.novel_writer.stage_3_quality import QualityAssessmentStage
    from src.services.novel_writer.stage_4_improvement import SceneImprovementStage
    from src.services.novel_writer.stage_5_assembly import ManuscriptAssemblyStage
    from src.services.novel_writer.orchestrator import NovelWriterOrchestrator
    from src.models.novel_writer.status import NovelWriterStatus

    print("  All stage imports: OK")


def test_init_exports():
    """Test that __init__.py exports all expected symbols."""
    from src.services.novel_writer import (
        NovelWriterOrchestrator,
        EntityProfilingStage,
        ProseGenerationStage,
        QualityAssessmentStage,
        SceneImprovementStage,
        ManuscriptAssemblyStage,
        StoryContext,
        CharacterProfile,
        LocationProfile,
        GeneratedChapter,
        NovelWriterPrompts,
        BasePipelineStage,
        PipelineStageContext,
        PipelineStageResult,
    )

    print("  __init__.py exports: OK")


# ─── Base Stage Inheritance Tests ─────────────────────────────────────────────

def test_all_stages_inherit_base():
    """Test that all stages inherit from the novel_writer BasePipelineStage."""
    from src.services.novel_writer.base_stage import BasePipelineStage
    from src.services.novel_writer.entity_profiler import EntityProfilingStage
    from src.services.novel_writer.scene_generator import ProseGenerationStage
    from src.services.novel_writer.stage_3_quality import QualityAssessmentStage
    from src.services.novel_writer.stage_4_improvement import SceneImprovementStage
    from src.services.novel_writer.stage_5_assembly import ManuscriptAssemblyStage

    stages = [
        EntityProfilingStage, ProseGenerationStage,
        QualityAssessmentStage, SceneImprovementStage,
        ManuscriptAssemblyStage,
    ]

    for stage_cls in stages:
        assert issubclass(stage_cls, BasePipelineStage), \
            f"{stage_cls.__name__} must inherit from BasePipelineStage"

    print("  All stages inherit BasePipelineStage: OK")


def test_base_stage_is_independent():
    """Test that novel_writer BasePipelineStage is NOT the deconstructor's."""
    from src.services.novel_writer.base_stage import BasePipelineStage as NWBase
    from src.services.deconstructor.base_stage import BasePipelineStage as DCBase

    assert NWBase is not DCBase, \
        "Novel writer BasePipelineStage must be independent from deconstructor"

    print("  BasePipelineStage independence: OK")


# ─── Orchestrator Initialization Tests ────────────────────────────────────────

def test_orchestrator_initialization():
    """Test that NovelWriterOrchestrator initializes all 5 stages."""
    from src.services.novel_writer.orchestrator import NovelWriterOrchestrator
    from src.services.novel_writer.entity_profiler import EntityProfilingStage
    from src.services.novel_writer.scene_generator import ProseGenerationStage
    from src.services.novel_writer.stage_3_quality import QualityAssessmentStage
    from src.services.novel_writer.stage_4_improvement import SceneImprovementStage
    from src.services.novel_writer.stage_5_assembly import ManuscriptAssemblyStage

    class MockEngine:
        pass

    class MockPool:
        pass

    orchestrator = NovelWriterOrchestrator(MockEngine(), MockPool())

    assert isinstance(orchestrator.stage_1, EntityProfilingStage)
    assert isinstance(orchestrator.stage_2, ProseGenerationStage)
    assert isinstance(orchestrator.stage_3, QualityAssessmentStage)
    assert isinstance(orchestrator.stage_4, SceneImprovementStage)
    assert isinstance(orchestrator.stage_5, ManuscriptAssemblyStage)

    print("  Orchestrator initializes 5 stages: OK")


def test_orchestrator_graph_service_graceful():
    """Test that orchestrator handles missing AGE gracefully."""
    from src.services.novel_writer.orchestrator import NovelWriterOrchestrator

    class MockEngine:
        pass

    class MockPool:
        pass

    # MockPool won't have a real DB, so GraphDatabaseService init will fail
    # The orchestrator should catch this and set graph_service = None
    orchestrator = NovelWriterOrchestrator(MockEngine(), MockPool())
    assert orchestrator.graph_service is None

    print("  Orchestrator graph service graceful: OK")


def test_orchestrator_has_key_methods():
    """Test that orchestrator has run_pipeline, _update_draft_status, get_pipeline_status."""
    from src.services.novel_writer.orchestrator import NovelWriterOrchestrator

    assert hasattr(NovelWriterOrchestrator, 'run_pipeline')
    assert hasattr(NovelWriterOrchestrator, '_update_draft_status')
    assert hasattr(NovelWriterOrchestrator, 'get_pipeline_status')
    assert hasattr(NovelWriterOrchestrator, '_run_stage')

    print("  Orchestrator key methods: OK")


# ─── Stage Method Signature Tests ─────────────────────────────────────────────

def test_all_stages_have_execute_stage():
    """Test all stages implement _execute_stage."""
    from src.services.novel_writer.entity_profiler import EntityProfilingStage
    from src.services.novel_writer.scene_generator import ProseGenerationStage
    from src.services.novel_writer.stage_3_quality import QualityAssessmentStage
    from src.services.novel_writer.stage_4_improvement import SceneImprovementStage
    from src.services.novel_writer.stage_5_assembly import ManuscriptAssemblyStage

    stages = [
        EntityProfilingStage, ProseGenerationStage,
        QualityAssessmentStage, SceneImprovementStage,
        ManuscriptAssemblyStage,
    ]

    for stage_cls in stages:
        assert hasattr(stage_cls, '_execute_stage'), \
            f"{stage_cls.__name__} must have _execute_stage"

    print("  All stages have _execute_stage: OK")


def test_all_stages_have_run_methods():
    """Test all stages have run() and run_with_connection() from base class."""
    from src.services.novel_writer.orchestrator import NovelWriterOrchestrator

    class MockEngine:
        pass

    class MockPool:
        pass

    orchestrator = NovelWriterOrchestrator(MockEngine(), MockPool())

    for stage_num in [1, 2, 3, 4, 5]:
        stage = getattr(orchestrator, f'stage_{stage_num}')
        assert hasattr(stage, 'run'), f"Stage {stage_num} must have run()"
        assert hasattr(stage, 'run_with_connection'), \
            f"Stage {stage_num} must have run_with_connection()"

    print("  All stages have run/run_with_connection: OK")


# ─── Entity Profiler Merging Tests ────────────────────────────────────────────

def test_entity_profiler_merge_characters():
    """Test character profile merging from multiple sources."""
    from src.services.novel_writer.entity_profiler import EntityProfilingStage
    from src.services.novel_writer.story_context import StoryContext, CharacterProfile

    # Instantiate without DB (we'll call merge directly)
    stage = EntityProfilingStage.__new__(EntityProfilingStage)
    stage.logger = __import__('logging').getLogger('test')

    ctx = StoryContext()

    # Simulate raw data from analysis reports
    ctx._raw_character_reports = [
        {
            'report_subject': 'Alice',
            'content_json': {
                'role': 'protagonist',
                'traits': ['brave', 'clever'],
                'arc_summary': 'Grows from timid to leader.',
                'motivations': {'primary': 'freedom'},
            }
        },
        {
            'report_subject': 'Bob',
            'content_json': {
                'role': 'antagonist',
                'traits': ['cunning'],
            }
        },
    ]

    # Simulate raw graph vertices
    ctx._raw_graph_characters = [
        {'name': 'Alice', 'properties': {'alias': 'The Brave'}},
        {'name': 'Charlie', 'properties': {'role': 'minor'}},
    ]

    # Simulate scene character lists
    ctx.scenes = [
        {'scene_number': 1, 'characters': ['Alice', 'Bob']},
        {'scene_number': 2, 'characters': ['Alice', 'Charlie']},
        {'scene_number': 3, 'characters': 'Dave'},  # Single string
    ]

    ctx.relationships = [
        {'source': 'Alice', 'target': 'Bob', 'relationship_type': 'OPPOSES', 'properties': {}},
    ]

    stage._merge_character_profiles(ctx)

    # Verify merged profiles
    assert 'Alice' in ctx.character_profiles
    assert 'Bob' in ctx.character_profiles
    assert 'Charlie' in ctx.character_profiles
    assert 'Dave' in ctx.character_profiles

    alice = ctx.character_profiles['Alice']
    assert alice.role == 'protagonist'
    assert 'brave' in alice.traits
    assert alice.graph_properties == {'alias': 'The Brave'}
    assert 1 in alice.scenes_present
    assert 2 in alice.scenes_present
    assert len(alice.relationships) == 1
    assert alice.relationships[0]['target'] == 'Bob'

    charlie = ctx.character_profiles['Charlie']
    assert charlie.graph_properties == {'role': 'minor'}
    assert 2 in charlie.scenes_present

    dave = ctx.character_profiles['Dave']
    assert dave.first_appearance_scene == 3

    # Verify temp attributes cleaned up
    assert not hasattr(ctx, '_raw_character_reports')
    assert not hasattr(ctx, '_raw_graph_characters')

    print("  Entity profiler character merging: OK")


def test_entity_profiler_merge_locations():
    """Test location profile merging from multiple sources."""
    from src.services.novel_writer.entity_profiler import EntityProfilingStage
    from src.services.novel_writer.story_context import StoryContext, LocationProfile

    stage = EntityProfilingStage.__new__(EntityProfilingStage)
    stage.logger = __import__('logging').getLogger('test')

    ctx = StoryContext()

    ctx._raw_setting_reports = [
        {
            'report_subject': 'Castle',
            'content_json': {
                'description': 'An ancient fortress.',
                'atmosphere': 'Dark and foreboding.',
                'significance': 'Central to the conflict.',
            }
        },
    ]

    ctx._raw_graph_locations = [
        {'name': 'Castle', 'properties': {'region': 'North'}},
        {'name': 'Forest', 'properties': {'type': 'mystical'}},
    ]

    ctx.scenes = [
        {'scene_number': 1, 'setting': 'Castle'},
        {'scene_number': 2, 'setting': 'Forest'},
        {'scene_number': 3, 'setting': 'Castle'},
    ]

    stage._merge_location_profiles(ctx)

    assert 'Castle' in ctx.location_profiles
    assert 'Forest' in ctx.location_profiles

    castle = ctx.location_profiles['Castle']
    assert castle.description == 'An ancient fortress.'
    assert castle.atmosphere == 'Dark and foreboding.'
    assert castle.graph_properties == {'region': 'North'}
    assert 1 in castle.scenes_present
    assert 3 in castle.scenes_present

    forest = ctx.location_profiles['Forest']
    assert forest.graph_properties == {'type': 'mystical'}
    assert 2 in forest.scenes_present

    assert not hasattr(ctx, '_raw_setting_reports')
    assert not hasattr(ctx, '_raw_graph_locations')

    print("  Entity profiler location merging: OK")


def test_entity_profiler_parse_json_field():
    """Test _parse_json_field handles various input types."""
    from src.services.novel_writer.entity_profiler import EntityProfilingStage

    stage = EntityProfilingStage.__new__(EntityProfilingStage)
    stage.logger = __import__('logging').getLogger('test')

    # None input
    assert stage._parse_json_field(None, default=[]) == []

    # Dict passthrough
    assert stage._parse_json_field({'key': 'val'}) == {'key': 'val'}

    # List passthrough
    assert stage._parse_json_field([1, 2]) == [1, 2]

    # Valid JSON string
    assert stage._parse_json_field('{"a": 1}') == {'a': 1}

    # Invalid JSON string
    assert stage._parse_json_field('not json', default={}) == {}

    # Numeric input
    assert stage._parse_json_field(42, default='fallback') == 'fallback'

    print("  Entity profiler _parse_json_field: OK")


def test_entity_profiler_graph_properties_string():
    """Test that string graph properties are parsed as JSON."""
    from src.services.novel_writer.entity_profiler import EntityProfilingStage
    from src.services.novel_writer.story_context import StoryContext

    stage = EntityProfilingStage.__new__(EntityProfilingStage)
    stage.logger = __import__('logging').getLogger('test')

    ctx = StoryContext()
    ctx._raw_character_reports = []
    ctx._raw_graph_characters = [
        {'name': 'Eve', 'properties': '{"role": "spy"}'},  # String JSON
    ]
    ctx.scenes = []
    ctx.relationships = []

    stage._merge_character_profiles(ctx)

    assert 'Eve' in ctx.character_profiles
    assert ctx.character_profiles['Eve'].graph_properties == {'role': 'spy'}

    print("  Entity profiler string graph properties: OK")


# ─── Scene Generator Key Methods ──────────────────────────────────────────────

def test_scene_generator_build_prompt():
    """Test that ProseGenerationStage._build_generation_prompt produces a valid prompt."""
    from src.services.novel_writer.scene_generator import ProseGenerationStage
    from src.services.novel_writer.story_context import (
        StoryContext, CharacterProfile, LocationProfile
    )

    stage = ProseGenerationStage.__new__(ProseGenerationStage)
    stage.logger = __import__('logging').getLogger('test')

    ctx = StoryContext()
    ctx.scenes = [
        {'scene_number': 1, 'title': 'Opening', 'summary': 'Hero arrives.',
         'setting': 'Castle', 'characters': ['Hero'],
         'enhanced_content': 'The hero arrived at the castle.'},
    ]
    ctx.chapters = [
        {'chapter_number': 1, 'start_scene': 1, 'end_scene': 1},
    ]
    ctx.character_profiles = {
        'Hero': CharacterProfile(name='Hero', role='protagonist', traits=['brave']),
    }
    ctx.location_profiles = {
        'Castle': LocationProfile(name='Castle', description='Ancient fortress.'),
    }
    ctx.plot_threads = []
    ctx.author_style = None

    chapter_context = ctx.get_chapter_context(1)

    prompt = stage._build_generation_prompt(
        ctx, chapter_context, chapter_number=1,
        chapter_title='The Beginning', total_chapters=3,
        target_word_count=2500
    )

    assert isinstance(prompt, str)
    assert len(prompt) > 200
    assert 'The Beginning' in prompt
    assert 'Hero' in prompt
    assert 'Castle' in prompt
    assert '2500' in prompt

    print("  Scene generator build prompt: OK")


def test_scene_generator_fallback_chapter():
    """Test _store_fallback_chapter stores concatenated scene content."""
    from src.services.novel_writer.scene_generator import ProseGenerationStage
    from src.services.novel_writer.story_context import StoryContext

    stage = ProseGenerationStage.__new__(ProseGenerationStage)
    stage.logger = __import__('logging').getLogger('test')

    ctx = StoryContext()
    ctx.scenes = [
        {'scene_number': 1, 'enhanced_content': 'Enhanced scene 1 text.'},
        {'scene_number': 2, 'enhanced_content': 'Enhanced scene 2 text.'},
        {'scene_number': 3, 'original_content': 'Original scene 3 text.'},
    ]

    chapter = {'start_scene': 1, 'end_scene': 2}

    stage._store_fallback_chapter(ctx, chapter, 1, 'Test Chapter')

    assert 1 in ctx.generated_chapters
    fb = ctx.generated_chapters[1]
    assert 'Enhanced scene 1' in fb.content
    assert 'Enhanced scene 2' in fb.content
    assert 'scene 3' not in fb.content  # Scene 3 is out of range
    assert fb.word_count > 0

    print("  Scene generator fallback chapter: OK")


# ─── Quality Assessment Scene Checklist ───────────────────────────────────────

def test_quality_build_scene_checklist():
    """Test _build_scene_checklist generates checklist from source scenes."""
    from src.services.novel_writer.stage_3_quality import QualityAssessmentStage
    from src.services.novel_writer.story_context import (
        StoryContext, GeneratedChapter
    )

    stage = QualityAssessmentStage.__new__(QualityAssessmentStage)
    stage.logger = __import__('logging').getLogger('test')

    ctx = StoryContext()
    ctx.scenes = [
        {'scene_number': 1, 'title': 'Opening', 'summary': 'Hero enters the castle.'},
        {'scene_number': 2, 'title': 'Battle', 'summary': 'A fight breaks out.'},
    ]

    chapter = GeneratedChapter(
        chapter_number=1, title='Ch1', content='...',
        word_count=10, source_scenes=[1, 2]
    )

    checklist = stage._build_scene_checklist(ctx, chapter)

    assert 'Scene 1' in checklist
    assert 'Opening' in checklist
    assert 'Scene 2' in checklist
    assert 'Battle' in checklist

    print("  Quality scene checklist: OK")


# ─── API Blueprint Test ───────────────────────────────────────────────────────

def test_api_blueprint_routes():
    """Test that novel writer API blueprint has expected routes."""
    from src.api.novel_writer import rewrite_novel

    assert rewrite_novel.name == 'rewrite_novel'

    # Check route rules are registered
    rules = []
    for rule in rewrite_novel.deferred_functions:
        rules.append(str(rule))

    # The blueprint should have deferred functions (route registrations)
    assert len(rewrite_novel.deferred_functions) >= 2, \
        f"Expected at least 2 routes, got {len(rewrite_novel.deferred_functions)}"

    print("  API blueprint routes: OK")


# ─── Runner ───────────────────────────────────────────────────────────────────

def run_all_integration_tests():
    """Run all novel writer integration tests."""
    print("=" * 60)
    print("NOVEL WRITER - INTEGRATION TESTS")
    print("=" * 60)

    all_tests = [
        # Imports
        ("All stage imports", test_all_stage_imports),
        ("__init__.py exports", test_init_exports),

        # Inheritance
        ("All stages inherit base", test_all_stages_inherit_base),
        ("BasePipelineStage independence", test_base_stage_is_independent),

        # Orchestrator
        ("Orchestrator initialization", test_orchestrator_initialization),
        ("Orchestrator graph graceful", test_orchestrator_graph_service_graceful),
        ("Orchestrator key methods", test_orchestrator_has_key_methods),

        # Method signatures
        ("_execute_stage on all stages", test_all_stages_have_execute_stage),
        ("run/run_with_connection", test_all_stages_have_run_methods),

        # Entity profiler merging
        ("Character profile merging", test_entity_profiler_merge_characters),
        ("Location profile merging", test_entity_profiler_merge_locations),
        ("_parse_json_field", test_entity_profiler_parse_json_field),
        ("String graph properties", test_entity_profiler_graph_properties_string),

        # Scene generator
        ("Build generation prompt", test_scene_generator_build_prompt),
        ("Fallback chapter storage", test_scene_generator_fallback_chapter),

        # Quality assessment
        ("Scene checklist builder", test_quality_build_scene_checklist),

        # API
        ("API blueprint routes", test_api_blueprint_routes),
    ]

    failed = []
    for name, test_fn in all_tests:
        try:
            test_fn()
        except Exception as e:
            print(f"  FAILED: {name} - {e}")
            import traceback
            traceback.print_exc()
            failed.append(name)

    # Summary
    total = len(all_tests)
    passed = total - len(failed)

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} passed")
    print("=" * 60)

    if not failed:
        print("All novel writer integration tests passed.")
    else:
        for name in failed:
            print(f"  FAILED: {name}")

    return len(failed) == 0


if __name__ == "__main__":
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)
