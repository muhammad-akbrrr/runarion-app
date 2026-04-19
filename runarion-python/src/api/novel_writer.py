"""
API endpoints for the novel writer service.
Handles novel generation pipeline requests.
"""

import uuid
import threading
import logging
from flask import Blueprint, request, current_app

from services.novel_writer.orchestrator import NovelWriterOrchestrator
from services.generation_engine import GenerationEngine
from models.request import BaseGenerationRequest, CallerInfo, GenerationConfig
from utils.api_response import DeconstructorResponse, validation_error, internal_error, error

logger = logging.getLogger(__name__)

rewrite_novel = Blueprint("rewrite_novel", __name__)


@rewrite_novel.route('/novel-writer/generate', methods=['POST'])
def start_novel_generation():
    """
    Start the novel writer pipeline.

    Expected request format:
    {
        "draft_id": "uuid-string",
        "user_id": 123,
        "workspace_id": "workspace-uuid",
        "project_id": "project-uuid",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "author_style_name": "Author Name",       // optional
        "target_chapter_length": 2500,             // optional
        "quality_threshold": 6.0,                  // optional
        "max_improvement_passes": 2,               // optional
        "generation_config": {}                    // optional
    }
    """
    try:
        if not request.is_json:
            return validation_error({'request': ['Request must be JSON']})

        data = request.get_json()

        # Validate required fields
        required_fields = ['draft_id', 'user_id', 'workspace_id']
        field_errors = {}

        for field in required_fields:
            if field not in data or not data[field]:
                field_errors[field] = [f'{field} is required']

        if field_errors:
            return validation_error(field_errors)

        draft_id = data['draft_id']
        user_id = data['user_id']
        workspace_id = data['workspace_id']
        project_id = data.get('project_id', workspace_id)
        provider = data.get('provider', 'gemini')
        model = data.get('model', 'gemini-2.5-flash')

        # Optional parameters
        author_style_name = data.get('author_style_name')
        target_chapter_length = data.get('target_chapter_length', 2500)
        quality_threshold = data.get('quality_threshold', 6.0)
        max_improvement_passes = data.get('max_improvement_passes', 2)

        # Validate optional parameters
        if not isinstance(target_chapter_length, int) or target_chapter_length < 500:
            field_errors['target_chapter_length'] = [
                'target_chapter_length must be an integer >= 500'
            ]

        if not isinstance(quality_threshold, (int, float)) or not (1 <= quality_threshold <= 10):
            field_errors['quality_threshold'] = [
                'quality_threshold must be a number between 1 and 10'
            ]

        if not isinstance(max_improvement_passes, int) or max_improvement_passes < 0:
            field_errors['max_improvement_passes'] = [
                'max_improvement_passes must be a non-negative integer'
            ]

        if field_errors:
            return validation_error(field_errors)

        # Validate database connection
        connection_pool = current_app.config.get('CONNECTION_POOL')
        if not connection_pool:
            return internal_error('Database connection not available')

        # Validate draft ownership and that deconstruction is complete
        conn = None
        try:
            conn = connection_pool.getconn()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT d.id, d.workspace_id, d.user_id, d.status
                    FROM drafts d
                    INNER JOIN workspace_members wm ON d.workspace_id = wm.workspace_id
                    WHERE d.id = %s AND wm.user_id = %s
                """, (draft_id, user_id))

                draft_result = cursor.fetchone()

                if not draft_result:
                    return DeconstructorResponse.permission_denied(draft_id)

                if draft_result[1] != workspace_id:
                    return error('Workspace ID mismatch', error_code='WORKSPACE_MISMATCH')

                draft_status = draft_result[3]

                # Verify deconstruction is complete
                valid_start_statuses = ['completed', 'nw_failed', 'nw_completed']
                if draft_status not in valid_start_statuses:
                    return error(
                        f'Draft must be in a completed state to start novel writing. '
                        f'Current status: {draft_status}',
                        error_code='INVALID_STATUS',
                        status_code=409,
                    )

                # Update draft status to indicate novel writing is starting
                cursor.execute(
                    "UPDATE drafts SET status = %s, processing_started_at = NOW() WHERE id = %s",
                    ('novel_writing', draft_id)
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to validate draft for novel writing: {e}")
            if conn:
                conn.rollback()
            return internal_error('Failed to start novel writing')
        finally:
            if conn:
                connection_pool.putconn(conn)

        # Create generation engine
        caller = CallerInfo(
            user_id=str(user_id),
            workspace_id=workspace_id,
            project_id=project_id,
            api_keys={},
            session_id=str(uuid.uuid4()),
        )

        generation_config = GenerationConfig(
            **(data.get('generation_config', {}))
        )

        generation_request = BaseGenerationRequest(
            prompt="",
            provider=provider,
            model=model,
            caller=caller,
            generation_config=generation_config,
        )

        generation_engine = GenerationEngine(generation_request)

        # Create orchestrator
        orchestrator = NovelWriterOrchestrator(
            generation_engine=generation_engine,
            db_pool=connection_pool,
        )

        # Start pipeline in background thread
        processing_thread = threading.Thread(
            target=orchestrator.run_pipeline,
            kwargs={
                'draft_id': draft_id,
                'user_id': user_id,
                'workspace_id': workspace_id,
                'target_chapter_length': target_chapter_length,
                'author_style_name': author_style_name,
                'quality_threshold': quality_threshold,
                'max_improvement_passes': max_improvement_passes,
            },
            daemon=True,
        )
        processing_thread.start()

        logger.info(f"Started novel writer pipeline for draft {draft_id}")

        return DeconstructorResponse.pipeline_started(draft_id)

    except Exception as e:
        logger.error(f"Error starting novel writer pipeline: {e}")
        return internal_error('Internal server error')


@rewrite_novel.route('/novel-writer/status/<draft_id>', methods=['GET'])
def get_novel_writer_status(draft_id):
    """
    Get the current status of the novel writer pipeline.
    """
    try:
        user_id = request.args.get('user_id')

        if not user_id:
            return validation_error({'user_id': ['user_id is required as query parameter']})

        connection_pool = current_app.config.get('CONNECTION_POOL')
        if not connection_pool:
            return internal_error('Database connection not available')

        conn = None
        try:
            conn = connection_pool.getconn()
            with conn.cursor() as cursor:
                # Validate ownership
                cursor.execute("""
                    SELECT d.status, d.processing_started_at, d.processing_completed_at,
                           d.error_message, d.metadata
                    FROM drafts d
                    INNER JOIN workspace_members wm ON d.workspace_id = wm.workspace_id
                    WHERE d.id = %s AND wm.user_id = %s
                """, (draft_id, user_id))

                result = cursor.fetchone()

                if not result:
                    return DeconstructorResponse.permission_denied(draft_id)

                status, started_at, completed_at, error_message, metadata = result

                # Build progress info for novel writer statuses
                progress_info = _get_nw_pipeline_progress(cursor, draft_id, status, metadata)

                return DeconstructorResponse.pipeline_status(
                    draft_id=draft_id,
                    status=status,
                    started_at=started_at,
                    completed_at=completed_at,
                    error_message=error_message,
                    metadata=metadata,
                    progress=progress_info,
                )

        finally:
            if conn:
                connection_pool.putconn(conn)

    except Exception as e:
        logger.error(f"Error getting novel writer status: {e}")
        return internal_error('Internal server error')


def _get_nw_pipeline_progress(cursor, draft_id, status, metadata):
    """Get novel writer-specific progress information."""
    progress = {
        'stage': 'unknown',
        'percentage': 0,
        'stages_completed': [],
    }

    status_mapping = {
        'novel_writing': {'stage': 'starting', 'percentage': 5},
        'nw_stage_1_complete': {'stage': 'entity_profiling', 'percentage': 15},
        'nw_stage_2_complete': {'stage': 'prose_generation', 'percentage': 50},
        'nw_stage_3_complete': {'stage': 'quality_assessment', 'percentage': 65},
        'nw_stage_4_complete': {'stage': 'scene_improvement', 'percentage': 85},
        'nw_completed': {'stage': 'completed', 'percentage': 100},
        'nw_failed': {'stage': 'failed', 'percentage': 0},
    }

    if status in status_mapping:
        progress.update(status_mapping[status])

    # Get counts
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM chapters WHERE draft_id = %s", (draft_id,)
        )
        chapter_count = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM final_manuscripts WHERE draft_id = %s", (draft_id,)
        )
        manuscript_count = cursor.fetchone()[0]

        progress['details'] = {
            'chapters_created': chapter_count,
            'manuscript_created': manuscript_count > 0,
        }

        # Include novel writer metadata if available
        if metadata and isinstance(metadata, dict):
            for key in ('nw_chapters_generated', 'nw_total_chapters', 'nw_total_words'):
                if key in metadata:
                    progress['details'][key] = metadata[key]

    except Exception as e:
        logger.warning(f"Could not get novel writer progress details: {e}")
        progress['details'] = {}

    return progress
