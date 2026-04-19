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
import sys
import time
from datetime import datetime
from pathlib import Path

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
    "max_improvement_passes": 1,
    "on_exist": "update",
    "style_analyzer_config": {
        "min_success_samples": 0.5,
        "min_success_partial_style": 0.5,
    },
}

# How long to poll before giving up (seconds)
POLL_TIMEOUT = 60 * 30   # 30 minutes
POLL_INTERVAL = 15       # check every 15 seconds
# ---------------------------------------------------------------------------


class NovelPipelineE2ETest:
    """
    End-to-end test runner for the novel pipeline orchestrator API.
    Sends real HTTP requests to a running Flask server.
    """

    def __init__(self):
        self.base_url = FLASK_BASE_URL.rstrip('/')
        self.pipeline_run_id: str = ''
        self.draft_id: str = ''
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

        print(f"  Flask server : {self.base_url}")
        print(f"  Manuscript   : {MANUSCRIPT_FILE.name}")
        print(f"  Author files : {[f.name for f in AUTHOR_SAMPLE_FILES]}")
        print(f"  Workspace ID : {self.workspace_id}")
        print(f"  User ID      : {self.user_id}")
        print()

    def _resolve_caller_ids(self):
        """Fetch a real workspace, user, and project from the database."""
        import psycopg2

        required = ['DB_HOST', 'DB_PORT', 'DB_DATABASE', 'DB_USER', 'DB_PASSWORD']
        missing = [v for v in required if not os.getenv(v)]
        if missing:
            raise EnvironmentError(f"Missing DB env vars: {missing}")

        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_DATABASE'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
        )
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

        return data

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
        print("Step 5: Testing error handling (invalid run_id)...")
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
        print("Step 6: Testing validation (missing manuscript_file)...")
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
        print("Step 7: Testing validation (missing data field)...")
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

            elapsed = (datetime.now() - start_time).total_seconds()
            print("=" * 70)
            print(f"  ALL TESTS PASSED  ({elapsed:.1f}s / {elapsed/60:.1f}min)")
            print("=" * 70)

            if self.pipeline_run_id:
                print()
                print("Useful IDs for manual inspection:")
                print(f"  pipeline_run_id = {self.pipeline_run_id}")
                print(f"  draft_id        = {self.draft_id}")

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
