import os
import sys
from io import BytesIO


import pytest
from flask import Flask

from src.api.deconstructor import deconstruct
from src.api.novel_pipeline_orchestrator import (
    PipelineCallerData,
    PipelineStartRequest,
    StyleAnalyzerConfig,
    _build_pipeline_payload,
    _build_pipeline_runtime_metadata,
    _claim_phase_execution,
)
from src.api.novel_writer import rewrite_novel
from src.api.style_analyzer import analyze_style
from src.models.request import RewritePolicy
from src.models.style_analyzer.author_style import (
    AuthorStyle,
    AuthorStyleAdaptation,
    AuthorStyleExamples,
    AuthorStyleTechniques,
)
from src.services.deconstructor.stage_3_sceneExtract import SceneDetectionStage
from src.services.novel_writer.prompt_template import NovelWriterPrompts
from src.services.novel_writer.rewrite_policy import compile_rewrite_policy
from src.services.style_analyzer.orchestrator import StyleAnalyzerOrchestrator
from src.services.style_analyzer.stage_2_profiling import ProfilingStage


def test_rewrite_policy_deduplicates_constraints():
    policy = RewritePolicy(
        negative_constraints=[" avoid melodrama ", "avoid melodrama", "", "avoid archaic dialogue"]
    )
    assert policy.negative_constraints == [
        "avoid melodrama",
        "avoid archaic dialogue",
    ]


def test_compiled_rewrite_policy_preserves_manuscript_fallback():
    compiled = compile_rewrite_policy(
        {
            "style_transfer_strength": "low",
            "style_source_priority": "preserve_manuscript",
            "negative_constraints": ["avoid melodrama"],
        },
        None,
    )
    assert "Preserve scene order" in compiled.generation_guidance
    assert "avoid melodrama" in compiled.negative_constraints_block
    assert "Preserve manuscript-native style characteristics" in compiled.author_style_guidance
    assert compiled.improvement_mode == "preserve_and_tighten"


def test_compiled_rewrite_policy_feeds_generation_assessment_and_improvement_consistently():
    compiled = compile_rewrite_policy(
        {
            "style_transfer_strength": "high",
            "style_source_priority": "favor_author",
            "negative_constraints": ["avoid melodrama", "avoid archaic dialogue"],
        },
        None,
    )

    assert "user negative constraints second" in compiled.generation_guidance
    assert "Hard invariants include scene coverage" in compiled.assessment_guidance
    assert "Do not add ornamental prose" in compiled.improvement_guidance
    assert "avoid melodrama" in compiled.negative_constraints_block
    assert compiled.improvement_mode == "strong_transfer_with_guardrails"


def test_novel_writer_prompts_remove_literary_default_language():
    prose_prompt = NovelWriterPrompts.get_prose_generation_prompt()
    quality_prompt = NovelWriterPrompts.get_quality_assessment_prompt()
    improvement_prompt = NovelWriterPrompts.get_improvement_prompt()
    fallback = NovelWriterPrompts.get_author_style_instruction(None)

    assert "master novelist" not in prose_prompt.lower()
    assert "literary quality assessor" not in quality_prompt.lower()
    assert "master literary editor" not in improvement_prompt.lower()
    assert "rich, literary style" not in fallback.lower()
    assert "NEGATIVE CONSTRAINTS:" in prose_prompt
    assert "NEGATIVE CONSTRAINTS:" in quality_prompt
    assert "NEGATIVE CONSTRAINTS:" in improvement_prompt


def test_style_analyzer_structured_parser_normalizes_v2_shape():
    stage = ProfilingStage.__new__(ProfilingStage)
    raw = """
    {
      "techniques": {
        "voice": {"diction": "plain", "syntax": null},
        "dialogue": {"conversation_style": "terse", "speaker_differentiation": "clear", "dialogue_narration_balance": "balanced"},
        "description": {"description_density": "sparse", "sensory_focus": "visual", "atmosphere_strategy": "restrained"},
        "exposition": {"exposition_strategy": "direct", "context_integration": "inline", "terminology_handling": "light"},
        "pacing": {"scene_tempo": "steady", "transition_style": "clean", "tension_pattern": "measured"},
        "narrative": {"pov_tendency": "close third", "narrative_distance": "close", "redundancy_avoidance": null}
      },
      "examples": {"voice": "short sample"},
      "adaptation": {"portable_traits": "plain diction"}
    }
    """

    parsed = ProfilingStage._parse_structured_response(stage, raw)
    assert parsed.schema_version == 2
    assert parsed.techniques.voice.syntax == ""
    assert parsed.examples.voice == ["short sample"]
    assert parsed.adaptation.portable_traits == ["plain diction"]


def test_style_analyzer_rejects_schema_v1_on_get():
    orchestrator = StyleAnalyzerOrchestrator.__new__(StyleAnalyzerOrchestrator)
    orchestrator._get_author_style = lambda workspace_id, author_name: (
        "style-1",
        1,
        {},
        {},
        {},
    )

    with pytest.raises(ValueError, match="schema_version"):
        orchestrator.check_and_clean(
            author_name="Legacy Author",
            caller=type("Caller", (), {"workspace_id": "ws-1"})(),
            on_exist="get",
        )


def test_scene_detection_accepts_structurally_coherent_out_of_band_output():
    stage = SceneDetectionStage.__new__(SceneDetectionStage)
    stage.logger = __import__("logging").getLogger("test.scene")
    stage._get_scene_count_band = lambda text: {
        "target_scene_count": 5,
        "soft_min_scenes": 4,
        "soft_max_scenes": 6,
    }
    stage._detect_scenes = lambda text, band: [
        {
            "scene_number": 1,
            "title": "Sparse Opening",
            "setting": "Arcology rooftop",
            "characters": ["Mira"],
            "summary": "Mira surveys the city before the handoff.",
            "content": "",
            "start_marker": "Mira crossed the roof",
            "end_marker": "The courier never arrived",
        }
    ]
    stage._retry_scene_detection = stage._detect_scenes

    scenes = stage._process_chunk(1, "word " * 4500, 10)

    assert len(scenes) == 1
    assert scenes[0]["scene_number"] == 10


def test_pipeline_payload_round_trips_for_queue_rehydration():
    request = PipelineStartRequest(
        caller=PipelineCallerData(
            user_id="1",
            workspace_id="ws-1",
            project_id="proj-1",
        ),
        author_name="Queue Ready Author",
        provider="gemini",
        model="gemini-2.5-flash",
        generation_config={"temperature": 0.4, "max_output_tokens": 800},
        rewrite_policy={
            "style_transfer_strength": "high",
            "style_source_priority": "balanced",
            "negative_constraints": ["avoid melodrama"],
        },
        style_analyzer_config=StyleAnalyzerConfig(
            provider="openai",
            model="gpt-test",
            generation_config={"temperature": 0.1},
        ),
    )

    payload = _build_pipeline_payload(
        data=request,
        manuscript_filename="ms.txt",
        author_file_paths=["/tmp/a.txt"],
    )
    metadata = _build_pipeline_runtime_metadata("run-1", "draft-1", payload)

    import json
    round_tripped = json.loads(json.dumps(payload))

    assert round_tripped == payload
    assert StyleAnalyzerConfig(**payload["style_analyzer_config"]).provider == "openai"
    assert metadata["policy_snapshot"]["rewrite_policy"]["negative_constraints"] == [
        "avoid melodrama"
    ]
    assert metadata["phase_payloads"]["phase_3"]["rewrite_policy"] == payload["rewrite_policy"]


def test_phase_claim_is_idempotent_for_completed_and_running_states():
    completed_conn = _FakeConnection(fetches=[
        (
            "run-1", "draft-1", "ws-1", "1", None, "Author", "running", 1,
            "completed", "pending", "pending", {}, None, None, None, None, {},
        )
    ])
    should_run, skip_result = _claim_phase_execution(completed_conn, "run-1", 1)
    assert should_run is False
    assert skip_result["skipped"] is True
    assert skip_result["already_completed"] is True

    running_conn = _FakeConnection(fetches=[
        (
            "run-1", "draft-1", "ws-1", "1", None, "Author", "running", 2,
            "completed", "running", "pending", {}, None, None, None, None, {},
        )
    ])
    should_run, skip_result = _claim_phase_execution(running_conn, "run-1", 2)
    assert should_run is False
    assert skip_result["skipped"] is True
    assert skip_result["already_running"] is True


class _FakeConnection:
    def __init__(self, fetches):
        self.fetches = list(fetches)
        self.executed = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._current = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self.conn.executed.append((query, params))
        if self.conn.fetches:
            self._current = self.conn.fetches.pop(0)
        else:
            self._current = None

    def fetchone(self):
        return self._current

    def fetchall(self):
        return self._current or []


class _FakePool:
    def __init__(self, connections):
        self.connections = list(connections)

    def getconn(self):
        return self.connections.pop(0)

    def putconn(self, conn):
        pass


class _NoopThread:
    def __init__(self, target=None, kwargs=None, daemon=None):
        self.target = target
        self.kwargs = kwargs or {}

    def start(self):
        if self.target:
            return self.target(**self.kwargs)
        return None


def _make_app(blueprint, tmp_path, connection_pool):
    app = Flask(__name__)
    app.register_blueprint(blueprint, url_prefix="/api")
    app.config["TESTING"] = True
    app.config["UPLOAD_PATH"] = str(tmp_path)
    app.config["CONNECTION_POOL"] = connection_pool
    return app


def test_deconstruct_endpoint_persists_rewrite_policy(monkeypatch, tmp_path):
    manuscript = tmp_path / "manuscript.txt"
    manuscript.write_text("hello world", encoding="utf-8")

    conn = _FakeConnection(fetches=[("draft-1", "ws-1", 1), None])
    app = _make_app(deconstruct, tmp_path, _FakePool([conn]))

    monkeypatch.setattr("src.api.deconstructor.threading.Thread", _NoopThread)
    monkeypatch.setattr("src.api.deconstructor.GenerationEngine", lambda request: object())
    monkeypatch.setattr(
        "src.api.deconstructor.DeconstructorOrchestrator",
        lambda generation_engine, db_pool: type("Orch", (), {"run_pipeline": lambda *args, **kwargs: None})(),
    )

    client = app.test_client()
    response = client.post(
        "/api/deconstruct",
        json={
            "draft_id": "draft-1",
            "file_name": "manuscript.txt",
            "user_id": 1,
            "workspace_id": "ws-1",
            "project_id": "proj-1",
            "rewrite_policy": {
                "style_transfer_strength": "medium",
                "style_source_priority": "balanced",
                "negative_constraints": ["avoid melodrama"],
            },
        },
    )

    assert response.status_code == 202
    update_query = conn.executed[1]
    assert "metadata = COALESCE" in update_query[0]
    assert "avoid melodrama" in update_query[1][1]


def test_novel_writer_endpoint_uses_stored_rewrite_policy(monkeypatch, tmp_path):
    stored_policy = {
        "style_transfer_strength": "low",
        "style_source_priority": "preserve_manuscript",
        "negative_constraints": ["avoid archaic dialogue"],
    }
    conn = _FakeConnection(
        fetches=[
            ("draft-1", "ws-1", 1, "completed", {"rewrite_policy": stored_policy}),
            None,
        ]
    )
    app = _make_app(rewrite_novel, tmp_path, _FakePool([conn]))

    captured = {}

    class _FakeWriterOrchestrator:
        def __init__(self, generation_engine, db_pool):
            pass

        def run_pipeline(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("src.api.novel_writer.threading.Thread", _NoopThread)
    monkeypatch.setattr("src.api.novel_writer.GenerationEngine", lambda request: object())
    monkeypatch.setattr("src.api.novel_writer.NovelWriterOrchestrator", _FakeWriterOrchestrator)

    client = app.test_client()
    response = client.post(
        "/api/novel-writer/generate",
        json={
            "draft_id": "draft-1",
            "user_id": 1,
            "workspace_id": "ws-1",
            "project_id": "proj-1",
        },
    )

    assert response.status_code == 202
    assert captured["config"]["rewrite_policy"] == stored_policy


def test_analyze_style_endpoint_returns_schema_v2(monkeypatch, tmp_path):
    app = _make_app(analyze_style, tmp_path, _FakePool([]))

    author_style = AuthorStyle(
        schema_version=2,
        techniques=AuthorStyleTechniques(),
        examples=AuthorStyleExamples(),
        adaptation=AuthorStyleAdaptation(),
    )

    class _FakeOrchestrator:
        def __init__(self, *args, **kwargs):
            pass

        def check_and_clean(self, author_name, caller, on_exist):
            return "style-1", author_style

    monkeypatch.setattr("src.api.style_analyzer.SamplingStage", lambda *args, **kwargs: object())
    monkeypatch.setattr("src.api.style_analyzer.ProfilingStage", lambda *args, **kwargs: object())
    monkeypatch.setattr("src.api.style_analyzer.StyleAnalyzerOrchestrator", _FakeOrchestrator)

    client = app.test_client()
    response = client.post(
        "/api/analyze-style",
        data={
            "data": '{"caller":{"user_id":"1","workspace_id":"ws-1","project_id":"proj-1"},"author_name":"A","on_exist":"get"}',
            "files": (BytesIO(b"sample"), "sample.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.get_json()["author_style"]["schema_version"] == 2


def test_analyze_style_endpoint_propagates_provider_model_and_generation_config(monkeypatch, tmp_path):
    app = _make_app(analyze_style, tmp_path, _FakePool([]))

    captured = {}

    class _FakeSamplingStage:
        def __init__(self, db_pool=None, min_success_samples=None):
            captured["sampling"] = {
                "min_success_samples": min_success_samples,
            }

    class _FakeProfilingStage:
        def __init__(
            self,
            db_pool=None,
            provider=None,
            model=None,
            max_output_tokens=None,
            generation_config=None,
            min_success_partial_style=None,
        ):
            captured["profiling"] = {
                "provider": provider,
                "model": model,
                "max_output_tokens": max_output_tokens,
                "generation_config": generation_config,
                "min_success_partial_style": min_success_partial_style,
            }

    class _FakeOrchestrator:
        def __init__(self, db_pool, sampling_stage, profiling_stage):
            pass

        def check_and_clean(self, author_name, caller, on_exist):
            return "style-1", None

        def run_pipeline(self, author_style_id, author_name, file_paths, caller):
            return {
                "status": "profiling_completed",
                "author_style": AuthorStyle(
                    schema_version=2,
                    techniques=AuthorStyleTechniques(),
                    examples=AuthorStyleExamples(),
                    adaptation=AuthorStyleAdaptation(),
                ),
            }

    monkeypatch.setattr("src.api.style_analyzer.SamplingStage", _FakeSamplingStage)
    monkeypatch.setattr("src.api.style_analyzer.ProfilingStage", _FakeProfilingStage)
    monkeypatch.setattr("src.api.style_analyzer.StyleAnalyzerOrchestrator", _FakeOrchestrator)

    client = app.test_client()
    response = client.post(
        "/api/analyze-style",
        data={
            "data": (
                '{"caller":{"user_id":"1","workspace_id":"ws-1","project_id":"proj-1"},'
                '"author_name":"A","on_exist":"update",'
                '"config":{"provider":"openai","model":"gpt-test","max_output_tokens":777,'
                '"min_success_samples":0.6,"min_success_partial_style":0.7},'
                '"generation_config":{"temperature":0.2,"max_output_tokens":777}}'
            ),
            "files": (BytesIO(b"sample"), "sample.txt"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert captured["sampling"]["min_success_samples"] == 0.6
    assert captured["profiling"]["provider"] == "openai"
    assert captured["profiling"]["model"] == "gpt-test"
    assert captured["profiling"]["max_output_tokens"] == 777
    assert captured["profiling"]["generation_config"] == {"temperature": 0.2, "max_output_tokens": 777}
    assert captured["profiling"]["min_success_partial_style"] == 0.7
