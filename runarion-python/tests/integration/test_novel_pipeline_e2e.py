"""
End-to-end integration test for the full 3-phase novel pipeline orchestrator.

Tests the complete flow via HTTP against a running Flask server:
  Phase 1: Deconstructor  — manuscript analysis (POST /api/novel-pipeline/start)
  Phase 2: Style Analyzer — author voice profiling (parallel with Phase 1)
  Phase 3: Novel Writer   — rewriting in author's voice

USAGE:
    # From runarion-python/ with venv active and .env loaded:
    python -m tests.integration.test_novel_pipeline_e2e

    # Or run directly:
    python tests/integration/test_novel_pipeline_e2e.py

PREREQUISITES:
  1. Flask server must be running:  python -m src.app
  2. PostgreSQL must be running with migrations applied
  3. .env must be configured with DB credentials and at least one LLM API key
  4. UPLOAD_PATH directory must be writable by the Flask process

CONFIGURATION:
  Edit the CONFIG block below to point to your sample files and server.
  The manuscript and author sample can be the same file for a quick smoke test.
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pytest

# ---------------------------------------------------------------------------
# Path setup so we can import from src/ when run directly
# ---------------------------------------------------------------------------
TEST_DIR = Path(__file__).parent
REPO_ROOT = TEST_DIR.parent.parent
PROJECT_ROOT = REPO_ROOT.parent

from dotenv import load_dotenv
load_dotenv(dotenv_path=PROJECT_ROOT / '.env')
load_dotenv(dotenv_path=REPO_ROOT / '.env')

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CONFIG — edit these to match your environment
# ---------------------------------------------------------------------------
FLASK_BASE_URL = os.getenv('PYTHON_TEST_URL', 'http://localhost:5000')

SAMPLE_DIR = TEST_DIR.parent / 'sample' / 'input'
OUTPUT_DIR = TEST_DIR.parent / 'sample' / 'output'

# Source manuscript (the story to be rewritten)
MANUSCRIPT_FILE = SAMPLE_DIR / 'short_story.pdf'

# Author voice samples (the style to imitate). Can be multiple files.
AUTHOR_SAMPLE_FILES = [
    SAMPLE_DIR / 'short_sample_1.pdf',
    SAMPLE_DIR / 'short_sample_2.pdf',
]

# Pipeline configuration
PIPELINE_CONFIG = {
    "author_name": "Test Author E2E",
    "provider": "gemini",
    "model": "gemini-2.5-flash",
    "chaptering_mode": "flexible",
    "target_chapter_length": 1000,   # small for faster tests
    "quality_threshold": 5.0,
    "enforce_hard_quality_gate": False,
    "hard_quality_threshold": 5.0,
    "max_improvement_passes": 1,
    "writing_perspective": "first_person",
    "author_style_mode": "create_or_update",
    "on_exist": "update",
    "rewrite_policy": {
        "style_transfer_strength": "medium",
        "style_source_priority": "balanced",
        "negative_constraints": ["avoid melodrama", "avoid archaic dialogue"],
    },
    "style_analyzer_config": {
        "min_success_samples": 0.5,
        "min_success_partial_style": 0.5,
    },
}

# How long to poll before giving up (seconds)
POLL_TIMEOUT = 60 * 45   # 45 minutes
POLL_INTERVAL = 15       # check every 15 seconds
MOCK_POLL_TIMEOUT = 90
MOCK_POLL_INTERVAL = 1
POLL_HEARTBEAT_SECONDS = 20
# ---------------------------------------------------------------------------

FIRST_PERSON_PRONOUNS = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves"}
SECOND_PERSON_PRONOUNS = {"you", "your", "yours", "yourself", "yourselves"}
THIRD_PERSON_PRONOUNS = {
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "they", "them", "their", "theirs", "themselves",
}

ACTION_WORDS = {
    "fight", "battle", "attack", "shoot", "gun", "gunfire", "chase", "escape",
    "strike", "kill", "blood", "panic", "explode", "explosion", "ambush", "pursuit",
}

ARCHAIC_DIALOGUE_MARKERS = {
    "thou", "thee", "thy", "thine", "hast", "dost", "art", "wherefore",
}

MOCK_CHAPTER_ANCHORS = {
    1: ("silver raven sigil", "omni-solutions"),
    2: ("gutter-flow", "freight cage"),
    3: ("silas", "veil-cove seven"),
    4: ("veridian", "memory-locket"),
    5: ("seventy-five thousand credits", "clasp"),
}


class NovelPipelineE2ETest:
    """
    End-to-end test runner for the novel pipeline orchestrator API.
    Sends real HTTP requests to a running Flask server.
    """

    def __init__(self, use_mock_provider: bool = False, pytest_mode: bool = False):
        self.base_url = FLASK_BASE_URL.rstrip('/')
        self.use_mock_provider = use_mock_provider
        self.pytest_mode = pytest_mode
        self.pipeline_run_id: str = ''
        self.draft_id: str = ''
        self.output_pdf_path: Optional[Path] = None
        self._validate_prerequisites()

    def _emit(self, message: str) -> None:
        if message:
            logger.info(message)
        if not self.pytest_mode:
            print(message, flush=True)

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _validate_prerequisites(self):
        self._emit("Validating prerequisites...")

        # Check sample files
        if not MANUSCRIPT_FILE.exists():
            raise FileNotFoundError(f"Manuscript file not found: {MANUSCRIPT_FILE}")
        for af in AUTHOR_SAMPLE_FILES:
            if not af.exists():
                raise FileNotFoundError(f"Author sample file not found: {af}")

        # Resolve workspace and user for the caller block from DB
        self.workspace_id, self.user_id, self.project_id = self._resolve_caller_ids()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        self._emit(f"  Flask server : {self.base_url}")
        self._emit(f"  Manuscript   : {MANUSCRIPT_FILE.name}")
        self._emit(f"  Author files : {[f.name for f in AUTHOR_SAMPLE_FILES]}")
        self._emit(f"  Workspace ID : {self.workspace_id}")
        self._emit(f"  User ID      : {self.user_id}")
        self._emit(f"  Mock LLM     : {self.use_mock_provider}")
        self._emit(f"  Output Dir   : {OUTPUT_DIR}")
        self._emit("")

    def _db_connect(self):
        import psycopg2

        required = ['DB_HOST', 'DB_PORT', 'DB_DATABASE', 'DB_USER', 'DB_PASSWORD']
        missing = [v for v in required if not os.getenv(v)]
        if missing:
            raise EnvironmentError(f"Missing DB env vars: {missing}")

        return psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_DATABASE'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
        )

    def _resolve_caller_ids(self):
        """Fetch a real workspace, user, and project from the database."""
        conn = self._db_connect()
        try:
            with conn.cursor() as cur:
                # Get a workspace that has at least one member
                cur.execute("""
                    SELECT wm.workspace_id, wm.user_id
                    FROM workspace_members wm
                    ORDER BY wm.created_at
                    LIMIT 1
                """)
                row = cur.fetchone()
                if not row:
                    raise RuntimeError(
                        "No workspace_members found. "
                        "Please seed the database before running this test."
                    )
                workspace_id, user_id = str(row[0]), str(row[1])

                # Get or fall back to workspace_id as project_id
                cur.execute("""
                    SELECT id FROM projects
                    WHERE workspace_id = %s
                    LIMIT 1
                """, (workspace_id,))
                proj_row = cur.fetchone()
                project_id = str(proj_row[0]) if proj_row else workspace_id

        finally:
            conn.close()

        return workspace_id, user_id, project_id

    def _fetch_rewritten_story_content(self) -> str:
        """Fetch rewritten story content from final_manuscripts for this draft."""
        if not self.draft_id:
            raise AssertionError("draft_id is empty; cannot fetch rewritten content")

        conn = self._db_connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT final_content
                    FROM final_manuscripts
                    WHERE draft_id = %s
                    ORDER BY generated_at DESC
                    LIMIT 1
                    """,
                    (self.draft_id,),
                )
                row = cur.fetchone()
        finally:
            conn.close()

        if not row or not row[0]:
            raise AssertionError(
                f"No rewritten final_content found in final_manuscripts for draft_id={self.draft_id}"
            )

        content = str(row[0]).strip()
        if not content:
            raise AssertionError(
                f"Rewritten final_content is empty in final_manuscripts for draft_id={self.draft_id}"
            )
        return content

    def _fetch_generated_chapters(self) -> list[dict]:
        """Fetch chapter rows from DB for craft-level assertions."""
        if not self.draft_id:
            raise AssertionError("draft_id is empty; cannot fetch chapter content")

        conn = self._db_connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT chapter_number, title, content, start_scene, end_scene, scene_count
                    FROM chapters
                    WHERE draft_id = %s
                    ORDER BY chapter_number
                    """,
                    (self.draft_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        chapters = []
        for row in rows:
            chapters.append({
                'chapter_number': int(row[0]),
                'title': str(row[1] or ''),
                'content': str(row[2] or ''),
                'start_scene': int(row[3] or 0),
                'end_scene': int(row[4] or 0),
                'scene_count': int(row[5] or 0),
            })
        return chapters

    def _expected_pov_bucket(self) -> str:
        perspective = PIPELINE_CONFIG.get('writing_perspective', 'third_person_limited')
        if perspective == 'first_person':
            return 'first'
        if perspective == 'second_person':
            return 'second'
        return 'third'

    def _pronoun_counts(self, text: str) -> dict:
        tokens = re.findall(r"[a-zA-Z']+", text.lower())
        return {
            'first': sum(1 for t in tokens if t in FIRST_PERSON_PRONOUNS),
            'second': sum(1 for t in tokens if t in SECOND_PERSON_PRONOUNS),
            'third': sum(1 for t in tokens if t in THIRD_PERSON_PRONOUNS),
            'total': len(tokens),
        }

    def _assert_pov_consistency(self, chapters: list[dict]) -> None:
        expected_bucket = self._expected_pov_bucket()
        violations = []

        for ch in chapters:
            counts = self._pronoun_counts(ch.get('content', ''))
            pronoun_total = counts['first'] + counts['second'] + counts['third']
            if pronoun_total < 8:
                continue

            dominant_bucket = max(
                [('first', counts['first']), ('second', counts['second']), ('third', counts['third'])],
                key=lambda x: x[1],
            )[0]
            dominant_ratio = counts[dominant_bucket] / max(pronoun_total, 1)

            if dominant_bucket != expected_bucket and dominant_ratio >= 0.45:
                violations.append(
                    f"Chapter {ch['chapter_number']} dominant POV={dominant_bucket} "
                    f"(ratio={dominant_ratio:.2f}, expected={expected_bucket})"
                )

            if expected_bucket != 'first' and counts['first'] >= 18 and counts['first'] > (counts['third'] + counts['second']):
                violations.append(
                    f"Chapter {ch['chapter_number']} has heavy first-person leakage ({counts['first']} pronouns)"
                )
            if expected_bucket != 'second' and counts['second'] >= 18 and counts['second'] > (counts['first'] + counts['third']):
                violations.append(
                    f"Chapter {ch['chapter_number']} has heavy second-person leakage ({counts['second']} pronouns)"
                )

        if violations:
            raise AssertionError(
                "POV consistency regression detected:\n- " + "\n- ".join(violations[:8])
            )

    def _assert_paragraph_structure(self, full_text: str) -> None:
        paragraphs = [p for p in re.split(r"\n\s*\n", full_text) if p.strip()]
        if len(paragraphs) < 4:
            raise AssertionError(
                f"Paragraph structure regression detected: only {len(paragraphs)} paragraph block(s)."
            )

    def _assert_chapter_scene_integrity(self, chapters: list[dict]) -> None:
        if not chapters:
            raise AssertionError("No chapters available for integrity checks.")

        prev_end = 0
        for ch in chapters:
            start_scene = ch.get('start_scene', 0)
            end_scene = ch.get('end_scene', 0)
            if start_scene <= 0 or end_scene <= 0:
                raise AssertionError(
                    f"Invalid scene bounds in chapter {ch['chapter_number']}: {start_scene}-{end_scene}"
                )
            if start_scene != prev_end + 1:
                raise AssertionError(
                    f"Scene continuity gap/overlap at chapter {ch['chapter_number']}: "
                    f"starts {start_scene}, expected {prev_end + 1}"
                )
            if end_scene < start_scene:
                raise AssertionError(
                    f"Invalid scene range in chapter {ch['chapter_number']}: {start_scene}-{end_scene}"
                )
            prev_end = end_scene

    def _assert_negative_constraints_effective(self, full_text: str) -> None:
        """Best-effort regression check for direct archaizing drift."""
        tokens = re.findall(r"[a-zA-Z']+", full_text.lower())
        archaic_hits = [token for token in tokens if token in ARCHAIC_DIALOGUE_MARKERS]
        if len(archaic_hits) > 2:
            raise AssertionError(
                "Negative-constraint regression detected: archaic dialogue markers leaked into output "
                f"({archaic_hits[:8]})"
            )

    def _is_action_dense(self, text: str) -> bool:
        words = re.findall(r"[a-zA-Z']+", text.lower())
        if not words:
            return False
        hits = sum(1 for w in words if w in ACTION_WORDS)
        return hits >= 3 or (hits / max(len(words), 1)) >= 0.05

    def _has_transition_cue(self, text: str) -> bool:
        return bool(re.search(
            r"\b(later|hours later|days later|meanwhile|afterward|the next|at dawn|by morning|back in)\b",
            text.lower(),
        ))

    def _assert_chapter_boundary_integrity(self, chapters: list[dict]) -> None:
        issues = []
        for idx in range(len(chapters) - 1):
            current_ch = chapters[idx]
            next_ch = chapters[idx + 1]

            current_text = (current_ch.get('content') or '').strip()
            next_text = (next_ch.get('content') or '').strip()
            if not current_text or not next_text:
                continue

            tail = current_text[-240:]
            head = next_text[:240]

            ends_mid_sentence = not re.search(r"[.!?][\"')\\]]?\s*$", current_text)
            ends_with_connector = bool(re.search(r"\b(and|or|but|because|while|as|then|so)\s*$", current_text.lower()))

            if (
                (ends_mid_sentence or ends_with_connector)
                and self._is_action_dense(tail)
                and self._is_action_dense(head)
                and not self._has_transition_cue(head)
            ):
                issues.append(
                    f"Boundary after chapter {current_ch['chapter_number']} appears to split continuous action."
                )

        if len(issues) > 1:
            raise AssertionError(
                "Chapter boundary integrity regression detected:\n- " + "\n- ".join(issues[:6])
            )

    def _assert_mock_source_anchors(self, chapters: list[dict]) -> None:
        failures = []
        for ch in chapters:
            expected_terms = MOCK_CHAPTER_ANCHORS.get(ch.get('chapter_number'))
            if not expected_terms:
                continue

            lowered = (ch.get('content') or '').lower()
            if not any(term in lowered for term in expected_terms):
                failures.append(
                    f"Chapter {ch['chapter_number']} missing expected mock anchors {expected_terms}"
                )

        if failures:
            raise AssertionError(
                "Mock source-anchor regression detected:\n- " + "\n- ".join(failures[:8])
            )

    def _assert_mock_phase_3_improvement(self, completed_status: dict) -> None:
        metadata = completed_status.get('metadata', {}) if isinstance(completed_status, dict) else {}
        diagnostics = metadata.get('diagnostics', {}) if isinstance(metadata, dict) else {}
        phase_3 = diagnostics.get('phase_3', {}) if isinstance(diagnostics, dict) else {}
        stages = phase_3.get('stages_completed', []) if isinstance(phase_3, dict) else []

        improvement_stage = next(
            (stage for stage in stages if stage.get('name') == 'scene_improvement'),
            None,
        )
        if not improvement_stage:
            raise AssertionError(
                f"Mock mode expected scene_improvement stage diagnostics, got: {phase_3}"
            )

        result = improvement_stage.get('result', {}) if isinstance(improvement_stage, dict) else {}
        if not result.get('success', False):
            raise AssertionError(f"Mock mode expected successful scene_improvement stage, got: {result}")
        if int(result.get('chapters_improved', 0) or 0) < 1:
            raise AssertionError(f"Mock mode expected at least one improved chapter, got: {result}")

    def _stage_success(self, stage: dict) -> bool:
        result = stage.get('result', {}) if isinstance(stage, dict) else {}
        if isinstance(result, dict) and 'success' in result:
            return bool(result.get('success'))
        return True

    def _emit_phase_execution_summary(self, completed_status: dict, results_data: dict) -> None:
        metadata = completed_status.get('metadata', {}) if isinstance(completed_status, dict) else {}
        phase_results = (
            results_data.get('phase_results')
            or results_data.get('phase_timings')
            or metadata.get('phase_results')
            or {}
        )
        diagnostics = results_data.get('diagnostics') or metadata.get('diagnostics') or {}

        if not phase_results:
            return

        self._emit("  Phase execution:")
        for phase_key in ("phase_1", "phase_2", "phase_3"):
            info = phase_results.get(phase_key, {})
            if not isinstance(info, dict):
                continue

            ok = bool(info.get('success', False))
            secs = info.get('timing_seconds')
            summary = f"    {phase_key}: {'OK' if ok else 'FAIL'}"
            if isinstance(secs, (int, float)):
                summary += f" in {secs:.1f}s"
            if info.get('skipped'):
                summary += " (skipped)"
            self._emit(summary)

            if phase_key == "phase_1":
                diag = info.get('diagnostics', {}) if isinstance(info.get('diagnostics'), dict) else {}
                stage_rows = ((diag.get('result') or {}).get('stages_completed') or []) if isinstance(diag, dict) else []
                for stage in stage_rows:
                    name = stage.get('name', 'unknown_stage')
                    stage_ok = self._stage_success(stage)
                    self._emit(f"      - {name}: {'OK' if stage_ok else 'FAIL'}")
            elif phase_key == "phase_2":
                diag = info.get('diagnostics', {}) if isinstance(info.get('diagnostics'), dict) else {}
                status = diag.get('status')
                if status:
                    self._emit(f"      - profiling: {status}")
            elif phase_key == "phase_3":
                phase_diag = diagnostics.get('phase_3', {})
                stage_rows = (phase_diag.get('stages_completed') or []) if isinstance(phase_diag, dict) else []
                for stage in stage_rows:
                    name = stage.get('name', 'unknown_stage')
                    stage_ok = self._stage_success(stage)
                    self._emit(f"      - {name}: {'OK' if stage_ok else 'FAIL'}")

    def _assert_phase_execution_details(self, completed_status: dict, results_data: dict) -> None:
        metadata = completed_status.get('metadata', {}) if isinstance(completed_status, dict) else {}
        phase_results = (
            results_data.get('phase_results')
            or results_data.get('phase_timings')
            or metadata.get('phase_results')
            or {}
        )
        diagnostics = results_data.get('diagnostics') or metadata.get('diagnostics') or {}

        for phase_key in ("phase_1", "phase_2", "phase_3"):
            info = phase_results.get(phase_key)
            if not isinstance(info, dict):
                raise AssertionError(f"Missing phase result details for {phase_key}: {phase_results}")
            if info.get('success') is not True:
                raise AssertionError(f"{phase_key} did not report success in phase results: {info}")
            secs = info.get('timing_seconds')
            if not isinstance(secs, (int, float)) or secs < 0:
                raise AssertionError(f"{phase_key} missing valid timing_seconds: {info}")

        phase_1_diag = ((phase_results.get('phase_1', {}).get('diagnostics') or {}).get('result') or {})
        phase_1_stage_rows = phase_1_diag.get('stages_completed') or []
        expected_phase_1 = {
            'ingestion',
            'cleaning',
            'scene_detection',
            'scene_analysis',
            'graph_analysis',
            'comprehensive_reporting',
            'coherence_check',
            'enhancement',
            'chaptering',
        }
        phase_1_names = {stage.get('name') for stage in phase_1_stage_rows if isinstance(stage, dict)}
        missing_phase_1 = expected_phase_1 - phase_1_names
        if missing_phase_1:
            raise AssertionError(f"Phase 1 diagnostics missing stages: {sorted(missing_phase_1)}")

        phase_2_diag = phase_results.get('phase_2', {}).get('diagnostics') or {}
        if phase_2_diag.get('status') != 'profiling_completed':
            raise AssertionError(f"Phase 2 diagnostics missing profiling_completed status: {phase_2_diag}")

        phase_3_diag = diagnostics.get('phase_3') or {}
        phase_3_stage_rows = phase_3_diag.get('stages_completed') or []
        expected_phase_3 = {
            'entity_profiling',
            'prose_generation',
            'quality_assessment',
            'scene_improvement',
            'manuscript_assembly',
        }
        phase_3_names = {stage.get('name') for stage in phase_3_stage_rows if isinstance(stage, dict)}
        missing_phase_3 = expected_phase_3 - phase_3_names
        if missing_phase_3:
            raise AssertionError(f"Phase 3 diagnostics missing stages: {sorted(missing_phase_3)}")

        failed_stages = [
            f"{stage.get('name')}"
            for stage in phase_1_stage_rows + phase_3_stage_rows
            if isinstance(stage, dict) and not self._stage_success(stage)
        ]
        if failed_stages:
            raise AssertionError(f"Pipeline completed but some stages reported failure: {failed_stages}")

    def _run_quality_regression_assertions(self) -> dict:
        """Run craft-level regression assertions on generated prose."""
        rewritten_story = self._fetch_rewritten_story_content()
        chapters = self._fetch_generated_chapters()

        self._assert_paragraph_structure(rewritten_story)
        self._assert_chapter_scene_integrity(chapters)
        self._assert_pov_consistency(chapters)
        self._assert_chapter_boundary_integrity(chapters)
        self._assert_negative_constraints_effective(rewritten_story)
        if self.use_mock_provider:
            self._assert_mock_source_anchors(chapters)

        return {
            'paragraph_blocks': len([p for p in re.split(r"\n\s*\n", rewritten_story) if p.strip()]),
            'chapters_checked': len(chapters),
            'expected_pov': self._expected_pov_bucket(),
        }

    def _export_rewritten_story_pdf(self, rewritten_story: str) -> Path:
        """Write rewritten story to PDF under tests/sample/output."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.utils import simpleSplit
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise RuntimeError(
                "reportlab is required for PDF export in this integration test"
            ) from exc

        input_draft = MANUSCRIPT_FILE.stem
        output_path = OUTPUT_DIR / f"{input_draft}_rewritten_{self.draft_id}.pdf"

        page_width, page_height = A4
        margin_left = 56
        margin_right = 56
        margin_top = 56
        margin_bottom = 56
        line_height = 14
        text_width = page_width - margin_left - margin_right

        pdf = canvas.Canvas(str(output_path), pagesize=A4)
        y = page_height - margin_top

        def ensure_room():
            nonlocal y
            if y < margin_bottom:
                pdf.showPage()
                pdf.setFont("Helvetica", 11)
                y = page_height - margin_top

        pdf.setTitle(f"Rewritten Story - {self.draft_id}")
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(margin_left, y, "Rewritten Story")
        y -= line_height + 2
        pdf.setFont("Helvetica", 10)
        pdf.drawString(margin_left, y, f"Input Draft: {input_draft}")
        y -= line_height
        pdf.drawString(margin_left, y, f"Draft ID: {self.draft_id}")
        y -= (line_height * 2)
        pdf.setFont("Helvetica", 11)

        for raw_line in rewritten_story.splitlines():
            line = raw_line.rstrip()
            if not line:
                y -= line_height
                ensure_room()
                continue

            wrapped_lines = simpleSplit(line, "Helvetica", 11, text_width)
            if not wrapped_lines:
                wrapped_lines = [""]

            for wrapped in wrapped_lines:
                ensure_room()
                pdf.drawString(margin_left, y, wrapped)
                y -= line_height

        pdf.save()
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise AssertionError(f"PDF export failed or produced empty file: {output_path}")
        return output_path

    # ------------------------------------------------------------------
    # Test steps
    # ------------------------------------------------------------------

    def step_health_check(self):
        """Verify the Flask server is reachable."""
        self._emit("Step 1: Health check...")
        resp = requests.get(f"{self.base_url}/health", timeout=10)
        assert resp.status_code == 200, f"Health check failed: {resp.status_code} {resp.text}"
        body = resp.json()
        assert body.get('status') == 'healthy', f"Server not healthy: {body}"
        assert body.get('database') == 'connected', f"DB not connected: {body}"
        self._emit("  Server healthy, DB connected.")

    def step_start_pipeline(self):
        """POST /api/novel-pipeline/start with multipart data."""
        self._emit("Step 2: Starting novel pipeline...")

        config = dict(PIPELINE_CONFIG)
        config['style_analyzer_config'] = dict(PIPELINE_CONFIG.get('style_analyzer_config', {}))
        config['caller'] = {
            'user_id': self.user_id,
            'workspace_id': self.workspace_id,
            'project_id': self.project_id,
        }
        if self.use_mock_provider:
            config['provider'] = 'mock'
            config['model'] = 'mock-replay-v1'
            config['style_analyzer_config']['provider'] = 'mock'
            config['style_analyzer_config']['model'] = 'mock-replay-v1'
            config['style_analyzer_config']['phase_start_delay_seconds'] = 0
            self._emit("  Mock provider enabled; disabling phase-2 start delay.")

        # Build multipart request
        files = []
        ms_handle = open(MANUSCRIPT_FILE, 'rb')
        files.append(('manuscript_file', (MANUSCRIPT_FILE.name, ms_handle, 'application/pdf')))

        author_handles = []
        for af in AUTHOR_SAMPLE_FILES:
            fh = open(af, 'rb')
            author_handles.append(fh)
            files.append(('author_files', (af.name, fh, 'application/pdf')))

        data_field = {'data': json.dumps(config)}

        try:
            resp = requests.post(
                f"{self.base_url}/api/novel-pipeline/start",
                files=files,
                data=data_field,
                timeout=60,
            )
        finally:
            ms_handle.close()
            for fh in author_handles:
                fh.close()

        self._emit(f"  Response status: {resp.status_code}")
        if resp.status_code != 202:
            self._emit(f"  Response body: {resp.text}")
        assert resp.status_code == 202, (
            f"Expected 202, got {resp.status_code}: {resp.text}"
        )

        body = resp.json()
        assert body.get('success') is True, f"Expected success=true: {body}"

        data_out = body.get('data', {})
        self.pipeline_run_id = data_out.get('pipeline_run_id', '')
        self.draft_id = data_out.get('draft_id', '')

        assert self.pipeline_run_id, f"No pipeline_run_id in response: {body}"
        assert self.draft_id, f"No draft_id in response: {body}"

        self._emit("  Pipeline started:")
        self._emit(f"    pipeline_run_id = {self.pipeline_run_id}")
        self._emit(f"    draft_id        = {self.draft_id}")

    def step_poll_status(self):
        """
        Poll GET /api/novel-pipeline/status/<run_id> until completion or timeout.
        Prints progress updates as phases transition.
        """
        self._emit("Step 3: Polling pipeline status...")
        timeout = MOCK_POLL_TIMEOUT if self.use_mock_provider else POLL_TIMEOUT
        interval = MOCK_POLL_INTERVAL if self.use_mock_provider else POLL_INTERVAL
        self._emit(f"  Timeout: {timeout}s, interval: {interval}s")
        self._emit("")

        start = time.time()
        last_status = None
        last_phases = {}
        last_progress_at = start
        last_heartbeat_at = start

        while True:
            elapsed = time.time() - start
            if elapsed > timeout:
                raise TimeoutError(
                    f"Pipeline did not complete within {timeout}s. "
                    f"Last status: {last_status}"
                )

            resp = requests.get(
                f"{self.base_url}/api/novel-pipeline/status/{self.pipeline_run_id}",
                params={'user_id': self.user_id},
                timeout=30,
            )
            assert resp.status_code == 200, (
                f"Status endpoint returned {resp.status_code}: {resp.text}"
            )

            body = resp.json()
            data = body.get('data', {})
            status = data.get('status', 'unknown')
            pct = data.get('overall_percentage', 0)
            phases = data.get('phases', {})

            # Print update when something changes
            phase_statuses = {k: v.get('status') for k, v in phases.items()}
            if status != last_status or phase_statuses != last_phases:
                ts = datetime.now().strftime('%H:%M:%S')
                self._emit(
                    f"  [{ts}] {status:25s} {pct:3d}%  |  "
                    f"P1={phase_statuses.get('phase_1','?'):10s}  "
                    f"P2={phase_statuses.get('phase_2','?'):10s}  "
                    f"P3={phase_statuses.get('phase_3','?'):10s}"
                )
                last_status = status
                last_phases = phase_statuses
                last_progress_at = time.time()

            if (time.time() - last_heartbeat_at) >= POLL_HEARTBEAT_SECONDS:
                stalled_for = time.time() - last_progress_at
                self._emit(
                    f"  Waiting... elapsed={elapsed:.1f}s, current_status={status}, "
                    f"unchanged_for={stalled_for:.1f}s"
                )
                last_heartbeat_at = time.time()

            if status == 'completed':
                self._emit("")
                self._emit(f"  Pipeline completed in {elapsed:.1f}s")
                return data

            if status == 'failed':
                err = data.get('error_message', 'unknown error')
                failed_phase = data.get('failed_phase')
                raise AssertionError(
                    f"Pipeline failed at phase {failed_phase}: {err}\n"
                    f"Full status: {json.dumps(data, indent=2, default=str)}"
                )

            time.sleep(interval)

    def step_validate_results(self, completed_status: dict):
        """GET /api/novel-pipeline/results/<run_id> and validate output."""
        self._emit("Step 4: Fetching and validating results...")

        resp = requests.get(
            f"{self.base_url}/api/novel-pipeline/results/{self.pipeline_run_id}",
            params={'user_id': self.user_id},
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Results endpoint returned {resp.status_code}: {resp.text}"
        )

        body = resp.json()
        assert body.get('success') is True, f"Expected success=true: {body}"

        data = body.get('data', {})

        # Core ID checks
        assert data.get('pipeline_run_id') == self.pipeline_run_id
        assert data.get('draft_id') == self.draft_id
        assert data.get('author_name') == PIPELINE_CONFIG['author_name']

        results = data.get('results', {})

        # Manuscript must exist
        manuscript = results.get('manuscript')
        assert manuscript, f"No manuscript in results: {results}"
        assert manuscript.get('word_count', 0) > 0, "Manuscript has 0 words"

        # Chapters must exist
        chapter_count = results.get('chapter_count', 0)
        assert chapter_count > 0, f"Expected chapters, got {chapter_count}"

        # Author style must be linked
        author_style = results.get('author_style')
        assert author_style, f"No author_style in results: {results}"
        assert author_style.get('author_name') == PIPELINE_CONFIG['author_name']

        self._emit("  Results validated:")
        self._emit(f"    Chapters      : {chapter_count}")
        self._emit(f"    Word count    : {manuscript.get('word_count')}")
        self._emit(f"    Scene count   : {results.get('scene_count', 0)}")
        self._emit(f"    Plot issues   : {results.get('plot_issues', {})}")
        self._emit(f"    Author style  : {author_style.get('author_name')} ({author_style.get('status')})")

        self._assert_phase_execution_details(completed_status, data)
        self._emit_phase_execution_summary(completed_status, data)

        quality_stats = self._run_quality_regression_assertions()
        if self.use_mock_provider:
            self._assert_mock_phase_3_improvement(completed_status)
        self._emit("  Craft quality assertions passed:")
        self._emit(f"    Paragraphs    : {quality_stats['paragraph_blocks']}")
        self._emit(f"    POV expected  : {quality_stats['expected_pov']}")
        self._emit(f"    Chapters check: {quality_stats['chapters_checked']}")

        return data

    def step_export_rewritten_story_pdf(self):
        """Fetch rewritten story from DB and export as PDF artifact."""
        self._emit("Step 5: Exporting rewritten story to PDF...")
        rewritten_story = self._fetch_rewritten_story_content()
        output_path = self._export_rewritten_story_pdf(rewritten_story)
        self.output_pdf_path = output_path
        self._emit(f"  Rewritten PDF : {output_path}")

    # ------------------------------------------------------------------
    # Negative / edge-case tests
    # ------------------------------------------------------------------

    def step_test_status_not_ready(self):
        """
        Test that /results returns 409 while pipeline is still running.
        (Only valid if called during the run — this is a best-effort check
        included for documentation; in the full E2E it runs before the
        pipeline completes.)
        """
        # This is only meaningful if called while still running.
        # We skip it here since we call after completion, but the code
        # is included so it can be adapted for a faster test loop.
        pass

    def step_test_invalid_run_id(self):
        """Test that a bogus run_id returns 404."""
        self._emit("Step 6: Testing error handling (invalid run_id)...")
        fake_id = "01JNOTALIDULID0000000000000"
        resp = requests.get(
            f"{self.base_url}/api/novel-pipeline/status/{fake_id}",
            params={'user_id': self.user_id},
            timeout=10,
        )
        assert resp.status_code == 404, (
            f"Expected 404 for unknown run_id, got {resp.status_code}"
        )
        self._emit("  404 returned for unknown run_id — correct.")

    def step_test_missing_files(self):
        """Test that omitting required files returns 400."""
        self._emit("Step 7: Testing validation (missing manuscript_file)...")
        config = dict(PIPELINE_CONFIG)
        config['caller'] = {
            'user_id': self.user_id,
            'workspace_id': self.workspace_id,
            'project_id': self.project_id,
        }
        # Send without any files
        resp = requests.post(
            f"{self.base_url}/api/novel-pipeline/start",
            data={'data': json.dumps(config)},
            timeout=15,
        )
        assert resp.status_code in (400, 422), (
            f"Expected 400/422 for missing files, got {resp.status_code}: {resp.text}"
        )
        self._emit(f"  {resp.status_code} returned for missing manuscript — correct.")

    def step_test_missing_data(self):
        """Test that omitting the data field returns 400."""
        self._emit("Step 8: Testing validation (missing data field)...")
        with open(MANUSCRIPT_FILE, 'rb') as fh:
            resp = requests.post(
                f"{self.base_url}/api/novel-pipeline/start",
                files={'manuscript_file': (MANUSCRIPT_FILE.name, fh, 'application/pdf')},
                timeout=15,
            )
        assert resp.status_code in (400, 422), (
            f"Expected 400/422 for missing data, got {resp.status_code}: {resp.text}"
        )
        self._emit(f"  {resp.status_code} returned for missing data — correct.")

    # ------------------------------------------------------------------
    # Main runner
    # ------------------------------------------------------------------

    def run(self, skip_pipeline: bool = False):
        """
        Execute all test steps in order.

        Args:
            skip_pipeline: If True, skip the long-running pipeline and only
                           run the error-handling / validation steps. Useful
                           for quick smoke tests when you already have a run_id.
        """
        start_time = datetime.now()

        self._emit("=" * 70)
        self._emit("  RUNARION — NOVEL PIPELINE ORCHESTRATOR — E2E INTEGRATION TEST")
        self._emit("=" * 70)
        self._emit("")

        try:
            self.step_health_check()
            self._emit("")

            if skip_pipeline:
                self._emit("Skipping full pipeline run (skip_pipeline=True).")
            else:
                self.step_start_pipeline()
                self._emit("")
                completed_status = self.step_poll_status()
                self._emit("")
                self.step_validate_results(completed_status)
                self._emit("")
                self.step_export_rewritten_story_pdf()
                self._emit("")

            # Validation / negative tests (fast, no LLM calls)
            self.step_test_invalid_run_id()
            self._emit("")
            self.step_test_missing_files()
            self._emit("")
            self.step_test_missing_data()
            self._emit("")

            elapsed = (datetime.now() - start_time).total_seconds()
            self._emit("=" * 70)
            self._emit(f"  ALL TESTS PASSED  ({elapsed:.1f}s / {elapsed/60:.1f}min)")
            self._emit("=" * 70)

            if self.pipeline_run_id:
                self._emit("")
                self._emit("Useful IDs for manual inspection:")
                self._emit(f"  pipeline_run_id = {self.pipeline_run_id}")
                self._emit(f"  draft_id        = {self.draft_id}")
                if self.output_pdf_path:
                    self._emit(f"  rewritten_pdf   = {self.output_pdf_path}")

            return True

        except (AssertionError, TimeoutError, Exception) as exc:
            elapsed = (datetime.now() - start_time).total_seconds()
            self._emit("")
            self._emit("=" * 70)
            self._emit(f"  TEST FAILED  ({elapsed:.1f}s)")
            self._emit("=" * 70)
            self._emit(f"  Error: {exc}")
            import traceback
            traceback.print_exc()
            return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    global FLASK_BASE_URL
    import argparse
    parser = argparse.ArgumentParser(description="Novel Pipeline E2E Integration Test")
    parser.add_argument(
        '--skip-pipeline',
        action='store_true',
        help='Skip the full LLM pipeline run; only run fast validation tests',
    )
    parser.add_argument(
        '--url',
        default=None,
        help=f'Flask server base URL (default: {FLASK_BASE_URL})',
    )
    parser.add_argument(
        '--mock-llm-provider',
        action='store_true',
        help='Use the internal mock provider instead of external LLM APIs.',
    )
    args = parser.parse_args()

    if args.url:
        FLASK_BASE_URL = args.url

    test = NovelPipelineE2ETest(use_mock_provider=args.mock_llm_provider)
    success = test.run(skip_pipeline=args.skip_pipeline)
    sys.exit(0 if success else 1)


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.slow
def test_novel_pipeline_e2e(pytestconfig):
    test = NovelPipelineE2ETest(
        use_mock_provider=bool(pytestconfig.getoption("--mock-llm-provider")),
        pytest_mode=True,
    )
    assert test.run(skip_pipeline=False) is True


if __name__ == '__main__':
    main()
