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
  1. Flask server must be running:  python src/app.py
  2. PostgreSQL must be running with migrations applied
  3. .env must be configured with DB credentials and at least one LLM API key
  4. UPLOAD_PATH directory must be writable by the Flask process

CONFIGURATION:
  Edit the CONFIG block below to point to your sample files and server.
  The manuscript and author sample can be the same file for a quick smoke test.
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup so we can import from src/ when run directly
# ---------------------------------------------------------------------------
TEST_DIR = Path(__file__).parent
REPO_ROOT = TEST_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / 'src'))

from dotenv import load_dotenv
load_dotenv(dotenv_path=REPO_ROOT / '.env')

import requests

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
    "style_analyzer_config": {
        "min_success_samples": 0.5,
        "min_success_partial_style": 0.5,
    },
}

# How long to poll before giving up (seconds)
POLL_TIMEOUT = 60 * 45   # 45 minutes
POLL_INTERVAL = 15       # check every 15 seconds
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


class NovelPipelineE2ETest:
    """
    End-to-end test runner for the novel pipeline orchestrator API.
    Sends real HTTP requests to a running Flask server.
    """

    def __init__(self):
        self.base_url = FLASK_BASE_URL.rstrip('/')
        self.pipeline_run_id: str = ''
        self.draft_id: str = ''
        self.output_pdf_path: Optional[Path] = None
        self._validate_prerequisites()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _validate_prerequisites(self):
        print("Validating prerequisites...")

        # Check sample files
        if not MANUSCRIPT_FILE.exists():
            raise FileNotFoundError(f"Manuscript file not found: {MANUSCRIPT_FILE}")
        for af in AUTHOR_SAMPLE_FILES:
            if not af.exists():
                raise FileNotFoundError(f"Author sample file not found: {af}")

        # Resolve workspace and user for the caller block from DB
        self.workspace_id, self.user_id, self.project_id = self._resolve_caller_ids()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        print(f"  Flask server : {self.base_url}")
        print(f"  Manuscript   : {MANUSCRIPT_FILE.name}")
        print(f"  Author files : {[f.name for f in AUTHOR_SAMPLE_FILES]}")
        print(f"  Workspace ID : {self.workspace_id}")
        print(f"  User ID      : {self.user_id}")
        print(f"  Output Dir   : {OUTPUT_DIR}")
        print()

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

    def _run_quality_regression_assertions(self) -> dict:
        """Run craft-level regression assertions on generated prose."""
        rewritten_story = self._fetch_rewritten_story_content()
        chapters = self._fetch_generated_chapters()

        self._assert_paragraph_structure(rewritten_story)
        self._assert_chapter_scene_integrity(chapters)
        self._assert_pov_consistency(chapters)
        self._assert_chapter_boundary_integrity(chapters)

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
        print("Step 1: Health check...")
        resp = requests.get(f"{self.base_url}/health", timeout=10)
        assert resp.status_code == 200, f"Health check failed: {resp.status_code} {resp.text}"
        body = resp.json()
        assert body.get('status') == 'healthy', f"Server not healthy: {body}"
        assert body.get('database') == 'connected', f"DB not connected: {body}"
        print(f"  Server healthy, DB connected.")

    def step_start_pipeline(self):
        """POST /api/novel-pipeline/start with multipart data."""
        print("Step 2: Starting novel pipeline...")

        config = dict(PIPELINE_CONFIG)
        config['caller'] = {
            'user_id': self.user_id,
            'workspace_id': self.workspace_id,
            'project_id': self.project_id,
        }

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

        print(f"  Response status: {resp.status_code}")
        if resp.status_code != 202:
            print(f"  Response body: {resp.text}")
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

        print(f"  Pipeline started:")
        print(f"    pipeline_run_id = {self.pipeline_run_id}")
        print(f"    draft_id        = {self.draft_id}")

    def step_poll_status(self):
        """
        Poll GET /api/novel-pipeline/status/<run_id> until completion or timeout.
        Prints progress updates as phases transition.
        """
        print("Step 3: Polling pipeline status...")
        print(f"  Timeout: {POLL_TIMEOUT}s, interval: {POLL_INTERVAL}s")
        print()

        start = time.time()
        last_status = None
        last_phases = {}

        while True:
            elapsed = time.time() - start
            if elapsed > POLL_TIMEOUT:
                raise TimeoutError(
                    f"Pipeline did not complete within {POLL_TIMEOUT}s. "
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
                print(f"  [{ts}] {status:25s} {pct:3d}%  |  "
                      f"P1={phase_statuses.get('phase_1','?'):10s}  "
                      f"P2={phase_statuses.get('phase_2','?'):10s}  "
                      f"P3={phase_statuses.get('phase_3','?'):10s}")
                last_status = status
                last_phases = phase_statuses

            if status == 'completed':
                print()
                print(f"  Pipeline completed in {elapsed:.1f}s")
                return data

            if status == 'failed':
                err = data.get('error_message', 'unknown error')
                failed_phase = data.get('failed_phase')
                raise AssertionError(
                    f"Pipeline failed at phase {failed_phase}: {err}\n"
                    f"Full status: {json.dumps(data, indent=2, default=str)}"
                )

            time.sleep(POLL_INTERVAL)

    def step_validate_results(self, completed_status: dict):
        """GET /api/novel-pipeline/results/<run_id> and validate output."""
        print("Step 4: Fetching and validating results...")

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

        print(f"  Results validated:")
        print(f"    Chapters      : {chapter_count}")
        print(f"    Word count    : {manuscript.get('word_count')}")
        print(f"    Scene count   : {results.get('scene_count', 0)}")
        print(f"    Plot issues   : {results.get('plot_issues', {})}")
        print(f"    Author style  : {author_style.get('author_name')} ({author_style.get('status')})")

        # Print phase timings if available
        timings = data.get('phase_timings', {})
        if timings:
            print(f"\n  Phase timings:")
            for phase, info in timings.items():
                secs = info.get('timing_seconds', 0)
                ok = info.get('success', False)
                print(f"    {phase}: {'OK' if ok else 'FAIL'} in {secs:.1f}s")

        quality_stats = self._run_quality_regression_assertions()
        print(f"\n  Craft quality assertions passed:")
        print(f"    Paragraphs    : {quality_stats['paragraph_blocks']}")
        print(f"    POV expected  : {quality_stats['expected_pov']}")
        print(f"    Chapters check: {quality_stats['chapters_checked']}")

        return data

    def step_export_rewritten_story_pdf(self):
        """Fetch rewritten story from DB and export as PDF artifact."""
        print("Step 5: Exporting rewritten story to PDF...")
        rewritten_story = self._fetch_rewritten_story_content()
        output_path = self._export_rewritten_story_pdf(rewritten_story)
        self.output_pdf_path = output_path
        print(f"  Rewritten PDF : {output_path}")

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
        print("Step 6: Testing error handling (invalid run_id)...")
        fake_id = "01JNOTALIDULID0000000000000"
        resp = requests.get(
            f"{self.base_url}/api/novel-pipeline/status/{fake_id}",
            params={'user_id': self.user_id},
            timeout=10,
        )
        assert resp.status_code == 404, (
            f"Expected 404 for unknown run_id, got {resp.status_code}"
        )
        print(f"  404 returned for unknown run_id — correct.")

    def step_test_missing_files(self):
        """Test that omitting required files returns 400."""
        print("Step 7: Testing validation (missing manuscript_file)...")
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
        print(f"  {resp.status_code} returned for missing manuscript — correct.")

    def step_test_missing_data(self):
        """Test that omitting the data field returns 400."""
        print("Step 8: Testing validation (missing data field)...")
        with open(MANUSCRIPT_FILE, 'rb') as fh:
            resp = requests.post(
                f"{self.base_url}/api/novel-pipeline/start",
                files={'manuscript_file': (MANUSCRIPT_FILE.name, fh, 'application/pdf')},
                timeout=15,
            )
        assert resp.status_code in (400, 422), (
            f"Expected 400/422 for missing data, got {resp.status_code}: {resp.text}"
        )
        print(f"  {resp.status_code} returned for missing data — correct.")

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

        print("=" * 70)
        print("  RUNARION — NOVEL PIPELINE ORCHESTRATOR — E2E INTEGRATION TEST")
        print("=" * 70)
        print()

        try:
            self.step_health_check()
            print()

            # Validation / negative tests (fast, no LLM calls)
            self.step_test_invalid_run_id()
            print()
            self.step_test_missing_files()
            print()
            self.step_test_missing_data()
            print()

            if skip_pipeline:
                print("Skipping full pipeline run (skip_pipeline=True).")
            else:
                self.step_start_pipeline()
                print()
                completed_status = self.step_poll_status()
                print()
                self.step_validate_results(completed_status)
                print()
                self.step_export_rewritten_story_pdf()
                print()

            elapsed = (datetime.now() - start_time).total_seconds()
            print("=" * 70)
            print(f"  ALL TESTS PASSED  ({elapsed:.1f}s / {elapsed/60:.1f}min)")
            print("=" * 70)

            if self.pipeline_run_id:
                print()
                print("Useful IDs for manual inspection:")
                print(f"  pipeline_run_id = {self.pipeline_run_id}")
                print(f"  draft_id        = {self.draft_id}")
                if self.output_pdf_path:
                    print(f"  rewritten_pdf   = {self.output_pdf_path}")

            return True

        except (AssertionError, TimeoutError, Exception) as exc:
            elapsed = (datetime.now() - start_time).total_seconds()
            print()
            print("=" * 70)
            print(f"  TEST FAILED  ({elapsed:.1f}s)")
            print("=" * 70)
            print(f"  Error: {exc}")
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
    args = parser.parse_args()

    if args.url:
        FLASK_BASE_URL = args.url

    test = NovelPipelineE2ETest()
    success = test.run(skip_pipeline=args.skip_pipeline)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
