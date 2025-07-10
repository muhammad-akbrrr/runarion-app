"""
API endpoints for the novel deconstructor service.
Handles document upload and pipeline processing requests.
"""

import os
import uuid
import threading
from flask import Blueprint, request, current_app
from werkzeug.utils import secure_filename

from services.deconstructor.orchestrator import DeconstructorOrchestrator
from services.generation_engine import GenerationEngine
from models.request import BaseGenerationRequest
from models.quota import QuotaCaller
from utils.api_response import DeconstructorResponse, validation_error, internal_error, error
from utils.logging_config import get_pipeline_logger

logger = get_pipeline_logger(__name__)

deconstruct = Blueprint("deconstruct", __name__)

@deconstruct.route('/deconstruct', methods=['POST'])
def start_deconstruction():
    """
    Start the novel deconstruction pipeline.
    
    Expected request format:
    {
        "draft_id": "uuid-string",
        "file_name": "manuscript.pdf",
        "provider": "openai",
        "model": "gpt-4o",
        "user_id": 123,
        "workspace_id": "workspace-uuid",
        "project_id": "project-uuid",
        "chaptering_mode": "flexible",  // optional: "flexible" or "constrained"
        "target_chapter_length": 2500   // optional: target words per chapter
    }
    """
    try:
        # Validate request
        if not request.is_json:
            return validation_error({'request': ['Request must be JSON']})
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['draft_id', 'file_name', 'user_id', 'workspace_id']
        field_errors = {}
        
        for field in required_fields:
            if field not in data or not data[field]:
                field_errors[field] = [f'{field} is required']
        
        if field_errors:
            return validation_error(field_errors)
        
        draft_id = data['draft_id']
        file_name = secure_filename(data['file_name'])
        provider = data.get('provider', 'openai')
        model = data.get('model', 'gpt-4o')
        user_id = data['user_id']
        workspace_id = data['workspace_id']
        project_id = data.get('project_id', workspace_id)
        
        # Optional chaptering parameters
        chaptering_mode = data.get('chaptering_mode', 'flexible')
        target_chapter_length = data.get('target_chapter_length', 2500)
        
        # Validate chaptering parameters
        if chaptering_mode not in ['flexible', 'constrained']:
            field_errors['chaptering_mode'] = ['chaptering_mode must be "flexible" or "constrained"']
        
        if not isinstance(target_chapter_length, int) or target_chapter_length < 500:
            field_errors['target_chapter_length'] = ['target_chapter_length must be an integer >= 500']
        
        if field_errors:
            return validation_error(field_errors)
        
        # Validate file exists and size/type
        upload_path = current_app.config.get('UPLOAD_PATH', '/app/uploads')
        file_path = os.path.join(upload_path, file_name)
        
        if not os.path.exists(file_path):
            return error(
                f'File not found: {file_name}',
                error_code='FILE_NOT_FOUND',
                status_code=404
            )
        
        # Validate file size (100MB limit)
        file_size = os.path.getsize(file_path)
        max_file_size = 100 * 1024 * 1024  # 100MB in bytes
        
        if file_size > max_file_size:
            return validation_error({
                'file_size': [f'File size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed size (100MB)']
            })
        
        # Validate file type (PDF and TXT only)
        allowed_extensions = ['.pdf', '.txt']
        file_extension = os.path.splitext(file_name)[1].lower()
        
        if file_extension not in allowed_extensions:
            return validation_error({
                'file_type': [f'File type "{file_extension}" not allowed. Only PDF and TXT files are supported.']
            })
        
        # Validate database connection
        connection_pool = current_app.config.get('CONNECTION_POOL')
        if not connection_pool:
            return internal_error('Database connection not available')
        
        # Validate draft ownership and workspace membership
        conn = None
        try:
            conn = connection_pool.getconn()
            with conn.cursor() as cursor:
                # Check if draft exists and user has permission
                cursor.execute("""
                    SELECT d.id, d.workspace_id, d.user_id 
                    FROM drafts d
                    INNER JOIN workspace_members wm ON d.workspace_id = wm.workspace_id
                    WHERE d.id = %s AND wm.user_id = %s
                """, (draft_id, user_id))
                
                draft_result = cursor.fetchone()
                
                if not draft_result:
                    return DeconstructorResponse.permission_denied(draft_id)
                
                # Verify workspace_id matches the draft's workspace
                if draft_result[1] != workspace_id:
                    return error('Workspace ID mismatch', error_code='WORKSPACE_MISMATCH')
                
                # Update draft status to processing
                cursor.execute(
                    "UPDATE drafts SET status = %s, processing_started_at = NOW() WHERE id = %s",
                    ('processing', draft_id)
                )
                conn.commit()
                
        except Exception as e:
            logger.error("Failed to validate ownership or update draft status", error=str(e), draft_id=draft_id)
            if conn:
                conn.rollback()
            return internal_error('Failed to start processing')
        finally:
            if conn:
                connection_pool.putconn(conn)
        
        # Create caller object for generation engine
        caller = QuotaCaller.from_request_data(
            user_id=user_id,
            workspace_id=workspace_id,
            project_id=project_id,
            session_id=str(uuid.uuid4()),
            api_keys={}  # Will use default API keys
        )
        
        # Create generation request
        generation_request = BaseGenerationRequest(
            prompt="",  # Will be set by individual stages
            provider=provider,
            model=model,
            caller=caller
        )
        
        # Create generation engine
        generation_engine = GenerationEngine(generation_request)
        
        # Create orchestrator
        orchestrator = DeconstructorOrchestrator(
            generation_engine=generation_engine,
            db_pool=connection_pool
        )
        
        # Start processing in background thread with chaptering parameters
        processing_thread = threading.Thread(
            target=orchestrator.run_pipeline,
            args=(draft_id, file_name, chaptering_mode, target_chapter_length),
            daemon=True
        )
        processing_thread.start()
        
        logger.info("Started deconstruction pipeline", draft_id=draft_id)
        
        return DeconstructorResponse.pipeline_started(draft_id)
        
    except Exception as e:
        logger.error("Error starting deconstruction pipeline", error=str(e))
        return internal_error('Internal server error')

@deconstruct.route('/deconstruct/status/<draft_id>', methods=['GET'])
def get_deconstruction_status(draft_id):
    """
    Get the current status of a deconstruction pipeline.
    """
    try:
        # Get user_id from query parameters for GET request
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
                # Validate ownership first
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
                
                # Get progress information
                progress_info = _get_pipeline_progress(cursor, draft_id, status)
                
                return DeconstructorResponse.pipeline_status(
                    draft_id=draft_id,
                    status=status,
                    started_at=started_at,
                    completed_at=completed_at,
                    error_message=error_message,
                    metadata=metadata,
                    progress=progress_info
                )
                
        finally:
            if conn:
                connection_pool.putconn(conn)
            
    except Exception as e:
        logger.error("Error getting deconstruction status", error=str(e), draft_id=draft_id)
        return internal_error('Internal server error')

def _get_pipeline_progress(cursor, draft_id, status):
    """
    Get detailed progress information for the pipeline.
    """
    progress = {
        'stage': 'unknown',
        'percentage': 0,
        'stages_completed': []
    }
    
    # Map status to progress
    status_mapping = {
        'pending': {'stage': 'pending', 'percentage': 0},
        'processing': {'stage': 'in_progress', 'percentage': 10},
        'stage_1_complete': {'stage': 'ingestion', 'percentage': 15},
        'stage_2_complete': {'stage': 'cleaning', 'percentage': 30},
        'stage_3_complete': {'stage': 'scene_extraction', 'percentage': 45},
        'stage_4_complete': {'stage': 'analysis', 'percentage': 65},
        'stage_5_complete': {'stage': 'coherence_check', 'percentage': 80},
        'stage_6_complete': {'stage': 'enhancement', 'percentage': 90},
        'completed': {'stage': 'completed', 'percentage': 100},
        'failed': {'stage': 'failed', 'percentage': 0}
    }
    
    if status in status_mapping:
        progress.update(status_mapping[status])
    
    # Get count information for completed stages
    try:
        cursor.execute("SELECT COUNT(*) FROM draft_chunks WHERE draft_id = %s", (draft_id,))
        chunk_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM scenes WHERE draft_id = %s", (draft_id,))
        scene_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM plot_issues WHERE draft_id = %s", (draft_id,))
        issue_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM analysis_reports WHERE draft_id = %s", (draft_id,))
        report_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM final_manuscripts WHERE draft_id = %s", (draft_id,))
        manuscript_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM chapters WHERE draft_id = %s", (draft_id,))
        chapter_count = cursor.fetchone()[0]
        
        progress['details'] = {
            'chunks_created': chunk_count,
            'scenes_extracted': scene_count,
            'issues_identified': issue_count,
            'reports_generated': report_count,
            'manuscripts_created': manuscript_count,
            'chapters_created': chapter_count
        }
        
    except Exception as e:
        logger.warning(f"Could not get progress details: {e}")
        progress['details'] = {}
    
    return progress

@deconstruct.route('/deconstruct/results/<draft_id>', methods=['GET'])
def get_deconstruction_results(draft_id):
    """
    Get the results of a completed deconstruction pipeline.
    """
    try:
        # Get user_id from query parameters for GET request
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
                # Check if draft exists, user has permission, and is completed
                cursor.execute("""
                    SELECT d.status
                    FROM drafts d
                    INNER JOIN workspace_members wm ON d.workspace_id = wm.workspace_id
                    WHERE d.id = %s AND wm.user_id = %s
                """, (draft_id, user_id))
                result = cursor.fetchone()
                
                if not result:
                    return DeconstructorResponse.permission_denied(draft_id)
                
                status = result[0]
                
                if status != 'completed':
                    return DeconstructorResponse.invalid_status(status, 'completed')
                
                # Get summary results
                results = _get_pipeline_results_summary(cursor, draft_id)
                
                return DeconstructorResponse.pipeline_results(draft_id, results)
                
        finally:
            if conn:
                connection_pool.putconn(conn)
            
    except Exception as e:
        logger.error(f"Error getting deconstruction results: {str(e)}")
        return internal_error('Internal server error')

def _get_pipeline_results_summary(cursor, draft_id):
    """
    Get a summary of pipeline results.
    """
    results = {}
    
    try:
        # Get scene count and basic info
        cursor.execute("""
            SELECT COUNT(*), 
                   AVG(LENGTH(original_content)) as avg_scene_length
            FROM scenes WHERE draft_id = %s
        """, (draft_id,))
        scene_result = cursor.fetchone()
        results['scene_count'] = scene_result[0] if scene_result else 0
        results['avg_scene_length'] = int(scene_result[1]) if scene_result and scene_result[1] else 0
        
        # Get plot issues summary
        cursor.execute("""
            SELECT issue_type, COUNT(*) 
            FROM plot_issues 
            WHERE draft_id = %s 
            GROUP BY issue_type
        """, (draft_id,))
        issue_results = cursor.fetchall()
        results['plot_issues'] = {issue_type: count for issue_type, count in issue_results}
        
        # Get analysis reports summary
        cursor.execute("""
            SELECT report_type, COUNT(*) 
            FROM analysis_reports 
            WHERE draft_id = %s 
            GROUP BY report_type
        """, (draft_id,))
        report_results = cursor.fetchall()
        results['analysis_reports'] = {report_type: count for report_type, count in report_results}
        
        # Get chapter count if available
        cursor.execute("""
            SELECT COUNT(*) FROM chapters WHERE draft_id = %s
        """, (draft_id,))
        chapter_result = cursor.fetchone()
        results['chapter_count'] = chapter_result[0] if chapter_result else 0
        
    except Exception as e:
        logger.warning(f"Error getting results summary: {e}")
        results['error'] = 'Could not fetch complete results'
    
    return results