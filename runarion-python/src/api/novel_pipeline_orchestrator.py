"""
API endpoints for the full novel pipeline orchestrator.

Orchestrates all 3 phases of the novel generation pipeline:
  Phase 1: Deconstructor  — analyzes and deconstructs the source manuscript
  Phase 2: Style Analyzer — profiles the author's writing voice from sample files
  Phase 3: Novel Writer   — rewrites the source material in the author's voice

Phases 1 and 2 run concurrently (they are independent). Phase 3 runs only
after both have completed successfully.

File handling strategy:
  The manuscript file and author sample files are accepted as multipart uploads
  in a single request. The Python service saves them to its own UPLOAD_PATH
  volume. When the Laravel controller is built it will forward the user's files
  to this endpoint via a multipart HTTP request — no shared filesystem required.

Endpoints:
  POST /api/novel-pipeline/start           — upload files + kick off all 3 phases
  GET  /api/novel-pipeline/status/<run_id> — combined progress across all phases
  GET  /api/novel-pipeline/results/<run_id>— final results once pipeline completes
"""

import json
import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

import ulid as ulid_lib
from flask import Blueprint, current_app, jsonify, request
from psycopg2.pool import SimpleConnectionPool
from pydantic import BaseModel, ValidationError
from werkzeug.utils import secure_filename

from models.deconstructor.status import DraftStatus
from models.request import BaseGenerationRequest, CallerInfo, GenerationConfig
from services.deconstructor.orchestrator import DeconstructorOrchestrator
from services.generation_engine import GenerationEngine
from services.novel_writer.orchestrator import NovelWriterOrchestrator
from services.style_analyzer import ProfilingStage, SamplingStage, StyleAnalyzerOrchestrator
from utils.api_response import (
    ApiResponse,
    error,
    internal_error,
    validation_error,
)

logger = logging.getLogger(__name__)

novel_pipeline = Blueprint("novel_pipeline", __name__)

# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class PipelineCallerData(BaseModel):
    user_id: str
    workspace_id: str
    project_id: str


class StyleAnalyzerConfig(BaseModel):
    min_success_samples: Optional[float] = None
    min_success_partial_style: Optional[float] = None
    max_output_tokens: Optional[int] = None


class PipelineStartRequest(BaseModel):
    caller: PipelineCallerData
    author_name: str
    provider: str = "gemini"
    model: str = "gemini-2.5-flash"
    # Deconstructor options
    chaptering_mode: str = "flexible"
    target_chapter_length: int = 2500
    # Novel writer options
    quality_threshold: float = 6.0
    max_improvement_passes: int = 2
    writing_perspective: str = "third_person_limited"
    enforce_hard_quality_gate: bool = True
    hard_quality_threshold: Optional[float] = None
    # Style analyzer options
    style_analyzer_config: StyleAnalyzerConfig = StyleAnalyzerConfig()
    # High-level style source selection (maps to on_exist behavior)
    # - create_or_update -> on_exist=update
    # - use_existing     -> on_exist=get
    author_style_mode: Optional[str] = None
    # Whether to update the author style if it already exists
    on_exist: str = "update"
    generation_config: dict = {}


WRITING_PERSPECTIVE_ALIASES = {
    "first_person": "first_person",
    "1st_person": "first_person",
    "1st person": "first_person",
    "first person": "first_person",
    "second_person": "second_person",
    "2nd_person": "second_person",
    "2nd person": "second_person",
    "second person": "second_person",
    "third_person_limited": "third_person_limited",
    "3rd_person_limited": "third_person_limited",
    "3rd person limited": "third_person_limited",
    "third person limited": "third_person_limited",
    "third_person_omniscient": "third_person_omniscient",
    "3rd_person_omniscient": "third_person_omniscient",
    "3rd person omniscient": "third_person_omniscient",
    "third person omniscient": "third_person_omniscient",
}

AUTHOR_STYLE_MODE_ALIASES = {
    "create_or_update": "create_or_update",
    "create": "create_or_update",
    "update": "create_or_update",
    "use_existing": "use_existing",
    "existing": "use_existing",
    "get": "use_existing",
}


def _normalize_writing_perspective(value: str) -> Optional[str]:
    if not value:
        return None
    key = value.strip().lower().replace("-", "_")
    return WRITING_PERSPECTIVE_ALIASES.get(key)


def _normalize_author_style_mode(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    key = value.strip().lower().replace("-", "_")
    return AUTHOR_STYLE_MODE_ALIASES.get(key)


# ---------------------------------------------------------------------------
# DB helpers — pipeline_runs table
# ---------------------------------------------------------------------------

def _create_pipeline_run(conn, run_id: str, draft_id: str, workspace_id: str,
                          user_id: str, author_name: str, config: dict) -> None:
    """Insert a new pipeline_runs row."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO pipeline_runs (
                id, draft_id, workspace_id, user_id,
                author_name, status,
                phase_1_status, phase_2_status, phase_3_status,
                config, started_at, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, NOW(), NOW(), NOW()
            )
        """, (
            run_id, draft_id, workspace_id, user_id,
            author_name, 'pending',
            'pending', 'pending', 'pending',
            json.dumps(config),
        ))


def _update_pipeline_run(conn, run_id: str, **fields) -> None:
    """
    Update arbitrary columns on a pipeline_runs row.
    Supported keyword args: status, current_phase, phase_1_status,
    phase_2_status, phase_3_status, author_style_id, error_message,
    failed_phase, completed_at, metadata.
    """
    allowed = {
        'status', 'current_phase', 'phase_1_status', 'phase_2_status',
        'phase_3_status', 'author_style_id', 'error_message',
        'failed_phase', 'completed_at', 'metadata',
    }
    sets, vals = [], []
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k == 'metadata' and isinstance(v, dict):
            v = json.dumps(v)
        sets.append(f"{k} = %s")
        vals.append(v)
    if not sets:
        return
    sets.append("updated_at = NOW()")
    vals.append(run_id)
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE pipeline_runs SET {', '.join(sets)} WHERE id = %s",
            vals,
        )


def _get_pipeline_run(conn, run_id: str) -> Optional[dict]:
    """Fetch a pipeline_runs row as a dict."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, draft_id, workspace_id, user_id,
                   author_style_id, author_name, status, current_phase,
                   phase_1_status, phase_2_status, phase_3_status,
                   config, error_message, failed_phase,
                   started_at, completed_at, metadata
            FROM pipeline_runs
            WHERE id = %s AND deleted_at IS NULL
        """, (run_id,))
        row = cur.fetchone()
    if not row:
        return None
    keys = [
        'id', 'draft_id', 'workspace_id', 'user_id',
        'author_style_id', 'author_name', 'status', 'current_phase',
        'phase_1_status', 'phase_2_status', 'phase_3_status',
        'config', 'error_message', 'failed_phase',
        'started_at', 'completed_at', 'metadata',
    ]
    return dict(zip(keys, row))


# ---------------------------------------------------------------------------
# Background orchestration logic
# ---------------------------------------------------------------------------

def _run_phase_1(draft_id: str, manuscript_filename: str,
                 chaptering_mode: str, target_chapter_length: int,
                 provider: str, model: str,
                 user_id: str, workspace_id: str, project_id: str,
                 db_pool: SimpleConnectionPool,
                 run_id: str, flask_app) -> dict:
    """
    Execute Phase 1 (Deconstructor). Runs in its own thread.
    Returns a result dict with keys: success, error, timing_seconds.
    """
    started = datetime.now()
    conn = db_pool.getconn()
    try:
        _update_pipeline_run(conn, run_id, phase_1_status='running')
        conn.commit()
    finally:
        db_pool.putconn(conn)

    try:
        with flask_app.app_context():
            caller = CallerInfo(
                user_id=str(user_id),
                workspace_id=workspace_id,
                project_id=project_id,
                api_keys={},
                session_id=str(uuid.uuid4()),
            )
            generation_request = BaseGenerationRequest(
                prompt="",
                provider=provider,
                model=model,
                caller=caller,
                generation_config=GenerationConfig(),
            )
            engine = GenerationEngine(generation_request)
            orchestrator = DeconstructorOrchestrator(
                generation_engine=engine,
                db_pool=db_pool,
            )
            result = orchestrator.run_pipeline(
                draft_id=draft_id,
                file_name=manuscript_filename,
                chaptering_mode=chaptering_mode,
                target_chapter_length=target_chapter_length,
            )
        elapsed = (datetime.now() - started).total_seconds()

        conn = db_pool.getconn()
        try:
            phase_status = 'completed' if result.get('success') else 'failed'
            _update_pipeline_run(conn, run_id, phase_1_status=phase_status)
            conn.commit()
        finally:
            db_pool.putconn(conn)

        return {
            'success': result.get('success', False),
            'error': result.get('error'),
            'timing_seconds': elapsed,
        }

    except Exception as exc:
        elapsed = (datetime.now() - started).total_seconds()
        logger.error(f"[Pipeline {run_id}] Phase 1 raised exception: {exc}", exc_info=True)
        conn = db_pool.getconn()
        try:
            _update_pipeline_run(conn, run_id, phase_1_status='failed')
            conn.commit()
        finally:
            db_pool.putconn(conn)
        return {'success': False, 'error': str(exc), 'timing_seconds': elapsed}


PHASE_2_START_DELAY_SECONDS = 30
"""
Seconds to wait before Phase 2 begins making LLM calls.
Phase 1 (Deconstructor) fires a burst of calls at t=0 (ingestion + cleaning chunks).
Delaying Phase 2 avoids both hitting the free-tier 20 RPM limit simultaneously.
Raise this value if you still see 429s; lower it (or set to 0) on a paid API key
with higher RPM limits.
"""


def _run_phase_2(author_name: str, file_paths: list,
                 caller: CallerInfo, style_config: StyleAnalyzerConfig,
                 on_exist: str, db_pool: SimpleConnectionPool,
                 run_id: str, flask_app) -> dict:
    """
    Execute Phase 2 (Style Analyzer). Runs in its own thread.
    Returns a result dict with keys: success, error, author_style_id, timing_seconds.

    Starts PHASE_2_START_DELAY_SECONDS after being spawned to avoid a simultaneous
    burst of LLM calls with Phase 1, which would exhaust the shared API quota.
    """
    import time
    started = datetime.now()
    conn = db_pool.getconn()
    try:
        _update_pipeline_run(conn, run_id, phase_2_status='running')
        conn.commit()
    finally:
        db_pool.putconn(conn)

    if PHASE_2_START_DELAY_SECONDS > 0:
        logger.info(
            f"[Pipeline {run_id}] Phase 2 delaying {PHASE_2_START_DELAY_SECONDS}s "
            f"to stagger API calls with Phase 1"
        )
        time.sleep(PHASE_2_START_DELAY_SECONDS)

    try:
        with flask_app.app_context():
            orchestrator = StyleAnalyzerOrchestrator(
                db_pool,
                SamplingStage(
                    db_pool=db_pool,
                    min_success_samples=style_config.min_success_samples,
                ),
                ProfilingStage(
                    db_pool=db_pool,
                    max_output_tokens=style_config.max_output_tokens,
                    min_success_partial_style=style_config.min_success_partial_style,
                ),
            )

            try:
                author_style_id, existing_style = orchestrator.check_and_clean(
                    author_name=author_name,
                    caller=caller,
                    on_exist=on_exist,
                )
            except ValueError as ve:
                elapsed = (datetime.now() - started).total_seconds()
                conn = db_pool.getconn()
                try:
                    _update_pipeline_run(conn, run_id, phase_2_status='failed')
                    conn.commit()
                finally:
                    db_pool.putconn(conn)
                return {'success': False, 'error': str(ve), 'author_style_id': None,
                        'timing_seconds': elapsed}

            # If on_exist='get' and style already exists, treat as success
            if on_exist == 'get' and existing_style:
                elapsed = (datetime.now() - started).total_seconds()
                conn = db_pool.getconn()
                try:
                    _update_pipeline_run(conn, run_id,
                                         phase_2_status='completed',
                                         author_style_id=author_style_id)
                    conn.commit()
                finally:
                    db_pool.putconn(conn)
                return {'success': True, 'error': None,
                        'author_style_id': author_style_id,
                        'timing_seconds': elapsed}

            result = orchestrator.run_pipeline(
                author_style_id=author_style_id,
                author_name=author_name,
                file_paths=file_paths,
                caller=caller,
            )
        elapsed = (datetime.now() - started).total_seconds()
        success = result.get('status') == 'profiling_completed'
        style_id = result.get('author_style_id')

        conn = db_pool.getconn()
        try:
            phase_status = 'completed' if success else 'failed'
            _update_pipeline_run(conn, run_id,
                                 phase_2_status=phase_status,
                                 author_style_id=style_id if success else None)
            conn.commit()
        finally:
            db_pool.putconn(conn)

        return {
            'success': success,
            'error': result.get('error_message') if not success else None,
            'author_style_id': style_id,
            'timing_seconds': elapsed,
        }

    except Exception as exc:
        elapsed = (datetime.now() - started).total_seconds()
        logger.error(f"[Pipeline {run_id}] Phase 2 raised exception: {exc}", exc_info=True)
        conn = db_pool.getconn()
        try:
            _update_pipeline_run(conn, run_id, phase_2_status='failed')
            conn.commit()
        finally:
            db_pool.putconn(conn)
        return {'success': False, 'error': str(exc), 'author_style_id': None,
                'timing_seconds': elapsed}


def _run_phase_3(draft_id: str, user_id: str, workspace_id: str,
                 project_id: str, provider: str, model: str,
                 author_style_name: Optional[str],
                 target_chapter_length: int, quality_threshold: float,
                 max_improvement_passes: int, writing_perspective: str,
                 enforce_hard_quality_gate: bool,
                 hard_quality_threshold: Optional[float],
                 generation_config_dict: dict,
                 db_pool: SimpleConnectionPool, run_id: str, flask_app) -> dict:
    """
    Execute Phase 3 (Novel Writer). Runs after Phases 1 & 2 have completed.
    Returns a result dict with keys: success, error, timing_seconds.
    """
    started = datetime.now()
    conn = db_pool.getconn()
    try:
        _update_pipeline_run(conn, run_id,
                             status='phase_3_running',
                             current_phase=3,
                             phase_3_status='running')
        conn.commit()
    finally:
        db_pool.putconn(conn)

    try:
        with flask_app.app_context():
            caller = CallerInfo(
                user_id=str(user_id),
                workspace_id=workspace_id,
                project_id=project_id,
                api_keys={},
                session_id=str(uuid.uuid4()),
            )
            gen_config = GenerationConfig(**(generation_config_dict or {}))
            generation_request = BaseGenerationRequest(
                prompt="",
                provider=provider,
                model=model,
                caller=caller,
                generation_config=gen_config,
            )
            engine = GenerationEngine(generation_request)
            orchestrator = NovelWriterOrchestrator(
                generation_engine=engine,
                db_pool=db_pool,
            )
            result = orchestrator.run_pipeline(
                draft_id=draft_id,
                user_id=user_id,
                workspace_id=workspace_id,
                target_chapter_length=target_chapter_length,
                author_style_name=author_style_name,
                quality_threshold=quality_threshold,
                max_improvement_passes=max_improvement_passes,
                writing_perspective=writing_perspective,
                enforce_hard_quality_gate=enforce_hard_quality_gate,
                hard_quality_threshold=hard_quality_threshold,
            )
        elapsed = (datetime.now() - started).total_seconds()
        success = result.get('success', False)

        conn = db_pool.getconn()
        try:
            _update_pipeline_run(conn, run_id,
                                 phase_3_status='completed' if success else 'failed')
            conn.commit()
        finally:
            db_pool.putconn(conn)

        return {
            'success': success,
            'error': result.get('error'),
            'timing_seconds': elapsed,
        }

    except Exception as exc:
        elapsed = (datetime.now() - started).total_seconds()
        logger.error(f"[Pipeline {run_id}] Phase 3 raised exception: {exc}", exc_info=True)
        conn = db_pool.getconn()
        try:
            _update_pipeline_run(conn, run_id, phase_3_status='failed')
            conn.commit()
        finally:
            db_pool.putconn(conn)
        return {'success': False, 'error': str(exc), 'timing_seconds': elapsed}


def _orchestrate_pipeline(run_id: str, draft_id: str,
                           manuscript_filename: str, author_style_files: list,
                           data: PipelineStartRequest, db_pool: SimpleConnectionPool,
                           flask_app) -> None:
    """
    Top-level background orchestration function.

    Execution order:
      1. Mark pipeline as phase_1_2_running
      2. Run Phase 1 (Deconstructor) + Phase 2 (Style Analyzer) in parallel via ThreadPoolExecutor
      3. If both succeed → run Phase 3 (Novel Writer)
      4. Update final pipeline_runs status
    """
    logger.info(f"[Pipeline {run_id}] Starting orchestration for draft {draft_id}")

    # Build CallerInfo for Phase 2 (style analyzer needs it)
    caller = CallerInfo(
        user_id=str(data.caller.user_id),
        workspace_id=data.caller.workspace_id,
        project_id=data.caller.project_id,
        api_keys={},
        session_id=str(uuid.uuid4()),
    )

    # Mark overall status
    conn = db_pool.getconn()
    try:
        _update_pipeline_run(conn, run_id,
                             status='phase_1_2_running',
                             current_phase=1)
        conn.commit()
    finally:
        db_pool.putconn(conn)

    phase_1_result = {}
    phase_2_result = {}
    phase_meta = {}

    # -----------------------------------------------------------------------
    # Parallel: Phase 1 + Phase 2
    # -----------------------------------------------------------------------
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_p1 = executor.submit(
            _run_phase_1,
            draft_id=draft_id,
            manuscript_filename=manuscript_filename,
            chaptering_mode=data.chaptering_mode,
            target_chapter_length=data.target_chapter_length,
            provider=data.provider,
            model=data.model,
            user_id=data.caller.user_id,
            workspace_id=data.caller.workspace_id,
            project_id=data.caller.project_id,
            db_pool=db_pool,
            run_id=run_id,
            flask_app=flask_app,
        )
        future_p2 = executor.submit(
            _run_phase_2,
            author_name=data.author_name,
            file_paths=author_style_files,
            caller=caller,
            style_config=data.style_analyzer_config,
            on_exist=data.on_exist,
            db_pool=db_pool,
            run_id=run_id,
            flask_app=flask_app,
        )

        for future in as_completed([future_p1, future_p2]):
            if future is future_p1:
                phase_1_result = future.result()
                phase_meta['phase_1'] = {
                    'success': phase_1_result['success'],
                    'error': phase_1_result.get('error'),
                    'timing_seconds': phase_1_result.get('timing_seconds'),
                }
            else:
                phase_2_result = future.result()
                phase_meta['phase_2'] = {
                    'success': phase_2_result['success'],
                    'error': phase_2_result.get('error'),
                    'author_style_id': phase_2_result.get('author_style_id'),
                    'timing_seconds': phase_2_result.get('timing_seconds'),
                }

    logger.info(
        f"[Pipeline {run_id}] Phase 1 {'OK' if phase_1_result.get('success') else 'FAILED'}, "
        f"Phase 2 {'OK' if phase_2_result.get('success') else 'FAILED'}"
    )

    # -----------------------------------------------------------------------
    # Gate: both phases must succeed to continue
    # -----------------------------------------------------------------------
    if not phase_1_result.get('success') or not phase_2_result.get('success'):
        failed_phase = None
        errors = []
        if not phase_1_result.get('success'):
            failed_phase = 1
            errors.append(f"Phase 1: {phase_1_result.get('error', 'unknown error')}")
        if not phase_2_result.get('success'):
            failed_phase = failed_phase or 2
            errors.append(f"Phase 2: {phase_2_result.get('error', 'unknown error')}")

        error_msg = "; ".join(errors)
        logger.error(f"[Pipeline {run_id}] Aborting before Phase 3. Errors: {error_msg}")
        draft_error_msg = error_msg[:250]  # drafts.error_message is VARCHAR(255)

        conn = db_pool.getconn()
        try:
            _update_pipeline_run(
                conn, run_id,
                status='failed',
                failed_phase=failed_phase,
                error_message=error_msg,
                completed_at=datetime.now().isoformat(),
                metadata=phase_meta,
            )
            # Also update draft status
            conn.cursor().execute(
                "UPDATE drafts SET status = %s, error_message = %s WHERE id = %s",
                (DraftStatus.PIPELINE_FAILED.value, draft_error_msg, draft_id)
            )
            conn.commit()
        finally:
            db_pool.putconn(conn)
        return

    # -----------------------------------------------------------------------
    # Sequential: Phase 3 (Novel Writer)
    # -----------------------------------------------------------------------
    author_style_id = phase_2_result.get('author_style_id')
    # Resolve the author_style_name: pass the name so the Novel Writer
    # picks the correct style from the workspace by name.
    author_style_name = data.author_name

    phase_3_result = _run_phase_3(
        draft_id=draft_id,
        user_id=data.caller.user_id,
        workspace_id=data.caller.workspace_id,
        project_id=data.caller.project_id,
        provider=data.provider,
        model=data.model,
        author_style_name=author_style_name,
        target_chapter_length=data.target_chapter_length,
        quality_threshold=data.quality_threshold,
        max_improvement_passes=data.max_improvement_passes,
        writing_perspective=data.writing_perspective,
        enforce_hard_quality_gate=data.enforce_hard_quality_gate,
        hard_quality_threshold=data.hard_quality_threshold,
        generation_config_dict=data.generation_config,
        db_pool=db_pool,
        run_id=run_id,
        flask_app=flask_app,
    )
    phase_meta['phase_3'] = {
        'success': phase_3_result['success'],
        'error': phase_3_result.get('error'),
        'timing_seconds': phase_3_result.get('timing_seconds'),
    }

    # -----------------------------------------------------------------------
    # Final status
    # -----------------------------------------------------------------------
    if phase_3_result.get('success'):
        logger.info(f"[Pipeline {run_id}] All 3 phases completed successfully.")
        conn = db_pool.getconn()
        try:
            _update_pipeline_run(
                conn, run_id,
                status='completed',
                current_phase=None,
                author_style_id=author_style_id,
                completed_at=datetime.now().isoformat(),
                metadata=phase_meta,
            )
            conn.cursor().execute(
                "UPDATE drafts SET status = %s WHERE id = %s",
                (DraftStatus.PIPELINE_COMPLETED.value, draft_id)
            )
            conn.commit()
        finally:
            db_pool.putconn(conn)
    else:
        error_msg = phase_3_result.get('error', 'Phase 3 failed')
        logger.error(f"[Pipeline {run_id}] Phase 3 failed: {error_msg}")
        draft_error_msg = error_msg[:250]  # drafts.error_message is VARCHAR(255)
        conn = db_pool.getconn()
        try:
            _update_pipeline_run(
                conn, run_id,
                status='failed',
                failed_phase=3,
                error_message=error_msg,
                author_style_id=author_style_id,
                completed_at=datetime.now().isoformat(),
                metadata=phase_meta,
            )
            conn.cursor().execute(
                "UPDATE drafts SET status = %s, error_message = %s WHERE id = %s",
                (DraftStatus.PIPELINE_FAILED.value, draft_error_msg, draft_id)
            )
            conn.commit()
        finally:
            db_pool.putconn(conn)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@novel_pipeline.route('/novel-pipeline/start', methods=['POST'])
def start_novel_pipeline():
    """
    Start the full 3-phase novel pipeline.

    Expects multipart/form-data with:
      manuscript_file  : The source manuscript (PDF or TXT). Required.
      author_files     : One or more author voice sample files (PDF/TXT/DOCX). Required.
      data             : JSON string matching PipelineStartRequest schema. Required.

    Returns 202 Accepted immediately; the pipeline runs in the background.
    Poll /api/novel-pipeline/status/<run_id> for progress.

    Example data JSON:
    {
        "caller": {"user_id": "1", "workspace_id": "<ulid>", "project_id": "<ulid>"},
        "author_name": "J.R.R. Tolkien",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "chaptering_mode": "flexible",
        "target_chapter_length": 2500,
        "quality_threshold": 6.0,
        "max_improvement_passes": 2,
        "writing_perspective": "third_person_limited",
        "enforce_hard_quality_gate": true,
        "hard_quality_threshold": 6.5,
        "author_style_mode": "create_or_update",
        "on_exist": "update"
    }
    """
    try:
        db_pool: Optional[SimpleConnectionPool] = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return internal_error('Database connection pool not configured')

        upload_path: str = current_app.config.get('UPLOAD_PATH', '/app/uploads')

        # ------------------------------------------------------------------
        # 1. Parse and validate JSON config from form data
        # ------------------------------------------------------------------
        raw_data = request.form.get('data')
        if not raw_data:
            return validation_error({'data': ['data field is required (JSON string)']})

        try:
            loaded = json.loads(raw_data)
            data = PipelineStartRequest(**loaded)
        except (json.JSONDecodeError, ValidationError) as exc:
            return validation_error({'data': [f'Invalid request data: {str(exc)}']})

        # Validate chaptering_mode
        if data.chaptering_mode not in ('flexible', 'constrained'):
            return validation_error({
                'chaptering_mode': ['Must be "flexible" or "constrained"']
            })
        if data.target_chapter_length < 500:
            return validation_error({
                'target_chapter_length': ['Must be >= 500']
            })
        if not (1.0 <= data.quality_threshold <= 10.0):
            return validation_error({
                'quality_threshold': ['Must be between 1 and 10']
            })
        if data.max_improvement_passes < 0:
            return validation_error({
                'max_improvement_passes': ['Must be >= 0']
            })
        if data.hard_quality_threshold is not None and not (1.0 <= data.hard_quality_threshold <= 10.0):
            return validation_error({
                'hard_quality_threshold': ['Must be between 1 and 10']
            })
        normalized_perspective = _normalize_writing_perspective(data.writing_perspective)
        if normalized_perspective is None:
            return validation_error({
                'writing_perspective': [
                    'Must be one of: first_person, second_person, '
                    'third_person_limited, third_person_omniscient'
                ]
            })
        data.writing_perspective = normalized_perspective

        normalized_style_mode = _normalize_author_style_mode(data.author_style_mode)
        if data.author_style_mode is not None and normalized_style_mode is None:
            return validation_error({
                'author_style_mode': [
                    'Must be one of: create_or_update, use_existing'
                ]
            })
        data.author_style_mode = normalized_style_mode
        if data.on_exist not in ('update', 'get', 'error'):
            return validation_error({
                'on_exist': ['Must be "update", "get", or "error"']
            })

        # Prefer the high-level style mode when provided.
        if data.author_style_mode == 'create_or_update':
            data.on_exist = 'update'
        elif data.author_style_mode == 'use_existing':
            data.on_exist = 'get'

        # ------------------------------------------------------------------
        # 2. Handle manuscript file upload
        # ------------------------------------------------------------------
        if 'manuscript_file' not in request.files:
            return validation_error({'manuscript_file': ['Manuscript file is required']})

        manuscript = request.files['manuscript_file']
        if not manuscript.filename:
            return validation_error({'manuscript_file': ['Manuscript file has no filename']})

        ms_ext = os.path.splitext(manuscript.filename)[1].lower()
        if ms_ext not in ('.pdf', '.txt'):
            return validation_error({
                'manuscript_file': ['Only PDF and TXT files are supported for the manuscript']
            })

        ms_filename = f"{ulid_lib.ULID()}_{secure_filename(manuscript.filename)}"
        ms_path = os.path.join(upload_path, ms_filename)
        os.makedirs(upload_path, exist_ok=True)
        manuscript.save(ms_path)

        # Validate size after saving (100 MB limit)
        ms_size = os.path.getsize(ms_path)
        if ms_size > 100 * 1024 * 1024:
            os.remove(ms_path)
            return validation_error({
                'manuscript_file': [
                    f'File size ({ms_size / (1024*1024):.1f} MB) exceeds 100 MB limit'
                ]
            })

        # ------------------------------------------------------------------
        # 3. Handle author style file uploads
        # ------------------------------------------------------------------
        author_files = request.files.getlist('author_files')
        if not author_files or all(not f.filename for f in author_files):
            os.remove(ms_path)
            return validation_error({'author_files': ['At least one author style file is required']})

        author_samples_dir = os.path.join(upload_path, 'author_samples')
        os.makedirs(author_samples_dir, exist_ok=True)

        author_file_paths = []
        for af in author_files:
            if not af.filename:
                continue
            af_filename = f"{ulid_lib.ULID()}_{secure_filename(af.filename)}"
            af_path = os.path.join(author_samples_dir, af_filename)
            af.save(af_path)
            author_file_paths.append(af_path)

        if not author_file_paths:
            os.remove(ms_path)
            return validation_error({'author_files': ['No valid author style files provided']})

        # ------------------------------------------------------------------
        # 4. Create draft record in DB
        # ------------------------------------------------------------------
        draft_id = str(ulid_lib.ULID())
        run_id = str(ulid_lib.ULID())
        workspace_id = data.caller.workspace_id
        user_id = data.caller.user_id

        conn = db_pool.getconn()
        conn_returned = False
        try:
            with conn.cursor() as cur:
                # Verify workspace membership
                cur.execute("""
                    SELECT wm.workspace_id
                    FROM workspace_members wm
                    WHERE wm.workspace_id = %s AND wm.user_id = %s
                    LIMIT 1
                """, (workspace_id, user_id))
                if not cur.fetchone():
                    conn.rollback()
                    db_pool.putconn(conn)
                    conn_returned = True
                    # Clean up uploaded files
                    os.remove(ms_path)
                    for p in author_file_paths:
                        os.remove(p)
                    return error(
                        'User is not a member of the specified workspace',
                        error_code='FORBIDDEN',
                        status_code=403,
                    )

                # Insert draft record
                cur.execute("""
                    INSERT INTO drafts (
                        id, workspace_id, user_id,
                        original_filename, file_path, file_size,
                        status, processing_started_at,
                        metadata, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, NOW(), NOW())
                """, (
                    draft_id,
                    workspace_id,
                    user_id,
                    secure_filename(manuscript.filename),
                    ms_path,
                    ms_size,
                    DraftStatus.PIPELINE_PENDING.value,
                    json.dumps({'pipeline_run_id': run_id, 'orchestrated': True}),
                ))

            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.error(f"Failed to create draft record: {exc}", exc_info=True)
            os.remove(ms_path)
            for p in author_file_paths:
                os.remove(p)
            return internal_error('Failed to create draft record')
        finally:
            if not conn_returned:
                db_pool.putconn(conn)

        # ------------------------------------------------------------------
        # 5. Create pipeline_runs record
        # ------------------------------------------------------------------
        config_snapshot = {
            'provider': data.provider,
            'model': data.model,
            'author_name': data.author_name,
            'chaptering_mode': data.chaptering_mode,
            'target_chapter_length': data.target_chapter_length,
            'quality_threshold': data.quality_threshold,
            'enforce_hard_quality_gate': data.enforce_hard_quality_gate,
            'hard_quality_threshold': data.hard_quality_threshold,
            'max_improvement_passes': data.max_improvement_passes,
            'writing_perspective': data.writing_perspective,
            'author_style_mode': data.author_style_mode,
            'on_exist': data.on_exist,
            'manuscript_filename': ms_filename,
            'author_file_count': len(author_file_paths),
        }

        conn = db_pool.getconn()
        try:
            _create_pipeline_run(
                conn=conn,
                run_id=run_id,
                draft_id=draft_id,
                workspace_id=workspace_id,
                user_id=user_id,
                author_name=data.author_name,
                config=config_snapshot,
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.error(f"Failed to create pipeline_runs record: {exc}", exc_info=True)
            # Non-fatal for the background job; log and continue
        finally:
            db_pool.putconn(conn)

        # ------------------------------------------------------------------
        # 6. Kick off background orchestration
        # ------------------------------------------------------------------
        # Capture the real Flask app object so the background thread can push
        # its own app context — current_app proxies don't work outside requests.
        flask_app = current_app._get_current_object()

        thread = threading.Thread(
            target=_orchestrate_pipeline,
            kwargs=dict(
                run_id=run_id,
                draft_id=draft_id,
                manuscript_filename=ms_filename,
                author_style_files=author_file_paths,
                data=data,
                db_pool=db_pool,
                flask_app=flask_app,
            ),
            daemon=True,
        )
        thread.start()

        logger.info(
            f"Novel pipeline started: run_id={run_id}, draft_id={draft_id}, "
            f"workspace={workspace_id}, author={data.author_name}"
        )

        return ApiResponse.processing(
            data={
                'pipeline_run_id': run_id,
                'draft_id': draft_id,
                'status': 'pending',
                'phases': {
                    'phase_1': 'pending',
                    'phase_2': 'pending',
                    'phase_3': 'pending',
                },
            },
            message='Novel pipeline started. Phases 1 (deconstructor) and 2 (style analyzer) '
                    'are running in parallel. Use the status endpoint to track progress.',
        )

    except Exception as exc:
        logger.error(f"Unexpected error in start_novel_pipeline: {exc}", exc_info=True)
        return internal_error('Internal server error')


# ---------------------------------------------------------------------------

@novel_pipeline.route('/novel-pipeline/status/<run_id>', methods=['GET'])
def get_pipeline_status(run_id: str):
    """
    Get the combined progress of a pipeline run across all 3 phases.

    Query params:
      user_id (required) — for ownership verification.
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return validation_error({'user_id': ['user_id query parameter is required']})

        db_pool: Optional[SimpleConnectionPool] = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return internal_error('Database connection pool not configured')

        conn = db_pool.getconn()
        try:
            run = _get_pipeline_run(conn, run_id)
            if not run:
                return error('Pipeline run not found', error_code='NOT_FOUND', status_code=404)

            # Verify user belongs to the workspace
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 1 FROM workspace_members
                    WHERE workspace_id = %s AND user_id = %s
                    LIMIT 1
                """, (run['workspace_id'], user_id))
                if not cur.fetchone():
                    return error('Access denied', error_code='FORBIDDEN', status_code=403)

            # Self-heal rare stuck phase_3_running rows when final artifacts
            # are already persisted.
            run = _reconcile_phase_3_completion_from_artifacts(conn, run)

            # Fetch supplementary data from drafts table for richer progress
            draft_status = None
            draft_error = None
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status, error_message FROM drafts WHERE id = %s",
                    (run['draft_id'],)
                )
                row = cur.fetchone()
                if row:
                    draft_status, draft_error = row

        finally:
            db_pool.putconn(conn)

        # Build a unified percentage estimate
        overall_pct = _compute_overall_percentage(
            run['status'],
            run['phase_1_status'],
            run['phase_2_status'],
            run['phase_3_status'],
        )

        response_data = {
            'pipeline_run_id': run_id,
            'draft_id': run['draft_id'],
            'author_name': run['author_name'],
            'author_style_id': run['author_style_id'],
            'status': run['status'],
            'overall_percentage': overall_pct,
            'current_phase': run['current_phase'],
            'phases': {
                'phase_1': {
                    'name': 'deconstructor',
                    'status': run['phase_1_status'],
                },
                'phase_2': {
                    'name': 'style_analyzer',
                    'status': run['phase_2_status'],
                },
                'phase_3': {
                    'name': 'novel_writer',
                    'status': run['phase_3_status'],
                },
            },
            'draft_status': draft_status,
            'started_at': run['started_at'].isoformat() if run['started_at'] else None,
            'completed_at': run['completed_at'].isoformat() if run['completed_at'] else None,
            'error_message': run['error_message'] or draft_error,
            'failed_phase': run['failed_phase'],
            'metadata': run['metadata'],
        }

        return ApiResponse.success(data=response_data)

    except Exception as exc:
        logger.error(f"Error getting pipeline status for {run_id}: {exc}", exc_info=True)
        return internal_error('Internal server error')


def _compute_overall_percentage(status: str, p1: str, p2: str, p3: str) -> int:
    """
    Compute a rough overall pipeline completion percentage.

    Phase 1 & 2 each represent 35% of total work (70% combined).
    Phase 3 represents the remaining 30%.
    """
    if status == 'completed':
        return 100
    if status == 'failed':
        return 0

    pct = 0
    phase_weight = {'pending': 0, 'running': 0.5, 'completed': 1.0, 'failed': 0, 'skipped': 1.0}
    pct += phase_weight.get(p1, 0) * 35
    pct += phase_weight.get(p2, 0) * 35
    pct += phase_weight.get(p3, 0) * 30
    return int(pct)


def _reconcile_phase_3_completion_from_artifacts(conn, run: dict) -> dict:
    """
    Reconcile stuck phase_3_running rows when final artifacts are already persisted.

    In rare cases the background thread can persist final manuscript artifacts but
    fail to update pipeline_runs to terminal completed state. This function
    performs a conservative self-heal so status/results endpoints remain usable.
    """
    if not run:
        return run

    if not (
        run.get('status') == 'phase_3_running'
        and run.get('phase_1_status') == 'completed'
        and run.get('phase_2_status') == 'completed'
        and run.get('phase_3_status') == 'running'
    ):
        return run

    with conn.cursor() as cur:
        cur.execute("SELECT status FROM drafts WHERE id = %s", (run['draft_id'],))
        draft_row = cur.fetchone()
        draft_status = draft_row[0] if draft_row else None

        # Only reconcile when draft already reached a terminal completed state.
        if draft_status not in (
            DraftStatus.NW_COMPLETED.value,
            DraftStatus.PIPELINE_COMPLETED.value,
        ):
            return run

        cur.execute(
            "SELECT COUNT(*) FROM final_manuscripts WHERE draft_id = %s",
            (run['draft_id'],),
        )
        manuscript_count = int(cur.fetchone()[0] or 0)

        cur.execute(
            "SELECT COUNT(*) FROM chapters WHERE draft_id = %s",
            (run['draft_id'],),
        )
        chapter_count = int(cur.fetchone()[0] or 0)

        if manuscript_count > 0 and chapter_count > 0:
            logger.warning(
                "[Pipeline %s] Reconciling stuck phase_3_running state "
                "(final artifacts already persisted: manuscripts=%s, chapters=%s)",
                run['id'],
                manuscript_count,
                chapter_count,
            )
            _update_pipeline_run(
                conn,
                run['id'],
                status='completed',
                current_phase=None,
                phase_3_status='completed',
                completed_at=datetime.now().isoformat(),
            )
            cur.execute(
                "UPDATE drafts SET status = %s WHERE id = %s",
                (DraftStatus.PIPELINE_COMPLETED.value, run['draft_id']),
            )
            conn.commit()
            return _get_pipeline_run(conn, run['id']) or run

    return run


# ---------------------------------------------------------------------------

@novel_pipeline.route('/novel-pipeline/results/<run_id>', methods=['GET'])
def get_pipeline_results(run_id: str):
    """
    Get the final results of a completed pipeline run.

    Query params:
      user_id (required) — for ownership verification.

    Returns 409 if the pipeline has not yet completed.
    """
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return validation_error({'user_id': ['user_id query parameter is required']})

        db_pool: Optional[SimpleConnectionPool] = current_app.config.get('CONNECTION_POOL')
        if not db_pool:
            return internal_error('Database connection pool not configured')

        conn = db_pool.getconn()
        try:
            run = _get_pipeline_run(conn, run_id)
            if not run:
                return error('Pipeline run not found', error_code='NOT_FOUND', status_code=404)

            # Verify membership
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 1 FROM workspace_members
                    WHERE workspace_id = %s AND user_id = %s
                    LIMIT 1
                """, (run['workspace_id'], user_id))
                if not cur.fetchone():
                    return error('Access denied', error_code='FORBIDDEN', status_code=403)

            # Self-heal rare stuck phase_3_running rows when final artifacts
            # are already persisted.
            run = _reconcile_phase_3_completion_from_artifacts(conn, run)

            if run['status'] != 'completed':
                return error(
                    f"Pipeline has not completed yet (status: {run['status']})",
                    error_code='NOT_READY',
                    status_code=409,
                )

            draft_id = run['draft_id']
            results = {}

            with conn.cursor() as cur:
                # Final manuscript
                cur.execute("""
                    SELECT id, word_count, generated_at, processing_summary
                    FROM final_manuscripts
                    WHERE draft_id = %s
                    ORDER BY generated_at DESC
                    LIMIT 1
                """, (draft_id,))
                ms_row = cur.fetchone()
                if ms_row:
                    results['manuscript'] = {
                        'id': ms_row[0],
                        'word_count': ms_row[1],
                        'generated_at': ms_row[2].isoformat() if ms_row[2] else None,
                        'processing_summary': ms_row[3],
                    }

                # Chapter count
                cur.execute(
                    "SELECT COUNT(*) FROM chapters WHERE draft_id = %s", (draft_id,)
                )
                results['chapter_count'] = cur.fetchone()[0]

                # Scene count
                cur.execute(
                    "SELECT COUNT(*) FROM scenes WHERE draft_id = %s", (draft_id,)
                )
                results['scene_count'] = cur.fetchone()[0]

                # Plot issues summary
                cur.execute("""
                    SELECT issue_type, COUNT(*)
                    FROM plot_issues WHERE draft_id = %s
                    GROUP BY issue_type
                """, (draft_id,))
                results['plot_issues'] = {r[0]: r[1] for r in cur.fetchall()}

                # Author style info
                if run['author_style_id']:
                    cur.execute("""
                        SELECT author_name, status, total_time_ms
                        FROM author_styles WHERE id = %s
                    """, (run['author_style_id'],))
                    as_row = cur.fetchone()
                    if as_row:
                        results['author_style'] = {
                            'id': run['author_style_id'],
                            'author_name': as_row[0],
                            'status': as_row[1],
                            'total_time_ms': as_row[2],
                        }

        finally:
            db_pool.putconn(conn)

        return ApiResponse.success(
            data={
                'pipeline_run_id': run_id,
                'draft_id': run['draft_id'],
                'author_name': run['author_name'],
                'completed_at': run['completed_at'].isoformat() if run['completed_at'] else None,
                'results': results,
                'phase_timings': run['metadata'] or {},
            }
        )

    except Exception as exc:
        logger.error(f"Error getting pipeline results for {run_id}: {exc}", exc_info=True)
        return internal_error('Internal server error')
