"""
AuditorService - Service for analyzing manuscripts and creating summaries.

This service handles:
- Chapter summarization (Record Keeper entries)
- Entity-specific summaries (Character, Location, Item, etc.)
- Incremental scanning with content hash tracking
- Record consistency checking (DB records vs story content)
- Story consistency checking (plot holes, continuity errors)
- Record optimization (duplicate detection and merging)
- Uses the same LLM infrastructure as deconstructor
"""

import logging
import json
import os
import uuid
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from services.records_manager import RecordsManager
from services.generation_engine import GenerationEngine
from models.request import BaseGenerationRequest, GenerationConfig
from models.quota import QuotaCaller
from utils.json_response_parser import JSONResponseParser

logger = logging.getLogger(__name__)


class AuditorService:
    """
    Service for manuscript analysis and summarization.
    """
    
    def __init__(self, db_pool):
        """
        Initialize the Auditor Service.
        
        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self.records_manager = RecordsManager(db_pool)
        
        logger.info("AuditorService initialized")
    
    def _create_caller(self, project_id: str, workspace_id: str = None) -> QuotaCaller:
        """
        Create a QuotaCaller for generation requests.
        Tries to get user_id from project, falls back to default if not available.
        
        Args:
            project_id: Project UUID
            workspace_id: Optional workspace UUID
            
        Returns:
            QuotaCaller instance
        """
        user_id = 1  # Default fallback
        api_keys = {}  # Will use default API keys from environment
        
        # Try to get user_id from project if workspace_id is available
        if workspace_id:
            conn = None
            try:
                conn = self.db_pool.getconn()
                with conn.cursor() as cursor:
                    # Try to get user_id from workspace_members for this workspace
                    cursor.execute("""
                        SELECT wm.user_id
                        FROM workspace_members wm
                        WHERE wm.workspace_id = %s
                        ORDER BY wm.role = 'owner' DESC, wm.created_at ASC
                        LIMIT 1
                    """, (workspace_id,))
                    result = cursor.fetchone()
                    if result:
                        user_id = result[0]
            except Exception as e:
                logger.debug(f"Could not get user_id from workspace: {e}, using default")
            finally:
                if conn:
                    self.db_pool.putconn(conn)
        
        return QuotaCaller.from_request_data(
            user_id=user_id,
            workspace_id=workspace_id or project_id,  # Fallback to project_id if workspace_id not available
            project_id=project_id,
            session_id=str(uuid.uuid4()),
            api_keys=api_keys
        )

    def _save_entity_properties_with_retry(
        self,
        project_id: str,
        vertex_id: int,
        properties: Dict[str, Any],
        operation_name: str = "save_entity_properties",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Save entity properties with retry for transient failures.

        This helper wraps records_manager.update_entity() with retry logic
        and error classification. Only DB operations are retried, not LLM calls.

        Args:
            project_id: Project UUID
            vertex_id: Entity vertex ID
            properties: Properties to save
            operation_name: Name for logging
            max_retries: Maximum retry attempts

        Returns:
            {'success': True} or {'error': '...', 'retry_possible': bool}
        """
        import time
        from utils.database_utils import classify_db_error

        initial_delay = 0.5
        delay = initial_delay

        for attempt in range(1, max_retries + 1):
            try:
                success = self.records_manager.update_entity(
                    project_id=project_id,
                    vertex_id=vertex_id,
                    properties=properties
                )

                if success:
                    if attempt > 1:
                        logger.info(f"[{operation_name}] Succeeded on attempt {attempt}")
                    return {'success': True}
                else:
                    # update_entity returned False without exception
                    # This could be a permanent issue (entity not found)
                    if attempt < max_retries:
                        logger.warning(
                            f"[{operation_name}] update_entity returned False "
                            f"(attempt {attempt}/{max_retries}), retrying..."
                        )
                        time.sleep(delay)
                        delay = min(delay * 2, 4.0)
                    else:
                        return {
                            'error': 'Failed to save entity properties after retries',
                            'retry_possible': True
                        }

            except Exception as e:
                error_type = classify_db_error(e)

                if error_type == 'permanent':
                    logger.error(f"[{operation_name}] Permanent error: {e}")
                    return {
                        'error': str(e),
                        'retry_possible': False
                    }

                # Transient error - maybe retry
                if attempt < max_retries:
                    logger.warning(
                        f"[{operation_name}] Transient error (attempt {attempt}/{max_retries}): "
                        f"{e}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 4.0)
                else:
                    logger.error(f"[{operation_name}] All {max_retries} attempts exhausted: {e}")
                    return {
                        'error': f'Database operation failed after {max_retries} attempts: {e}',
                        'retry_possible': True
                    }

        return {'error': 'Unexpected error in save operation', 'retry_possible': True}

    def _create_entity_with_retry(
        self,
        project_id: str,
        name: str,
        entity_type: str,
        properties: Dict[str, Any],
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Create a new entity with retry for transient failures.

        Args:
            project_id: Project UUID
            name: Entity name
            entity_type: Entity type
            properties: Entity properties
            max_retries: Maximum retry attempts

        Returns:
            {'success': True, 'vertex_id': ...} or {'error': '...'}
        """
        import time
        from utils.database_utils import classify_db_error

        initial_delay = 0.5
        delay = initial_delay

        for attempt in range(1, max_retries + 1):
            try:
                result = self.records_manager.create_entity(
                    project_id=project_id,
                    name=name,
                    entity_type=entity_type,
                    properties=properties
                )

                if result:
                    if attempt > 1:
                        logger.info(f"[create_entity] Succeeded on attempt {attempt}")
                    return {'success': True, 'vertex_id': result.get('vertex_id')}
                else:
                    # create_entity returned None/False without exception
                    if attempt < max_retries:
                        logger.warning(
                            f"[create_entity] Returned falsy value "
                            f"(attempt {attempt}/{max_retries}), retrying..."
                        )
                        time.sleep(delay)
                        delay = min(delay * 2, 4.0)
                    else:
                        return {'error': 'Failed to create entity after retries'}

            except Exception as e:
                error_type = classify_db_error(e)

                if error_type == 'permanent':
                    logger.error(f"[create_entity] Permanent error: {e}")
                    return {'error': str(e)}

                # Transient error - maybe retry
                if attempt < max_retries:
                    logger.warning(
                        f"[create_entity] Transient error (attempt {attempt}/{max_retries}): "
                        f"{e}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 4.0)
                else:
                    logger.error(f"[create_entity] All {max_retries} attempts exhausted: {e}")
                    return {'error': f'Failed to create entity after {max_retries} attempts: {e}'}

        return {'error': 'Unexpected error in create operation'}

    # =========================================================================
    # SCAN STATUS TRACKING
    # =========================================================================
    
    def _compute_content_hash(self, content: str) -> str:
        """Compute MD5 hash of content for change detection."""
        if not content:
            return ""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_scan_status(self, project_id: str) -> Dict[str, Any]:
        """
        Get comprehensive scan status for all chapters in a project.
        
        Tracks BOTH extraction AND summarization separately, with category details.
        
        Returns:
            {
                'chapters': {
                    0: {
                        'chapter_order': 0,
                        'chapter_name': 'Chapter 1',
                        'content_hash': 'abc123...',
                        'extraction': {
                            'done': True/False,
                            'last_at': '2025-12-04T...',
                            'categories_extracted': ['character', 'location', ...],
                            'entity_count': 15
                        },
                        'record_keeper': {
                            'done': True/False,
                            'last_at': '2025-12-04T...'
                        },
                        'category_summaries': {
                            'done': True/False,
                            'last_at': '2025-12-04T...',
                            'categories_summarized': ['character', ...]
                        },
                        'has_changes': True/False,
                        'needs_extraction': True/False,
                        'needs_summarization': True/False
                    },
                    ...
                },
                'total_chapters': 4,
                'extraction_pending': 2,
                'summarization_pending': 3
            }
        """
        try:
            # Get audit metadata entity for this project
            scan_metadata = self._get_or_create_scan_metadata(project_id)
            chapter_scans = scan_metadata.get('chapter_scans', {})
            
            # Handle case where chapter_scans is a JSON string (from AGE storage)
            if isinstance(chapter_scans, str):
                try:
                    chapter_scans = json.loads(chapter_scans)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(f"Failed to parse chapter_scans JSON, using empty dict")
                    chapter_scans = {}
            
            # Ensure it's a dict
            if not isinstance(chapter_scans, dict):
                chapter_scans = {}
            
            # Get current chapters to detect changes
            chapters = self.get_chapters(project_id)
            
            # Get current entities to verify extraction data still exists
            current_entities = self.records_manager.get_project_entities(project_id)
            current_entity_count = len([e for e in current_entities 
                                       if not e.get('type', '').startswith('_')
                                       and e.get('type', '').lower() != 'record_keeper'])
            current_entity_names = set(e.get('name', '').lower() for e in current_entities)
            
            # Get current record keeper entries to verify they exist
            record_keeper_entries = self.records_manager.get_project_entities(project_id, entity_type="record_keeper")
            record_keeper_chapters = set()
            for rk in record_keeper_entries:
                chapter_num = rk.get('properties', {}).get('chapter_number')
                if chapter_num:
                    record_keeper_chapters.add(str(chapter_num))
            
            result = {
                'chapters': {},
                'total_chapters': len(chapters),
                'extraction_pending': 0,
                'summarization_pending': 0,
                'data_warnings': 0,  # Count of chapters with deleted/modified data
                # Legacy fields for backwards compatibility
                'chapters_with_changes': 0,
                'chapters_not_scanned': 0
            }
            
            for chapter in chapters:
                chapter_order = chapter.get('order', 0)
                chapter_name = chapter.get('chapter_name', f"Chapter {chapter_order + 1}")
                current_content = chapter.get('content', '')
                current_hash = self._compute_content_hash(current_content)
                
                # Get previous scan data
                prev_scan = chapter_scans.get(str(chapter_order), {})
                if isinstance(prev_scan, str):
                    try:
                        prev_scan = json.loads(prev_scan)
                    except:
                        prev_scan = {}
                
                prev_hash = prev_scan.get('content_hash', '')
                has_changes = current_hash != prev_hash if prev_hash else True
                
                # Extraction status
                extraction_done = bool(prev_scan.get('last_extraction_at'))
                categories_extracted = prev_scan.get('categories_extracted', [])
                entity_count = prev_scan.get('entity_count', 0)
                entities_extracted_names = prev_scan.get('entities_extracted', [])
                
                # Record keeper summarization status
                record_keeper_done = bool(prev_scan.get('last_record_keeper_at'))
                
                # Category-specific summarization status
                category_summaries_done = bool(prev_scan.get('last_category_summary_at'))
                categories_summarized = prev_scan.get('categories_summarized', [])
                
                # VERIFICATION: Check if extracted data still exists
                extraction_warning = None
                if extraction_done and entity_count > 0:
                    # Check if entities were deleted
                    if current_entity_count == 0:
                        extraction_warning = "All extracted entities have been deleted"
                    elif entity_count > current_entity_count + 5:  # Allow some tolerance
                        extraction_warning = f"Many entities deleted ({entity_count} extracted → {current_entity_count} remaining)"
                    elif entities_extracted_names:
                        # Check if specific extracted entities still exist
                        missing_count = sum(1 for name in entities_extracted_names[:10] 
                                          if name.lower() not in current_entity_names)
                        if missing_count > len(entities_extracted_names[:10]) // 2:
                            extraction_warning = f"Some extracted entities have been deleted"
                
                # VERIFICATION: Check if record keeper entry exists
                record_keeper_warning = None
                chapter_num_str = str(chapter_order + 1)  # Chapter numbers are 1-based in RK
                if record_keeper_done:
                    if chapter_num_str not in record_keeper_chapters:
                        record_keeper_warning = "Record Keeper entry has been deleted"
                
                # Determine what needs to be done
                needs_extraction = not extraction_done or has_changes
                needs_summarization = not record_keeper_done or has_changes
                
                # Add warnings to pending count
                has_warning = bool(extraction_warning or record_keeper_warning)
                if has_warning:
                    result['data_warnings'] += 1
                
                if needs_extraction:
                    result['extraction_pending'] += 1
                if needs_summarization:
                    result['summarization_pending'] += 1
                
                # Legacy fields
                if has_changes:
                    result['chapters_with_changes'] += 1
                if not extraction_done:
                    result['chapters_not_scanned'] += 1
                
                result['chapters'][chapter_order] = {
                    'chapter_order': chapter_order,
                    'chapter_name': chapter_name,
                    'current_content_hash': current_hash,
                    'stored_content_hash': prev_hash,
                    'has_changes': has_changes,
                    'has_warning': has_warning,
                    'content_length': len(current_content) if current_content else 0,
                    
                    # Detailed extraction status
                    'extraction': {
                        'done': extraction_done,
                        'last_at': prev_scan.get('last_extraction_at'),
                        'categories_extracted': categories_extracted,
                        'entity_count': entity_count,
                        'warning': extraction_warning  # NEW: Warning if data deleted
                    },
                    
                    # Record keeper summarization status
                    'record_keeper': {
                        'done': record_keeper_done,
                        'last_at': prev_scan.get('last_record_keeper_at'),
                        'warning': record_keeper_warning  # NEW: Warning if RK deleted
                    },
                    
                    # Category-specific summarization status
                    'category_summaries': {
                        'done': category_summaries_done,
                        'last_at': prev_scan.get('last_category_summary_at'),
                        'categories_summarized': categories_summarized
                    },
                    
                    # What needs to be done
                    'needs_extraction': needs_extraction,
                    'needs_summarization': needs_summarization,
                    
                    # Legacy fields for backwards compatibility
                    'last_extraction_at': prev_scan.get('last_extraction_at'),
                    'last_summarization_at': prev_scan.get('last_record_keeper_at'),
                    'entities_extracted': prev_scan.get('entities_extracted', []),
                    'not_scanned': not extraction_done
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting scan status: {e}", exc_info=True)
            return {'error': str(e)}
    
    def _get_or_create_scan_metadata(self, project_id: str) -> Dict[str, Any]:
        """Get or create scan metadata entity for tracking scan status."""
        try:
            # Look for existing _scan_metadata entity
            entities = self.records_manager.get_project_entities(project_id, entity_type="_scan_metadata")
            
            if entities:
                return entities[0].get('properties', {})
            
            # Create new metadata entity
            metadata = {
                'chapter_scans': {},
                'created_at': datetime.utcnow().isoformat(),
                'version': 1
            }
            
            # IMPORTANT: Don't specify vertex_label - let it be auto-generated from entity_type
            # entity_type="_scan_metadata" will become vertex_label="ScanMetadata"
            # This ensures consistency between create and query
            vertex_id = self.records_manager.create_entity(
                project_id=project_id,
                entity_name="_AuditScanMetadata",
                entity_type="_scan_metadata",
                properties=metadata
            )
            
            if vertex_id:
                logger.info(f"Created scan metadata entity for project {project_id}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting/creating scan metadata: {e}")
            return {'chapter_scans': {}}
    
    def _update_scan_metadata(
        self, 
        project_id: str, 
        chapter_order: int,
        content_hash: str,
        scan_type: str,  # 'extraction', 'record_keeper', or 'category_summary'
        entities_found: Optional[List[str]] = None,
        categories_processed: Optional[List[str]] = None,
        entity_count: int = 0
    ):
        """
        Update scan metadata after processing a chapter.
        
        Args:
            project_id: Project UUID
            chapter_order: Chapter index (0-based)
            content_hash: Hash of chapter content
            scan_type: Type of scan performed:
                - 'extraction': Entity extraction
                - 'record_keeper': Record keeper summarization
                - 'category_summary': Category-specific summarization
            entities_found: List of entity names found (for extraction)
            categories_processed: List of categories processed (for extraction/summary)
            entity_count: Number of entities extracted
        """
        try:
            # Get existing metadata
            entities = self.records_manager.get_project_entities(project_id, entity_type="_scan_metadata")
            
            if not entities:
                # Create if doesn't exist
                self._get_or_create_scan_metadata(project_id)
                entities = self.records_manager.get_project_entities(project_id, entity_type="_scan_metadata")
            
            if entities:
                entity = entities[0]
                props = entity.get('properties', {})
                chapter_scans = props.get('chapter_scans', {})
                
                # Handle case where chapter_scans is a JSON string (from AGE storage)
                if isinstance(chapter_scans, str):
                    try:
                        chapter_scans = json.loads(chapter_scans)
                    except (json.JSONDecodeError, TypeError):
                        chapter_scans = {}
                
                if not isinstance(chapter_scans, dict):
                    chapter_scans = {}
                
                # Update chapter scan data
                chapter_key = str(chapter_order)
                if chapter_key not in chapter_scans:
                    chapter_scans[chapter_key] = {}
                
                chapter_scans[chapter_key]['content_hash'] = content_hash
                
                timestamp = datetime.utcnow().isoformat()
                
                if scan_type == 'extraction':
                    chapter_scans[chapter_key]['last_extraction_at'] = timestamp
                    if entities_found:
                        chapter_scans[chapter_key]['entities_extracted'] = entities_found
                    if categories_processed:
                        # Merge with existing categories
                        existing_cats = chapter_scans[chapter_key].get('categories_extracted', [])
                        all_cats = list(set(existing_cats + categories_processed))
                        chapter_scans[chapter_key]['categories_extracted'] = all_cats
                    chapter_scans[chapter_key]['entity_count'] = entity_count
                    
                elif scan_type == 'record_keeper':
                    chapter_scans[chapter_key]['last_record_keeper_at'] = timestamp
                    # Also update legacy field for backwards compatibility
                    chapter_scans[chapter_key]['last_summarization_at'] = timestamp
                    
                elif scan_type == 'category_summary':
                    chapter_scans[chapter_key]['last_category_summary_at'] = timestamp
                    if categories_processed:
                        # Merge with existing categories
                        existing_cats = chapter_scans[chapter_key].get('categories_summarized', [])
                        all_cats = list(set(existing_cats + categories_processed))
                        chapter_scans[chapter_key]['categories_summarized'] = all_cats
                
                props['chapter_scans'] = chapter_scans
                props['last_updated_at'] = timestamp
                
                # Save updated metadata
                self.records_manager.update_entity(
                    project_id=project_id,
                    vertex_id=entity.get('vertex_id'),
                    properties=props
                )
                
                logger.debug(f"Updated scan metadata for chapter {chapter_order} ({scan_type})")
                
        except Exception as e:
            logger.error(f"Error updating scan metadata: {e}", exc_info=True)
    
    def get_chapters_to_process(
        self, 
        project_id: str, 
        workspace_id: str = None,
        mode: str = "incremental"  # "incremental", "full", or "new_only"
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get chapters that need processing based on scan mode.
        
        Args:
            project_id: Project UUID
            workspace_id: Workspace UUID
            mode: 
                - "incremental": Only chapters with changes or never scanned
                - "full": All chapters (rescan)
                - "new_only": Only chapters never scanned before
        
        Returns:
            Tuple of (chapters_to_process, scan_info)
        """
        all_chapters = self.get_chapters(project_id, workspace_id)
        scan_status = self.get_scan_status(project_id)
        
        if 'error' in scan_status:
            return all_chapters, {'mode': mode, 'reason': 'scan_status_error'}
        
        chapters_to_process = []
        
        for chapter in all_chapters:
            chapter_order = chapter.get('order', 0)
            chapter_scan = scan_status['chapters'].get(chapter_order, {})
            
            should_process = False
            
            if mode == "full":
                should_process = True
            elif mode == "new_only":
                should_process = chapter_scan.get('not_scanned', True)
            elif mode == "incremental":
                should_process = chapter_scan.get('has_changes', True) or chapter_scan.get('not_scanned', True)
            
            if should_process:
                chapters_to_process.append(chapter)
        
        scan_info = {
            'mode': mode,
            'total_chapters': len(all_chapters),
            'chapters_to_process': len(chapters_to_process),
            'chapters_skipped': len(all_chapters) - len(chapters_to_process)
        }
        
        logger.info(f"Scan mode '{mode}': {scan_info['chapters_to_process']}/{scan_info['total_chapters']} chapters to process")
        
        return chapters_to_process, scan_info
    
    # =========================================================================
    # CONSISTENCY CHECKING
    # =========================================================================
    
    def check_record_consistency(
        self,
        project_id: str,
        workspace_id: str,
        categories: Optional[List[str]] = None,
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Check consistency between database records and story content.
        
        Identifies:
        - Contradictions: DB says X but story shows Y
        - Outdated info: Story has evolved but records don't reflect it
        - Missing updates: New information not captured in records
        
        Returns:
            {
                'issues': [
                    {
                        'entity_name': 'Yurak',
                        'entity_type': 'character',
                        'issue_type': 'contradiction' | 'outdated' | 'missing_update',
                        'field': 'traits',
                        'db_value': '...',
                        'story_evidence': '...',
                        'severity': 'high' | 'medium' | 'low',
                        'suggestion': '...'
                    }
                ],
                'entities_checked': 10,
                'issues_found': 3
            }
        """
        try:
            results = {
                'issues': [],
                'entities_checked': 0,
                'issues_found': 0,
                'categories_checked': []
            }
            
            # Get all entities
            all_entities = self.records_manager.get_project_entities(project_id)
            if not all_entities:
                return {**results, 'message': 'No entities found to check'}
            
            # Filter by categories if specified
            if categories:
                all_entities = [e for e in all_entities 
                              if e.get('type', '').lower() in [c.lower() for c in categories]]
            
            # Exclude metadata entities
            all_entities = [e for e in all_entities 
                          if not e.get('type', '').startswith('_') 
                          and e.get('type', '').lower() != 'record_keeper']
            
            if not all_entities:
                return {**results, 'message': 'No entities match criteria'}
            
            # Get all chapter content
            chapters = self.get_chapters(project_id, workspace_id)
            manuscript_content = "\n\n".join([
                f"--- {ch.get('chapter_name', 'Chapter')} ---\n{ch.get('content', '')}"
                for ch in chapters if ch.get('content')
            ])
            
            if not manuscript_content.strip():
                return {**results, 'error': 'No chapter content available'}
            
            # Create caller
            caller = self._create_caller(project_id, workspace_id)
            
            # Check entities in batches
            batch_size = 5
            for i in range(0, len(all_entities), batch_size):
                batch = all_entities[i:i+batch_size]
                
                # Build entity info for prompt - INCLUDING summaries for arc context
                entities_info = []
                for entity in batch:
                    props = entity.get('properties', {})
                    
                    # Include summaries to show the entity's journey
                    summaries = props.get('_summaries', [])
                    summaries_text = ""
                    if summaries and isinstance(summaries, list):
                        summaries_text = "\n".join([
                            f"  - Chapter {s.get('chapter_number', '?')}: {s.get('activity', 'No activity recorded')[:200]}"
                            for s in summaries if s
                        ])
                    
                    entity_info = {
                        'name': entity.get('name'),
                        'type': entity.get('type'),
                        'current_properties': {k: v for k, v in props.items()
                                              if not k.startswith('_')},
                        'chapter_journey': summaries_text if summaries_text else "No chapter summaries available"
                    }
                    entities_info.append(entity_info)
                
                prompt = f"""You are an ARC-AWARE consistency checker for a narrative database. Your job is to distinguish between:
- ACTUAL ERRORS (contradictions, mistakes)
- INTENTIONAL CHARACTER DEVELOPMENT (arcs, growth, change)

STORED ENTITY RECORDS (with their chapter journey):
{json.dumps(entities_info, indent=2)}

STORY CONTENT:
{manuscript_content[:15000]}

CRITICAL UNDERSTANDING - CHARACTER DEVELOPMENT IS NOT AN ERROR:
Stories involve change. Characters grow, fall, transform. A character who starts "brave" but becomes "cowardly" after trauma is NOT a contradiction - it's CHARACTER DEVELOPMENT.

Before flagging anything, ask yourself:
1. Does the entity's "chapter_journey" show a progression that explains the change?
2. Is there a story event (betrayal, loss, revelation) that would cause this change?
3. Is this intentional narrative arc or an actual database error?

ONLY FLAG AS ISSUES:
1. CONTRADICTIONS (ACTUAL ERRORS):
   - DB says character has blue eyes, story says brown eyes (physical detail error)
   - DB says character is "dead" but they appear alive with no resurrection explanation
   - DB says location is in the North, story places it in the South
   
2. OUTDATED INFO (needs refresh, not an error):
   - Properties reflect early-story state but story has progressed significantly
   - Mark as "outdated" NOT "contradiction" - these need refresh, not correction
   
3. MISSING UPDATES:
   - Major new information revealed that should be captured
   - New relationships, new abilities, new affiliations

DO NOT FLAG:
- Character trait changes that result from story events (brave → cowardly after trauma)
- Emotional state changes (determined → hopeless after loss)
- Relationship changes (ally → enemy after betrayal)
- Any change that can be explained by narrative progression

OUTPUT FORMAT (JSON array):
[
  {{
    "entity_name": "Name",
    "entity_type": "type",
    "issue_type": "contradiction" | "outdated" | "missing_update",
    "field": "affected field name",
    "current_db_value": "what the database says",
    "story_evidence": "quote or description from story",
    "is_character_development": false,
    "severity": "high" | "medium" | "low",
    "suggestion": "recommended action"
  }}
]

If no ACTUAL issues found (character development doesn't count), return: []

ANALYSIS:"""

                # Generate analysis
                request = BaseGenerationRequest(
                    prompt=prompt,
                    provider=provider,
                    model=model,
                    instruction="Check entity consistency and return JSON array of issues.",
                    generation_config=GenerationConfig(
                        temperature=0.3,  # Lower temp for accuracy
                        max_output_tokens=3000,
                    ),
                    caller=caller
                )
                
                engine = GenerationEngine(request)
                response = engine.generate(skip_quota=True)
                
                if response.success:
                    try:
                        issues, _ = JSONResponseParser.parse_response(
                            response.text,
                            expected_type="list",
                            fallback_value=[]
                        )
                        
                        if issues:
                            results['issues'].extend(issues)
                            results['issues_found'] += len(issues)
                    except Exception as e:
                        logger.warning(f"Error parsing consistency check response: {e}")
                
                results['entities_checked'] += len(batch)
            
            # Track which categories were checked
            results['categories_checked'] = list(set(e.get('type') for e in all_entities))
            
            return results
            
        except Exception as e:
            logger.error(f"Error in check_record_consistency: {e}", exc_info=True)
            return {'error': str(e)}
    
    def check_story_consistency(
        self,
        project_id: str,
        workspace_id: str,
        check_types: Optional[List[str]] = None,  # ['plot_holes', 'timeline', 'character', 'continuity']
        model: str = "gemini-2.5-flash",
        provider: str = "gemini",
        chapter_orders: Optional[List[int]] = None  # Optional: specific chapters to check
    ) -> Dict[str, Any]:
        """
        Check story itself for internal consistency issues.
        
        For large stories, processes in chunks to handle full content.
        
        Identifies:
        - Plot holes: Unresolved threads, unexplained events
        - Timeline issues: Events in wrong order, impossible timing
        - Character consistency: Personality shifts, knowledge inconsistencies
        - Continuity errors: Objects appearing/disappearing, changed details
        
        Returns:
            {
                'issues': [...],
                'chapters_analyzed': 4,
                'issues_by_type': {'plot_holes': 2, 'timeline': 1, ...}
            }
        """
        import time
        
        try:
            if check_types is None:
                check_types = ['plot_holes', 'timeline', 'character', 'continuity']
            
            results = {
                'issues': [],
                'chapters_analyzed': 0,
                'issues_by_type': {t: 0 for t in check_types}
            }
            
            # Get chapters
            all_chapters = self.get_chapters(project_id, workspace_id)
            if not all_chapters:
                return {**results, 'error': 'No chapters found'}
            
            # Filter chapters if specific ones requested
            if chapter_orders is not None:
                chapters = [ch for ch in all_chapters if ch.get('order') in chapter_orders]
            else:
                chapters = all_chapters
            
            if not chapters:
                return {**results, 'error': 'No chapters match criteria'}
            
            results['chapters_analyzed'] = len(chapters)
            
            # Build chapter content with markers
            chapter_contents = []
            total_chars = 0
            for ch in chapters:
                chapter_num = ch.get('order', 0) + 1
                chapter_name = ch.get('chapter_name', f'Chapter {chapter_num}')
                content = ch.get('content', '')
                if content:
                    chapter_text = f"=== CHAPTER {chapter_num}: {chapter_name} ===\n{content}"
                    chapter_contents.append({
                        'order': ch.get('order', 0),
                        'name': chapter_name,
                        'text': chapter_text,
                        'chars': len(chapter_text)
                    })
                    total_chars += len(chapter_text)
            
            if not chapter_contents:
                return {**results, 'error': 'No chapter content available'}
            
            # Create caller
            caller = self._create_caller(project_id, workspace_id)
            
            # Build check type descriptions
            check_descriptions = {
                'plot_holes': "PLOT HOLES: Unresolved plot threads, Chekhov's guns that never fire, unexplained events, forgotten storylines",
                'timeline': "TIMELINE ISSUES: Events in impossible order, characters in two places at once, time passing inconsistently",
                'character': "CHARACTER CONSISTENCY: Sudden personality changes without explanation, characters knowing things they shouldn't, forgotten skills or relationships",
                'continuity': "CONTINUITY ERRORS: Items appearing/disappearing, physical details changing (eye color, locations of wounds), environmental changes"
            }
            
            checks_to_do = "\n".join([f"- {check_descriptions[t]}" for t in check_types if t in check_descriptions])
            
            # Determine chunk strategy based on total content size
            # Modern Gemini can handle ~1M tokens, but we'll be conservative at ~100k chars per chunk
            MAX_CHARS_PER_CHUNK = 80000
            
            if total_chars <= MAX_CHARS_PER_CHUNK:
                # Small story - process all at once
                logger.info(f"Story consistency: Processing {len(chapters)} chapters ({total_chars} chars) in single pass")
                manuscript = "\n\n".join([ch['text'] for ch in chapter_contents])
                
                all_issues = self._analyze_consistency_chunk(
                    manuscript=manuscript,
                    checks_to_do=checks_to_do,
                    check_types=check_types,
                    caller=caller,
                    model=model,
                    provider=provider,
                    chunk_info=None
                )
                results['issues'] = all_issues
            else:
                # Large story - process in chunks with context
                logger.info(f"Story consistency: Processing {len(chapters)} chapters ({total_chars} chars) in chunks")
                
                # Build chunks - try to keep ~3-4 chapters per chunk, but respect char limit
                chunks = []
                current_chunk = []
                current_chars = 0
                
                for ch in chapter_contents:
                    if current_chars + ch['chars'] > MAX_CHARS_PER_CHUNK and current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = [ch]
                        current_chars = ch['chars']
                    else:
                        current_chunk.append(ch)
                        current_chars += ch['chars']
                
                if current_chunk:
                    chunks.append(current_chunk)
                
                logger.info(f"Story consistency: Split into {len(chunks)} chunks")
                
                # Build summaries of previous chunks for context
                chunk_summaries = []
                
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_num = chunk_idx + 1
                    chapter_range = f"Chapters {chunk[0]['order']+1}-{chunk[-1]['order']+1}"
                    logger.info(f"Story consistency: Analyzing chunk {chunk_num}/{len(chunks)} ({chapter_range})")
                    
                    manuscript = "\n\n".join([ch['text'] for ch in chunk])
                    
                    # Add context from previous chunks
                    context = ""
                    if chunk_summaries:
                        context = "PREVIOUS STORY CONTEXT:\n" + "\n".join(chunk_summaries[-3:]) + "\n\n"  # Last 3 summaries
                    
                    chunk_issues = self._analyze_consistency_chunk(
                        manuscript=context + manuscript,
                        checks_to_do=checks_to_do,
                        check_types=check_types,
                        caller=caller,
                        model=model,
                        provider=provider,
                        chunk_info=f"Chunk {chunk_num}/{len(chunks)}: {chapter_range}"
                    )
                    
                    results['issues'].extend(chunk_issues)
                    
                    # Generate summary for next chunk's context
                    summary = f"[{chapter_range}]: Main events in these chapters."
                    chunk_summaries.append(summary)
                    
                    # Small delay between chunks
                    if chunk_idx < len(chunks) - 1:
                        time.sleep(0.5)
            
            # Count issues by type
            for issue in results['issues']:
                issue_type = issue.get('issue_type', 'unknown')
                if issue_type in results['issues_by_type']:
                    results['issues_by_type'][issue_type] += 1
            
            logger.info(f"Story consistency complete: Found {len(results['issues'])} issues")
            return results
            
        except Exception as e:
            logger.error(f"Error in check_story_consistency: {e}", exc_info=True)
            return {'error': str(e)}
    
    def _analyze_consistency_chunk(
        self,
        manuscript: str,
        checks_to_do: str,
        check_types: List[str],
        caller,
        model: str,
        provider: str,
        chunk_info: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Analyze a chunk of the story for consistency issues."""
        
        prompt = f"""You are a professional story editor checking for consistency issues in a manuscript.

MANUSCRIPT:
{manuscript}

CHECK FOR THESE ISSUES:
{checks_to_do}

TASK: Read through the story carefully and identify any consistency problems. Be specific about where issues occur.

OUTPUT FORMAT (JSON array):
[
  {{
    "issue_type": "plot_holes" | "timeline" | "character" | "continuity",
    "title": "Brief title for the issue",
    "description": "Detailed explanation of the inconsistency",
    "location": "Chapter X" or "Between Chapter X and Y",
    "evidence": "Specific quotes or references from the text",
    "severity": "critical" | "major" | "minor",
    "suggestion": "How this could be fixed"
  }}
]

If no issues found, return an empty array: []

IMPORTANT:
- Only report actual inconsistencies, not stylistic preferences
- Be specific with evidence from the text
- Consider that some apparent inconsistencies might be intentional (unreliable narrator, character lying, etc.)

ANALYSIS:"""
        
        try:
            # Generate analysis
            request = BaseGenerationRequest(
                prompt=prompt,
                provider=provider,
                model=model,
                instruction="Check story consistency and return JSON array of issues.",
                generation_config=GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=4000,
                ),
                caller=caller
            )
            
            engine = GenerationEngine(request)
            response = engine.generate(skip_quota=True)
            
            if response.success:
                try:
                    issues, _ = JSONResponseParser.parse_response(
                        response.text,
                        expected_type="list",
                        fallback_value=[]
                    )
                    
                    if issues:
                        if chunk_info:
                            logger.info(f"  {chunk_info}: Found {len(issues)} issues")
                        return issues
                except Exception as e:
                    logger.warning(f"Error parsing story consistency response: {e}")
            
            return []
            
        except Exception as e:
            logger.warning(f"Error in _analyze_consistency_chunk: {e}")
            return []
    
    # =========================================================================
    # PROPERTY REFRESH (Arc-Aware Updates)
    # =========================================================================
    
    def refresh_entity_properties(
        self,
        project_id: str,
        workspace_id: str,
        vertex_id: str,
        model: str = "gemini-2.5-flash",
        provider: str = "gemini",
        entity_data: Optional[Dict[str, Any]] = None,
        chapters_cache: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Refresh an entity's properties to reflect its CURRENT state in the story.
        
        This is arc-aware: it understands that characters/entities change over time
        and updates properties to reflect where they are NOW in the narrative.
        
        Also tracks property changes with timestamps and reasons.
        
        Args:
            project_id: Project UUID
            workspace_id: Workspace UUID
            vertex_id: Entity vertex ID to refresh
            model: AI model to use
            provider: AI provider
            entity_data: Optional pre-fetched entity data (avoids extra DB call)
            chapters_cache: Optional pre-fetched chapters (avoids extra DB call)
            
        Returns:
            {
                'success': True,
                'entity_name': 'Yurak',
                'properties_changed': ['emotional_state', 'traits'],
                'changes': [
                    {
                        'field': 'emotional_state',
                        'old_value': 'determined',
                        'new_value': 'broken',
                        'reason': 'After capture by Akheatoon in Chapter 2',
                        'chapter_reference': 2
                    }
                ]
            }
        """
        try:
            # Use pre-fetched entity data if provided, otherwise fetch
            if entity_data:
                entity = entity_data
            else:
                all_entities = self.records_manager.get_project_entities(project_id)
                entity = None
                for e in all_entities:
                    if str(e.get('vertex_id')) == str(vertex_id):
                        entity = e
                        break
            
            if not entity:
                return {'error': f'Entity with vertex_id {vertex_id} not found'}
            
            entity_name = entity.get('name')
            entity_type = entity.get('type')
            current_props = entity.get('properties', {})
            
            # Use cached chapters if provided, otherwise fetch
            chapters = chapters_cache if chapters_cache else self.get_chapters(project_id, workspace_id)
            if not chapters:
                return {'error': 'No chapters found'}
            
            # Build manuscript with chapter markers
            manuscript_parts = []
            for ch in chapters:
                chapter_num = ch.get('order', 0) + 1
                chapter_name = ch.get('chapter_name', f'Chapter {chapter_num}')
                content = ch.get('content', '')
                if content:
                    manuscript_parts.append(f"=== CHAPTER {chapter_num}: {chapter_name} ===\n{content}")
            
            manuscript = "\n\n".join(manuscript_parts)
            
            if not manuscript.strip():
                return {'error': 'No chapter content available'}
            
            # Get existing summaries for context
            summaries = current_props.get('_summaries', [])
            summaries_context = ""
            if summaries and isinstance(summaries, list):
                summaries_context = "\n".join([
                    f"Chapter {s.get('chapter_number', '?')}: {s.get('activity', 'Unknown')}"
                    for s in summaries if s
                ])
            
            # Build prompt for property refresh
            # Filter out internal properties for the prompt
            display_props = {k: v for k, v in current_props.items() if not k.startswith('_')}
            
            # Build comprehensive chapter content - prioritize last chapter (current state)
            # and include key excerpts from earlier chapters
            total_chapters = len(chapters)
            chapter_content_parts = []
            
            # Calculate budget per chapter, giving more to the last chapter
            total_budget = 25000  # Total chars for story content
            if total_chapters == 1:
                last_chapter_budget = total_budget
                early_chapter_budget = 0
            else:
                last_chapter_budget = min(15000, total_budget // 2)  # Last chapter gets half
                early_chapter_budget = (total_budget - last_chapter_budget) // max(1, total_chapters - 1)
            
            for i, ch in enumerate(chapters):
                ch_num = ch.get('order', i) + 1
                ch_name = ch.get('chapter_name', f'Chapter {ch_num}')
                content = ch.get('content', '')
                
                if i == total_chapters - 1:
                    # Last chapter - include more content (current state)
                    excerpt = content[:last_chapter_budget] if content else ""
                    if len(content) > last_chapter_budget:
                        excerpt += f"\n[... {len(content) - last_chapter_budget} more chars ...]"
                else:
                    # Earlier chapters - include beginning and end excerpts
                    if len(content) <= early_chapter_budget:
                        excerpt = content
                    else:
                        half = early_chapter_budget // 2
                        excerpt = content[:half] + f"\n[... middle section ...]\n" + content[-half:]
                
                if excerpt:
                    chapter_content_parts.append(f"=== CHAPTER {ch_num}: {ch_name} ===\n{excerpt}")
            
            story_content = "\n\n".join(chapter_content_parts)
            
            prompt = f"""You are analyzing a {entity_type} entity to determine its CURRENT state at the END of the available story content.

ENTITY: {entity_name}
TYPE: {entity_type}

CURRENT DATABASE PROPERTIES:
{json.dumps(display_props, indent=2)}

=== ENTITY'S JOURNEY (CHAPTER SUMMARIES - CRITICAL FOR UNDERSTANDING ARC) ===
{summaries_context if summaries_context else "No chapter summaries available - analyze from story content below"}

=== STORY CONTENT (Total {total_chapters} chapters) ===
{story_content}

TASK: Based on where the story CURRENTLY ENDS (Chapter {total_chapters}), determine what this entity's properties should be NOW.

IMPORTANT: 
- The chapter summaries above show this entity's COMPLETE journey through ALL chapters
- Properties should reflect their state at the END of the LAST chapter, not earlier
- Consider how they've CHANGED from the beginning to NOW
- Focus on: emotional_state, traits, status, relationships, physical state, goals

For each property that needs updating, explain:
- What it was (initial/early value)  
- What it should be NOW (current state at end of Chapter {total_chapters})
- WHY it changed (specific story event)
- Which chapter caused the change

OUTPUT FORMAT (JSON):
{{
  "current_chapter": {total_chapters},
  "updated_properties": {{
    "property_name": "new current value",
    "another_property": "new current value"
  }},
  "changes": [
    {{
      "field": "property name",
      "old_value": "what it was",
      "new_value": "what it should be now",
      "reason": "specific story event that caused this change",
      "chapter_reference": <chapter number where change occurred>
    }}
  ],
  "initial_state_backup": {{
    "property_name": "original value from start of story"
  }}
}}

If NO changes needed (entity is already up-to-date), return:
{{
  "current_chapter": {total_chapters},
  "updated_properties": {{}},
  "changes": [],
  "message": "Entity properties are current"
}}

ANALYSIS:"""

            # Create caller and generate
            caller = self._create_caller(project_id, workspace_id)
            
            request = BaseGenerationRequest(
                prompt=prompt,
                provider=provider,
                model=model,
                instruction=f"Analyze {entity_name}'s current state at the END of Chapter {total_chapters} and return JSON with updated properties.",
                generation_config=GenerationConfig(
                    temperature=0.3,  # Lower temperature for more consistent analysis
                    max_output_tokens=3000,  # More tokens for comprehensive changes
                ),
                caller=caller
            )
            
            engine = GenerationEngine(request)
            response = engine.generate(skip_quota=True)
            
            if not response.success:
                return {'error': f'Failed to analyze entity: {response.error_message}'}
            
            # Parse response
            try:
                analysis, _ = JSONResponseParser.parse_response(
                    response.text,
                    expected_type="dict",
                    fallback_value={}
                )
                
                updated_properties = analysis.get('updated_properties', {})
                changes = analysis.get('changes', [])
                initial_backup = analysis.get('initial_state_backup', {})
                
                if not updated_properties and not changes:
                    return {
                        'success': True,
                        'entity_name': entity_name,
                        'message': 'No updates needed - entity is current',
                        'properties_changed': [],
                        'changes': []
                    }
                
                # Build new properties
                new_props = dict(current_props)
                
                # Store initial state backup (only if not already stored)
                if initial_backup and '_initial_properties' not in new_props:
                    new_props['_initial_properties'] = initial_backup
                
                # Track property changes - ensure it's a list, not a JSON string
                if '_property_changes' not in new_props:
                    new_props['_property_changes'] = []
                elif isinstance(new_props['_property_changes'], str):
                    # Parse if stored as JSON string in database
                    try:
                        new_props['_property_changes'] = json.loads(new_props['_property_changes'])
                    except (json.JSONDecodeError, TypeError):
                        new_props['_property_changes'] = []
                
                # Also parse _initial_properties if it's a string
                if '_initial_properties' in new_props and isinstance(new_props['_initial_properties'], str):
                    try:
                        new_props['_initial_properties'] = json.loads(new_props['_initial_properties'])
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Apply updates and track changes
                properties_changed = []
                for field, new_value in updated_properties.items():
                    if field.startswith('_'):
                        continue  # Don't overwrite internal properties
                    
                    old_value = new_props.get(field)
                    if old_value != new_value:
                        # Find the change reason from the changes array
                        change_reason = None
                        chapter_ref = None
                        for change in changes:
                            if change.get('field') == field:
                                change_reason = change.get('reason', 'Property updated based on story progression')
                                chapter_ref = change.get('chapter_reference')
                                break
                        
                        # Record the change
                        change_record = {
                            'field': field,
                            'old_value': old_value,
                            'new_value': new_value,
                            'reason': change_reason or 'Updated to current story state',
                            'chapter_reference': chapter_ref,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                        new_props['_property_changes'].append(change_record)
                        
                        # Apply the update
                        new_props[field] = new_value
                        properties_changed.append(field)
                
                # Save updated entity with retry
                vid = int(vertex_id) if isinstance(vertex_id, str) else vertex_id
                save_result = self._save_entity_properties_with_retry(
                    project_id=project_id,
                    vertex_id=vid,
                    properties=new_props,
                    operation_name="refresh_entity_properties"
                )

                if save_result.get('success'):
                    return {
                        'success': True,
                        'entity_name': entity_name,
                        'properties_changed': properties_changed,
                        'changes': changes,
                        'current_chapter': analysis.get('current_chapter')
                    }
                else:
                    return {'error': save_result.get('error', 'Failed to save updated properties')}
                    
            except Exception as e:
                logger.error(f"Error parsing property refresh response: {e}")
                return {'error': f'Failed to parse analysis: {str(e)}'}
            
        except Exception as e:
            logger.error(f"Error in refresh_entity_properties: {e}", exc_info=True)
            return {'error': str(e)}
    
    def refresh_all_entities_properties(
        self,
        project_id: str,
        workspace_id: str,
        categories: Optional[List[str]] = None,
        entity_ids: Optional[List[str]] = None,
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Refresh properties for all entities (or filtered by category/entity_ids) to current story state.
        
        Args:
            project_id: Project UUID
            workspace_id: Workspace UUID
            categories: Optional list of categories to filter
            entity_ids: Optional list of specific entity vertex_ids to process
            model: AI model
            provider: AI provider
            
        Returns:
            Summary of all refreshes performed
        """
        import time
        
        try:
            results = {
                'entities_processed': 0,
                'entities_updated': 0,
                'entities_unchanged': 0,
                'errors': [],
                'changes_by_entity': {},
                'total_entities': 0
            }
            
            # OPTIMIZATION: Fetch all entities ONCE at the beginning
            all_entities = self.records_manager.get_project_entities(project_id)
            if not all_entities:
                return {**results, 'message': 'No entities found'}
            
            # Filter by specific entity_ids if specified
            if entity_ids:
                entity_ids_set = set(str(eid) for eid in entity_ids)
                all_entities = [e for e in all_entities 
                              if str(e.get('vertex_id')) in entity_ids_set]
            # Otherwise filter by categories if specified
            elif categories:
                all_entities = [e for e in all_entities 
                              if e.get('type', '').lower() in [c.lower() for c in categories]]
            
            # Exclude metadata entities and record keeper
            all_entities = [e for e in all_entities 
                          if not e.get('type', '').startswith('_')
                          and e.get('type', '').lower() != 'record_keeper']
            
            if not all_entities:
                return {**results, 'message': 'No entities match criteria'}
            
            # OPTIMIZATION: Fetch chapters ONCE at the beginning
            chapters_cache = self.get_chapters(project_id, workspace_id)
            if not chapters_cache:
                return {**results, 'message': 'No chapters found'}
            
            results['total_entities'] = len(all_entities)
            logger.info(f"Property refresh: Processing {len(all_entities)} entities sequentially (chapters pre-fetched)")
            
            # Process entities ONE AT A TIME to avoid connection pool exhaustion
            for idx, entity in enumerate(all_entities):
                vertex_id = entity.get('vertex_id')
                entity_name = entity.get('name')
                results['entities_processed'] += 1
                
                logger.info(f"Property refresh {idx + 1}/{len(all_entities)}: Processing {entity_name}")
                
                try:
                    # Pass pre-fetched entity data and chapters to avoid DB calls
                    refresh_result = self.refresh_entity_properties(
                        project_id=project_id,
                        workspace_id=workspace_id,
                        vertex_id=str(vertex_id),
                        model=model,
                        provider=provider,
                        entity_data=entity,  # Pass entity data directly
                        chapters_cache=chapters_cache  # Pass cached chapters
                    )
                    
                    if refresh_result.get('success'):
                        if refresh_result.get('properties_changed'):
                            results['entities_updated'] += 1
                            results['changes_by_entity'][entity_name] = refresh_result.get('changes', [])
                            logger.info(f"  ✓ {entity_name}: Updated with {len(refresh_result.get('changes', []))} changes")
                        else:
                            results['entities_unchanged'] += 1
                            logger.debug(f"  - {entity_name}: No changes needed")
                    else:
                        error_msg = refresh_result.get('error', 'Unknown error')
                        results['errors'].append(f"{entity_name}: {error_msg}")
                        logger.warning(f"  ✗ {entity_name}: {error_msg}")
                        
                except Exception as e:
                    results['errors'].append(f"{entity_name}: {str(e)}")
                    logger.error(f"  ✗ {entity_name}: Exception - {str(e)}")
                
                # Delay between entities to let connections return to pool and respect API rate limits
                # LLM call takes ~2-3 seconds anyway, so 1s extra helps with rate limiting
                if idx < len(all_entities) - 1:
                    time.sleep(1.0)
            
            logger.info(f"Property refresh complete: {results['entities_updated']} updated, {results['entities_unchanged']} unchanged, {len(results['errors'])} errors")
            return results
            
        except Exception as e:
            logger.error(f"Error in refresh_all_entities_properties: {e}", exc_info=True)
            return {'error': str(e)}
    
    def apply_consistency_fix(
        self,
        project_id: str,
        workspace_id: str,
        entity_name: str,
        entity_type: Optional[str] = None,
        issue_type: Optional[str] = None,
        field: Optional[str] = None,
        suggestion: str = "",
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Apply a fix based on consistency check suggestions.
        
        Uses LLM to interpret the suggestion and generate appropriate property updates.
        
        Args:
            project_id: Project UUID
            workspace_id: Workspace UUID
            entity_name: Name of entity to fix
            entity_type: Type of entity (optional for lookup)
            issue_type: Type of consistency issue
            field: Specific field to update (optional)
            suggestion: The fix suggestion from consistency check
            model: AI model
            provider: AI provider
            
        Returns:
            Result of the fix operation
        """
        try:
            logger.info(f"Applying fix for {entity_name}, issue_type={issue_type}, field={field}")
            
            # Find the entity
            all_entities = self.records_manager.get_project_entities(project_id)
            entity = None
            for e in all_entities:
                if e.get('name', '').lower() == entity_name.lower():
                    if entity_type and e.get('type', '').lower() != entity_type.lower():
                        continue
                    entity = e
                    break
            
            if not entity:
                return {'error': f'Entity "{entity_name}" not found'}
            
            vertex_id = entity.get('vertex_id')
            current_props = entity.get('properties', {})
            
            # Get chapter content for context
            chapters = self.get_chapters(project_id, workspace_id)
            manuscript_preview = ""
            if chapters:
                for ch in chapters[:2]:  # First 2 chapters for context
                    content = ch.get('content', '')[:3000]
                    if content:
                        manuscript_preview += f"\n{content}"
            
            # Build prompt to interpret and apply the fix
            prompt = f"""You are updating a database record based on a consistency check suggestion.

ENTITY: {entity_name}
TYPE: {entity.get('type', 'unknown')}

CURRENT PROPERTIES:
{json.dumps({k: v for k, v in current_props.items() if not k.startswith('_')}, indent=2)}

ISSUE TYPE: {issue_type or 'general'}
FIELD TO UPDATE: {field or 'determine based on suggestion'}

SUGGESTION/FIX:
{suggestion}

STORY CONTEXT (for reference):
{manuscript_preview[:4000] if manuscript_preview else "No story content available"}

Based on the suggestion, determine what property value should be updated.

Respond with JSON:
{{
    "field": "the_field_to_update",
    "new_value": "the new value based on the suggestion",
    "explanation": "Brief explanation of the change"
}}

If the suggestion requires creating a new entity instead of updating, respond:
{{
    "action": "create_entity",
    "entity_name": "name of new entity",
    "entity_type": "type",
    "properties": {{}},
    "explanation": "Why this needs a new entity"
}}

OUTPUT (JSON only):"""

            # Get LLM response using GenerationEngine (same pattern as other methods)
            caller = self._create_caller(project_id, workspace_id)
            
            request = BaseGenerationRequest(
                model=model,
                provider=provider,
                prompt=prompt,
                system_instruction="Analyze the fix suggestion and return JSON with field and new_value.",
                generation_config=GenerationConfig(
                    temperature=0.3,
                    max_tokens=1000
                ),
                caller=caller
            )
            
            engine = GenerationEngine(request)
            response = engine.generate(skip_quota=True)
            
            if not response.success:
                return {'error': f'LLM request failed: {response.error_message}'}
            
            # Parse the response
            analysis, _ = JSONResponseParser.parse_response(
                response.text,
                expected_type="dict",
                fallback_value={}
            )
            
            if not analysis:
                return {'error': 'Failed to parse fix analysis'}
            
            # Check if it's a create action
            if analysis.get('action') == 'create_entity':
                # Create new entity with retry
                new_entity_name = analysis.get('entity_name')
                new_entity_type = analysis.get('entity_type', 'item')
                new_props = analysis.get('properties', {})

                create_result = self._create_entity_with_retry(
                    project_id=project_id,
                    name=new_entity_name,
                    entity_type=new_entity_type,
                    properties=new_props
                )

                if create_result.get('success'):
                    return {
                        'success': True,
                        'action': 'created',
                        'entity_name': new_entity_name,
                        'entity_type': new_entity_type,
                        'explanation': analysis.get('explanation', 'New entity created')
                    }
                else:
                    return {'error': create_result.get('error', 'Failed to create new entity')}
            
            # Update existing entity
            field_to_update = analysis.get('field', field)
            new_value = analysis.get('new_value')

            # Check for sentinel values indicating LLM determined no update needed
            invalid_sentinel_values = {'N/A', 'n/a', 'NA', 'na', 'None', 'none', 'null', ''}
            if field_to_update in invalid_sentinel_values or new_value in invalid_sentinel_values:
                return {
                    'success': True,
                    'action': 'skipped',
                    'entity_name': entity_name,
                    'message': 'No update needed - LLM determined the issue does not require a fix',
                    'explanation': analysis.get('explanation', 'No changes required'),
                    'skipped': True
                }

            if not field_to_update or new_value is None:
                return {'error': 'Could not determine field or value to update'}
            
            # Get current value
            old_value = current_props.get(field_to_update)
            
            # Check if value actually changed - convert both to strings for comparison
            old_str = json.dumps(old_value, sort_keys=True) if isinstance(old_value, (dict, list)) else str(old_value) if old_value is not None else ""
            new_str = json.dumps(new_value, sort_keys=True) if isinstance(new_value, (dict, list)) else str(new_value) if new_value is not None else ""
            
            if old_str == new_str:
                return {
                    'success': True,
                    'action': 'no_change',
                    'entity_name': entity_name,
                    'field': field_to_update,
                    'message': 'No change needed - value is already correct',
                    'explanation': analysis.get('explanation', 'Value already matches suggestion')
                }
            
            # Apply the update
            current_props[field_to_update] = new_value
            
            # Track the change (only if actually changed)
            # Handle _property_changes which might be stored as JSON string
            property_changes = current_props.get('_property_changes', [])
            if isinstance(property_changes, str):
                try:
                    property_changes = json.loads(property_changes)
                except (json.JSONDecodeError, TypeError):
                    property_changes = []
            if not isinstance(property_changes, list):
                property_changes = []
            
            property_changes.append({
                'field': field_to_update,
                'old_value': old_value,
                'new_value': new_value,
                'reason': f'Consistency fix: {issue_type}',
                'timestamp': datetime.utcnow().isoformat()
            })
            current_props['_property_changes'] = property_changes
            
            # Save the entity with retry
            vid = int(vertex_id) if isinstance(vertex_id, str) else vertex_id
            save_result = self._save_entity_properties_with_retry(
                project_id=project_id,
                vertex_id=vid,
                properties=current_props,
                operation_name="apply_consistency_fix"
            )

            if save_result.get('success'):
                return {
                    'success': True,
                    'action': 'updated',
                    'entity_name': entity_name,
                    'field': field_to_update,
                    'old_value': old_value,
                    'new_value': new_value,
                    'explanation': analysis.get('explanation', 'Property updated')
                }
            else:
                return {'error': save_result.get('error', 'Failed to save updated entity')}
                
        except Exception as e:
            logger.error(f"Error in apply_consistency_fix: {e}", exc_info=True)
            return {'error': str(e)}
    
    def fix_story_text(
        self,
        project_id: str,
        workspace_id: str = None,
        issue_type: str = None,
        title: str = None,
        description: str = "",
        evidence: str = "",
        location: str = "",
        suggestion: str = "",
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Generate a fix for story text (not entity properties).
        This identifies the problematic text segment and generates a revised version.
        
        Returns:
            {
                'old_text': 'The problematic text segment',
                'new_text': 'The revised text segment',
                'explanation': 'Why this change fixes the issue',
                'chapter_name': 'Chapter 1'
            }
        """
        try:
            # Parse chapter number from location (e.g., "Chapter 1" -> 0)
            chapter_order = 0
            chapter_name = location or "Chapter 1"
            if location:
                import re
                match = re.search(r'chapter\s*(\d+)', location.lower())
                if match:
                    chapter_order = int(match.group(1)) - 1  # Convert to 0-indexed
            
            # Get chapter content (uses database fallback if Laravel endpoint fails)
            chapters = self.get_chapters(project_id, workspace_id)
            if not chapters:
                return {'error': 'No chapters found for this project'}
            
            # Find the relevant chapter
            chapter = None
            for ch in chapters:
                if ch.get('chapter_order', ch.get('order', 0)) == chapter_order:
                    chapter = ch
                    chapter_name = ch.get('chapter_name', ch.get('name', chapter_name))
                    break
            
            if not chapter:
                # Use first chapter if specific one not found
                chapter = chapters[0]
                chapter_name = chapter.get('chapter_name', chapter.get('name', 'Chapter 1'))
            
            content = chapter.get('content', '')
            if not content:
                return {'error': f'No content found in {chapter_name}'}
            
            # Build prompt to find and fix the problematic text
            prompt = f"""You are a professional story editor. A consistency issue has been identified in the following manuscript chapter.

ISSUE TYPE: {issue_type}
ISSUE TITLE: {title}
DESCRIPTION: {description}
EVIDENCE FROM TEXT: {evidence}
SUGGESTED FIX: {suggestion}

CHAPTER CONTENT:
{content[:15000]}

TASK:
1. Locate the problematic text segment that causes this consistency issue
2. Generate a revised version that fixes the issue while maintaining the story's style and flow
3. The fix should be minimal - change only what's necessary to resolve the inconsistency

OUTPUT FORMAT (JSON):
{{
    "old_text": "The exact text segment that contains the problem (copy VERBATIM from the chapter)",
    "new_text": "The revised text segment that fixes the issue",
    "explanation": "Brief explanation of what was changed and why"
}}

CRITICAL JSON FORMATTING RULES:
- ALL quotes inside string values MUST be escaped with backslash: use \\" not "
- Example: "old_text": "He said \\"Hello\\" to her"
- Newlines in text should be: \\n
- This is REQUIRED for valid JSON

CRITICAL VERBATIM REQUIREMENT:
- You MUST copy the old_text EXACTLY character-by-character from the chapter content above
- Do NOT paraphrase, summarize, or rephrase any part of old_text
- The old_text must match byte-for-byte with the original chapter text
- Include all punctuation, quotes, spaces, and whitespace EXACTLY as they appear
- Before responding, verify your old_text exists in the chapter by searching for it

IMPORTANT:
- Keep the same writing style and voice in new_text
- Make the minimum necessary changes
- Preserve paragraph breaks and formatting
"""
            
            # Use LLM to analyze and generate fix
            from services.generation_engine import GenerationEngine
            from models.request import BaseGenerationRequest, GenerationConfig
            
            # Create caller first
            caller = self._create_caller(project_id, workspace_id)
            
            # Build request with all needed fields
            request = BaseGenerationRequest(
                usecase="novel_pipeline",
                provider=provider,
                model=model,
                prompt=prompt,
                generation_config=GenerationConfig(
                    max_output_tokens=4000,
                    temperature=0.3
                ),
                caller=caller
            )
            
            engine = GenerationEngine(request)
            response = engine.generate(skip_quota=True)
            
            if not response or not response.text:
                return {'error': 'Failed to generate story fix'}
            
            # Parse response
            from utils.json_response_parser import JSONResponseParser
            analysis, _ = JSONResponseParser.parse_response(response.text, expected_type="dict", fallback_value={})
            
            if not analysis:
                return {'error': 'Failed to parse LLM response'}
            
            old_text = analysis.get('old_text', '')
            new_text = analysis.get('new_text', '')
            explanation = analysis.get('explanation', '')
            
            if not old_text or not new_text:
                return {'error': 'Could not identify text to fix'}
            
            # Verify old_text exists in chapter
            if old_text not in content:
                # Log warning - frontend will use fuzzy matching
                logger.warning(f"LLM returned old_text not found verbatim in chapter. Frontend will use fuzzy matching. old_text preview: {old_text[:100]}...")

            # Generate content hash for change detection
            import hashlib
            content_hash = hashlib.md5(content.encode()).hexdigest()[:8]

            return {
                'old_text': old_text,
                'new_text': new_text,
                'explanation': explanation,
                'chapter_name': chapter_name,
                'chapter_order': chapter_order,
                'content_hash': content_hash  # For detecting if chapter changed since fix was generated
            }
            
        except Exception as e:
            logger.error(f"Error in fix_story_text: {e}", exc_info=True)
            return {'error': str(e)}

    def batch_fix_story_text(
        self,
        project_id: str,
        workspace_id: str = None,
        issues: List[Dict] = None,
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Generate fixes for multiple story issues against the same content snapshot.
        This ensures all fixes are compatible and can be applied together without conflicts.

        Args:
            project_id: The project ID
            workspace_id: The workspace ID
            issues: List of issue objects with issue_type, title, description, evidence, location, suggestion
            model: LLM model to use
            provider: LLM provider

        Returns:
            {
                'fixes': [
                    {
                        'issue_index': 0,
                        'old_text': '...',
                        'new_text': '...',
                        'explanation': '...',
                        'chapter_order': 1,
                        'chapter_name': 'Chapter 1',
                        'position': 234,  # Character offset for ordering
                    },
                    ...
                ],
                'content_hash': 'abc123',
                'errors': []  # Any issues that couldn't be fixed
            }
        """
        import re

        if not issues:
            return {'fixes': [], 'content_hash': '', 'errors': ['No issues provided']}

        try:
            # Get all chapters once
            chapters = self.get_chapters(project_id, workspace_id)
            if not chapters:
                return {'fixes': [], 'content_hash': '', 'errors': ['No chapters found for this project']}

            # Create chapter lookup by order
            chapter_lookup = {}
            for ch in chapters:
                order = ch.get('chapter_order', ch.get('order', 0))
                chapter_lookup[order] = ch

            # Group issues by chapter
            issues_by_chapter: Dict[int, List[Tuple[int, Dict]]] = {}
            for idx, issue in enumerate(issues):
                location = issue.get('location', '')
                chapter_order = 0

                if location:
                    match = re.search(r'chapter\s*(\d+)', location.lower())
                    if match:
                        chapter_order = int(match.group(1)) - 1  # Convert to 0-indexed

                if chapter_order not in issues_by_chapter:
                    issues_by_chapter[chapter_order] = []
                issues_by_chapter[chapter_order].append((idx, issue))

            all_fixes = []
            all_errors = []
            content_hashes = {}

            # Process each chapter's issues together
            for chapter_order, chapter_issues in issues_by_chapter.items():
                chapter = chapter_lookup.get(chapter_order)
                if not chapter:
                    # Use first chapter if specific one not found
                    chapter = chapters[0]
                    chapter_order = chapter.get('chapter_order', chapter.get('order', 0))

                chapter_name = chapter.get('chapter_name', chapter.get('name', f'Chapter {chapter_order + 1}'))
                content = chapter.get('content', '')

                if not content:
                    for idx, issue in chapter_issues:
                        all_errors.append(f"Issue {idx}: No content in {chapter_name}")
                    continue

                # Store content hash for this chapter
                content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
                content_hashes[chapter_order] = content_hash

                # Build prompt for ALL issues in this chapter
                issues_text = ""
                for i, (idx, issue) in enumerate(chapter_issues, 1):
                    issues_text += f"""
ISSUE {i} (original_index: {idx}):
- Type: {issue.get('issue_type', 'unknown')}
- Title: {issue.get('title', 'Unknown issue')}
- Description: {issue.get('description', '')}
- Evidence: {issue.get('evidence', '')}
- Suggestion: {issue.get('suggestion', '')}
"""

                prompt = f"""You are a professional story editor. Multiple consistency issues have been identified in the following manuscript chapter.
Fix ALL issues while maintaining grammatical flow and the author's writing style.

CHAPTER: {chapter_name}
CHAPTER CONTENT:
{content[:15000]}

ISSUES TO FIX:
{issues_text}

TASK:
For EACH issue listed above:
1. Locate the EXACT problematic text segment in the chapter
2. Generate a minimal revision that fixes the issue
3. Ensure the fix reads naturally within the surrounding paragraph
4. Maintain the author's style, tone, and narrative voice

OUTPUT FORMAT (JSON array):
[
    {{
        "original_index": <the original_index from the issue>,
        "old_text": "EXACT text segment from chapter (copy VERBATIM)",
        "new_text": "The revised text that fixes the issue",
        "explanation": "Brief explanation of what was changed"
    }},
    ...
]

CRITICAL JSON FORMATTING RULES:
- ALL quotes inside string values MUST be escaped with backslash: use \\" not "
- Example: "old_text": "He said \\"Hello\\" to her"
- Newlines in text should be: \\n
- Return a valid JSON array with one object per issue

CRITICAL VERBATIM REQUIREMENT:
- old_text MUST be copied EXACTLY character-by-character from the chapter
- Do NOT paraphrase or rephrase - the frontend needs exact matches
- Include all punctuation, quotes, and whitespace exactly as they appear

CRITICAL GRAMMATICAL FLOW:
- new_text must read naturally within its paragraph
- Transitions to/from adjacent sentences must be smooth
- Preserve the narrative voice (first/third person, past/present tense)
- Make MINIMAL changes - only fix the specific issue

Return fixes for ALL {len(chapter_issues)} issues.
"""

                # Use LLM to generate all fixes for this chapter
                caller = self._create_caller(project_id, workspace_id)

                request = BaseGenerationRequest(
                    usecase="novel_pipeline",
                    provider=provider,
                    model=model,
                    prompt=prompt,
                    generation_config=GenerationConfig(
                        max_output_tokens=8000,  # More tokens for multiple fixes
                        temperature=0.3
                    ),
                    caller=caller
                )

                engine = GenerationEngine(request)
                response = engine.generate(skip_quota=True)

                if not response or not response.text:
                    for idx, issue in chapter_issues:
                        all_errors.append(f"Issue {idx}: Failed to generate fix")
                    continue

                # Parse response - expecting JSON array
                fixes_data, _ = JSONResponseParser.parse_response(response.text, expected_type="list", fallback_value=[])

                if not fixes_data:
                    # Try parsing as dict with fixes key
                    dict_data, _ = JSONResponseParser.parse_response(response.text, expected_type="dict", fallback_value={})
                    fixes_data = dict_data.get('fixes', [])

                if not fixes_data:
                    for idx, issue in chapter_issues:
                        all_errors.append(f"Issue {idx}: Failed to parse LLM response")
                    continue

                # Process each fix
                for fix_data in fixes_data:
                    original_index = fix_data.get('original_index', fix_data.get('issue_index', -1))
                    old_text = fix_data.get('old_text', '')
                    new_text = fix_data.get('new_text', '')
                    explanation = fix_data.get('explanation', '')

                    if not old_text or not new_text:
                        all_errors.append(f"Issue {original_index}: Empty old_text or new_text")
                        continue

                    # Find position in content for ordering
                    position = content.find(old_text)
                    if position == -1:
                        # Try case-insensitive search
                        position = content.lower().find(old_text.lower())
                        if position == -1:
                            # Log warning - frontend will use fuzzy matching
                            logger.warning(f"Batch fix: old_text not found verbatim for issue {original_index}")
                            position = 0  # Default to start if not found

                    all_fixes.append({
                        'issue_index': original_index,
                        'old_text': old_text,
                        'new_text': new_text,
                        'explanation': explanation,
                        'chapter_order': chapter_order,
                        'chapter_name': chapter_name,
                        'position': position,
                        'content_hash': content_hash
                    })

            # Sort fixes by chapter then by position (descending - for bottom-to-top application)
            all_fixes.sort(key=lambda f: (f['chapter_order'], -f['position']))

            # Combine content hashes
            combined_hash = hashlib.md5(
                '|'.join(f"{k}:{v}" for k, v in sorted(content_hashes.items())).encode()
            ).hexdigest()[:8]

            return {
                'fixes': all_fixes,
                'content_hash': combined_hash,
                'errors': all_errors
            }

        except Exception as e:
            logger.error(f"Error in batch_fix_story_text: {e}", exc_info=True)
            return {'fixes': [], 'content_hash': '', 'errors': [str(e)]}

    # =========================================================================
    # RECORD OPTIMIZATION
    # =========================================================================

    def find_duplicate_entities(
        self,
        project_id: str,
        workspace_id: str = None,
        scope: str = "all",
        categories: Optional[List[str]] = None,
        entity_ids: Optional[List[str]] = None,
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Find potential duplicate entities that could be merged.
        
        Args:
            scope: "all" | "category" | "entity"
            categories: List of category types to filter by (when scope is "category")
            entity_ids: List of specific entity vertex_ids (when scope is "entity")
        
        Detects:
        - Same entity with different names ("John" and "John Doe")
        - Aliases and nicknames
        - Redundant entries
        
        Returns:
            {
                'potential_duplicates': [
                    {
                        'entities': [
                            {'vertex_id': '123', 'name': 'John', 'type': 'character'},
                            {'vertex_id': '456', 'name': 'John Doe', 'type': 'character'}
                        ],
                        'confidence': 0.9,
                        'reason': 'Same character with full name vs nickname',
                        'suggested_canonical': 'John Doe',
                        'merge_suggestion': {...}
                    }
                ],
                'entities_analyzed': 20,
                'duplicate_groups_found': 3
            }
        """
        try:
            results = {
                'potential_duplicates': [],
                'entities_analyzed': 0,
                'duplicate_groups_found': 0,
                'errors': [],  # Track API failures
                'categories_processed': []
            }
            
            # Get all entities
            all_entities = self.records_manager.get_project_entities(project_id)
            if not all_entities:
                return {**results, 'message': 'No entities found'}
            
            # Apply scope filtering
            if scope == 'category' and categories:
                # Filter by categories
                all_entities = [e for e in all_entities 
                              if e.get('type', '').lower() in [c.lower() for c in categories]]
            elif scope == 'entity' and entity_ids:
                # Filter by specific entity IDs
                all_entities = [e for e in all_entities 
                              if str(e.get('vertex_id', '')) in entity_ids]
            elif categories:
                # Legacy support: filter by categories if provided even without explicit scope
                all_entities = [e for e in all_entities 
                              if e.get('type', '').lower() in [c.lower() for c in categories]]
            
            # Exclude metadata entities
            all_entities = [e for e in all_entities 
                          if not e.get('type', '').startswith('_')
                          and e.get('type', '').lower() != 'record_keeper']
            
            if len(all_entities) < 2:
                return {**results, 'message': 'Not enough entities to check for duplicates'}
            
            results['entities_analyzed'] = len(all_entities)
            
            # Group by type for more accurate comparison
            entities_by_type = {}
            for entity in all_entities:
                entity_type = entity.get('type', 'unknown')
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                entities_by_type[entity_type].append({
                    'vertex_id': str(entity.get('vertex_id')),
                    'name': entity.get('name'),
                    'type': entity_type,
                    'properties': {k: v for k, v in entity.get('properties', {}).items() 
                                  if not k.startswith('_')}
                })
            
            # Get chapter content for context
            chapters = self.get_chapters(project_id, workspace_id) if workspace_id else []
            story_context = ""
            if chapters:
                story_context = "\n".join([
                    f"Chapter {ch.get('order', 0)+1}: {ch.get('content', '')[:2000]}"
                    for ch in chapters[:3]  # First 3 chapters for context
                ])
            
            # Create caller
            caller = self._create_caller(project_id, workspace_id)
            
            # Check each type group for duplicates
            for entity_type, entities in entities_by_type.items():
                if len(entities) < 2:
                    continue
                
                prompt = f"""You are analyzing a database of {entity_type} entities to find potential duplicates.

ENTITIES OF TYPE "{entity_type.upper()}":
{json.dumps(entities, indent=2)}

STORY CONTEXT (for reference):
{story_context[:5000] if story_context else "No story context available"}

TASK: Identify entities that might be duplicates or refer to the same thing.

Look for:
1. Same entity with different name variations (e.g., "John" and "John Smith", "NYC" and "New York City")
2. Nicknames or titles (e.g., "The King" and "King Edward")
3. Aliases (e.g., "The Dark Knight" and "Batman")
4. Typos or slight variations
5. Redundant entries that describe the same thing

OUTPUT FORMAT (JSON array of duplicate groups):
[
  {{
    "entities": [
      {{"vertex_id": "id1", "name": "name1"}},
      {{"vertex_id": "id2", "name": "name2"}}
    ],
    "confidence": 0.9,
    "reason": "Why these are likely duplicates",
    "suggested_canonical": "The preferred name to keep",
    "merge_properties": {{
      "keep_from_first": ["property1"],
      "keep_from_second": ["property2"],
      "merge": ["property3"]
    }}
  }}
]

If no duplicates found, return an empty array: []

IMPORTANT: Only report likely duplicates, not entities that merely share some characteristics.

ANALYSIS:"""

                request = BaseGenerationRequest(
                    prompt=prompt,
                    provider=provider,
                    model=model,
                    instruction="Find duplicate entities and return JSON array.",
                    generation_config=GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=2000,
                    ),
                    caller=caller
                )
                
                engine = GenerationEngine(request)
                response = engine.generate(skip_quota=True)
                
                if response.success:
                    results['categories_processed'].append(entity_type)
                    try:
                        duplicates, _ = JSONResponseParser.parse_response(
                            response.text,
                            expected_type="list",
                            fallback_value=[]
                        )
                        
                        if duplicates:
                            for dup in duplicates:
                                dup['entity_type'] = entity_type
                            results['potential_duplicates'].extend(duplicates)
                            results['duplicate_groups_found'] += len(duplicates)
                    except Exception as e:
                        logger.warning(f"Error parsing duplicate check response: {e}")
                        results['errors'].append(f"{entity_type}: Failed to parse response")
                else:
                    # API call failed - track the error
                    error_msg = response.error_message or "Unknown error"
                    logger.warning(f"Duplicate check failed for {entity_type}: {error_msg}")
                    results['errors'].append(f"{entity_type}: {error_msg}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in find_duplicate_entities: {e}", exc_info=True)
            return {'error': str(e)}
    
    def merge_entities(
        self,
        project_id: str,
        source_vertex_id: str,
        target_vertex_id: str,
        merge_strategy: str = "combine"  # "combine", "prefer_source", "prefer_target"
    ) -> Dict[str, Any]:
        """
        Merge two entities into one atomically.

        Both the property update and source deletion happen in a single transaction.
        If either fails, the entire operation is rolled back.

        Args:
            project_id: Project UUID
            source_vertex_id: Entity to merge FROM (will be deleted)
            target_vertex_id: Entity to merge INTO (will be kept)
            merge_strategy: How to handle conflicting properties

        Returns:
            {
                'success': True,
                'merged_entity': {...},
                'deleted_entity_id': '...'
            }
        """
        from utils.database_utils import TransientDatabaseError, PermanentDatabaseError

        try:
            # Get both entities (read-only)
            all_entities = self.records_manager.get_project_entities(project_id)

            source_entity = None
            target_entity = None

            for entity in all_entities:
                vid = str(entity.get('vertex_id'))
                if vid == str(source_vertex_id):
                    source_entity = entity
                elif vid == str(target_vertex_id):
                    target_entity = entity

            if not source_entity:
                return {'error': f'Source entity {source_vertex_id} not found'}
            if not target_entity:
                return {'error': f'Target entity {target_vertex_id} not found'}

            # Merge properties based on strategy (pure computation)
            source_props = source_entity.get('properties', {})
            target_props = target_entity.get('properties', {})

            merged_props = {}

            if merge_strategy == "prefer_target":
                merged_props = {**source_props, **target_props}
            elif merge_strategy == "prefer_source":
                merged_props = {**target_props, **source_props}
            else:  # combine
                # Smart merge: combine arrays, use longer strings, keep newer dates
                all_keys = set(source_props.keys()) | set(target_props.keys())
                for key in all_keys:
                    source_val = source_props.get(key)
                    target_val = target_props.get(key)

                    if source_val is None:
                        merged_props[key] = target_val
                    elif target_val is None:
                        merged_props[key] = source_val
                    elif isinstance(source_val, list) and isinstance(target_val, list):
                        # Combine arrays, remove duplicates
                        combined = list(target_val)
                        for item in source_val:
                            if item not in combined:
                                combined.append(item)
                        merged_props[key] = combined
                    elif isinstance(source_val, str) and isinstance(target_val, str):
                        # Keep longer string (usually more detailed)
                        merged_props[key] = source_val if len(source_val) > len(target_val) else target_val
                    else:
                        # Default to target
                        merged_props[key] = target_val

            # Merge _summaries specially
            source_summaries = source_props.get('_summaries', [])
            target_summaries = target_props.get('_summaries', [])
            if source_summaries or target_summaries:
                # Combine and dedupe by chapter_number
                all_summaries = {}
                for s in target_summaries:
                    if s and s.get('chapter_number'):
                        all_summaries[s['chapter_number']] = s
                for s in source_summaries:
                    if s and s.get('chapter_number') and s['chapter_number'] not in all_summaries:
                        all_summaries[s['chapter_number']] = s
                merged_props['_summaries'] = list(all_summaries.values())

            # Execute atomic merge with retry
            return self._merge_entities_atomic(
                project_id=project_id,
                source_vertex_id=source_vertex_id,
                target_vertex_id=target_vertex_id,
                merged_props=merged_props
            )

        except TransientDatabaseError as e:
            logger.error(f"Merge failed after retries (transient): {e}")
            return {'error': f'Database temporarily unavailable: {e}', 'retry_possible': True}
        except PermanentDatabaseError as e:
            logger.error(f"Merge failed permanently: {e}")
            return {'error': str(e), 'retry_possible': False}
        except Exception as e:
            logger.error(f"Error merging entities: {e}", exc_info=True)
            return {'error': str(e)}

    def _merge_entities_atomic(
        self,
        project_id: str,
        source_vertex_id: str,
        target_vertex_id: str,
        merged_props: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Atomic merge operation - update target and delete source in single transaction.

        Includes retry with exponential backoff for transient failures.
        If any operation fails, entire transaction is rolled back.

        Args:
            project_id: Project UUID
            source_vertex_id: Entity to merge FROM (will be deleted)
            target_vertex_id: Entity to merge INTO (will be kept)
            merged_props: Pre-computed merged properties

        Returns:
            Success dict or raises exception
        """
        import time
        from utils.database_utils import classify_db_error, TransientDatabaseError, PermanentDatabaseError

        max_retries = 3
        initial_delay = 0.5
        delay = initial_delay

        source_vid = int(source_vertex_id) if isinstance(source_vertex_id, str) else source_vertex_id
        target_vid = int(target_vertex_id) if isinstance(target_vertex_id, str) else target_vertex_id

        graph_draft_id = self.records_manager._project_id_to_draft_id(project_id)
        graph_name = self.records_manager.graph_service.graph_name
        graph_service = self.records_manager.graph_service

        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                # Single connection for both operations (atomic transaction)
                with graph_service.get_age_connection() as conn:
                    with conn.cursor() as cursor:
                        # Idempotency check: Is source already deleted?
                        cursor.execute("""
                            SELECT vertex_id FROM novel_graph_vertices
                            WHERE project_id = %s AND vertex_id = %s
                        """, (project_id, source_vid))

                        if cursor.fetchone() is None:
                            # Source already deleted - merge was already done
                            logger.info(f"Merge already completed (idempotent): {source_vid} -> {target_vid}")
                            return {
                                'success': True,
                                'merged_into': str(target_vertex_id),
                                'deleted': str(source_vertex_id),
                                'already_merged': True
                            }

                        safe_draft_id = graph_service._escape_cypher_string(graph_draft_id)
                        safe_props = graph_service._prepare_agtype_properties(merged_props)

                        # 1. Update target entity in graph
                        update_query = f"""
                            SELECT result FROM ag_catalog.cypher('{graph_name}', $$
                            MATCH (n {{draft_id: '{safe_draft_id}'}})
                            WHERE id(n) = {target_vid}
                            SET n.properties = {safe_props}
                            RETURN n
                            $$) AS (result agtype)
                        """
                        cursor.execute(update_query)

                        # 2. Update target entity in metadata
                        cursor.execute("""
                            UPDATE novel_graph_vertices
                            SET properties = %s, updated_at = NOW()
                            WHERE project_id = %s AND vertex_id = %s
                        """, (json.dumps(merged_props), project_id, target_vid))

                        if cursor.rowcount == 0:
                            raise PermanentDatabaseError(f"Target entity {target_vid} not found in metadata")

                        # 3. Delete source entity from graph
                        delete_query = f"""
                            SELECT result FROM ag_catalog.cypher('{graph_name}', $$
                            MATCH (n)
                            WHERE id(n) = {source_vid}
                            DETACH DELETE n
                            RETURN count(n) AS deleted_count
                            $$) AS (result agtype)
                        """
                        cursor.execute(delete_query)

                        # 4. Delete source entity from metadata
                        cursor.execute("""
                            DELETE FROM novel_graph_vertices
                            WHERE project_id = %s AND vertex_id = %s
                        """, (project_id, source_vid))

                    # All operations succeeded - commit
                    conn.commit()

                logger.info(f"Atomic merge completed: {source_vid} -> {target_vid}")

                return {
                    'success': True,
                    'merged_into': str(target_vertex_id),
                    'deleted': str(source_vertex_id),
                    'merged_properties': merged_props
                }

            except (TransientDatabaseError, PermanentDatabaseError):
                raise  # Re-raise our custom errors

            except Exception as e:
                last_error = e
                error_type = classify_db_error(e)

                if error_type == 'permanent':
                    logger.error(f"[merge_entities_atomic] Permanent error: {e}")
                    raise PermanentDatabaseError(f"Merge failed: {e}") from e

                # Transient error - maybe retry
                if attempt < max_retries:
                    logger.warning(
                        f"[merge_entities_atomic] Transient error (attempt {attempt}/{max_retries}): "
                        f"{e}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 4.0)
                else:
                    logger.error(f"[merge_entities_atomic] All {max_retries} attempts exhausted: {e}")
                    raise TransientDatabaseError(
                        f"Merge failed after {max_retries} attempts: {e}"
                    ) from e

        # Should not reach here
        if last_error:
            raise TransientDatabaseError(f"Merge failed: {last_error}") from last_error
    
    def get_chapters(self, project_id: str, workspace_id: str = None) -> List[Dict[str, Any]]:
        """
        Fetch all chapters for a project with current content from version control.

        Uses direct database access to query project_content and version control tables.

        Args:
            project_id: Project UUID
            workspace_id: Optional workspace ID (kept for API compatibility, not used)

        Returns:
            List of chapter dictionaries with order, chapter_name, content
        """
        from utils.database_utils import utf8_database_connection

        # Direct database query - fetches chapters with version control content
        try:
            with utf8_database_connection(self.db_pool, operation_name="get_chapters") as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT content FROM project_content 
                        WHERE project_id = %s
                    """, (project_id,))
                    
                    result = cursor.fetchone()
                    if not result or not result[0]:
                        logger.warning(f"No project_content found for project {project_id}")
                        return []
                    
                    chapters = result[0]
                    if isinstance(chapters, str):
                        chapters = json.loads(chapters)
                    
                    if not isinstance(chapters, list):
                        logger.warning(f"Invalid chapters format for project {project_id}")
                        return []
                    
                    # Get current content from version control for each chapter
                    enriched_chapters = []
                    chapters_without_content = 0
                    for chapter in chapters:
                        chapter_order = chapter.get('order')
                        chapter_name = chapter.get('chapter_name', f"Chapter {chapter_order}")
                        chapter_content = chapter.get('content', '')
                        
                        if chapter_order is not None:
                            # Try multiple methods to get content
                            current_content = None
                            
                            # Method 1: Try version control (chapter_states -> content_versions)
                            current_content = self._get_current_chapter_content(
                                conn, project_id, chapter_order
                            )
                            
                            # Method 2: Try content_nodes table directly (if version control fails)
                            if not current_content or len(current_content.strip()) == 0:
                                current_content = self._get_content_from_nodes(conn, project_id, chapter_order)
                            
                            # Method 3: Fallback to project_content.content field
                            if not current_content or len(current_content.strip()) == 0:
                                if chapter_content and len(chapter_content.strip()) > 0:
                                    current_content = chapter_content
                            
                            if current_content and len(current_content.strip()) > 0:
                                chapter['content'] = current_content
                                logger.info(f"Chapter {chapter_order} ({chapter_name}): Found content ({len(current_content)} chars)")
                            else:
                                logger.warning(f"Chapter {chapter_order} ({chapter_name}): No content available from any source")
                                chapters_without_content += 1
                        
                        enriched_chapters.append(chapter)
                    
                    # Log summary
                    chapters_with_content = sum(1 for ch in enriched_chapters if ch.get('content') and len(ch.get('content', '').strip()) > 0)
                    logger.info(f"Fetched {len(enriched_chapters)} chapters from database for project {project_id}, {chapters_with_content} have content, {chapters_without_content} missing content")
                    
                    return enriched_chapters
                    
        except Exception as e:
            logger.error(f"Failed to fetch chapters from database for project {project_id}: {e}", exc_info=True)
            return []

    def _get_current_chapter_content(self, conn, project_id: str, chapter_order: int) -> Optional[str]:
        """
        Get current chapter content from version control.
        
        Args:
            conn: Database connection
            project_id: Project UUID (ULID string)
            chapter_order: Chapter order number
            
        Returns:
            Current chapter content, or None if not found
        """
        try:
            with conn.cursor() as cursor:
                # First, check if chapter_states table exists and has any entries for this project
                try:
                    cursor.execute("""
                        SELECT COUNT(*) FROM chapter_states 
                        WHERE project_id = %s
                    """, (project_id,))
                    total_states = cursor.fetchone()[0]
                    logger.debug(f"Found {total_states} chapter_states entries for project {project_id}")
                except Exception as e:
                    logger.warning(f"Error checking chapter_states table: {e}")
                    return None
                
                # Get current version from chapter_states
                # Note: project_id and current_node_id are ULIDs stored as strings
                cursor.execute("""
                    SELECT cs.current_version_index, cs.current_node_id
                    FROM chapter_states cs
                    WHERE cs.project_id = %s AND cs.chapter_order = %s
                """, (project_id, chapter_order))
                
                state = cursor.fetchone()
                if not state:
                    logger.info(f"No chapter_states entry for chapter {chapter_order} (project_id: {project_id}) - version control may not be initialized for this chapter")
                    return None
                
                current_version_index, current_node_id = state
                
                if not current_node_id:
                    logger.warning(f"Chapter {chapter_order} has NULL current_node_id in chapter_states")
                    return None
                
                logger.info(f"Found chapter_states for chapter {chapter_order}: node_id={current_node_id}, version_index={current_version_index}")
                
                # Get content from content_versions
                cursor.execute("""
                    SELECT cv.content
                    FROM content_versions cv
                    WHERE cv.node_id = %s AND cv.version_index = %s
                """, (current_node_id, current_version_index))
                
                version = cursor.fetchone()
                if version and version[0]:
                    content = version[0]
                    content_length = len(content) if content else 0
                    logger.info(f"Retrieved {content_length} chars from version control for chapter {chapter_order}")
                    return content
                else:
                    logger.warning(f"No content_versions entry for chapter {chapter_order} (node_id: {current_node_id}, version_index: {current_version_index})")
                    # Try to see if any versions exist for this node
                    cursor.execute("""
                        SELECT COUNT(*) FROM content_versions 
                        WHERE node_id = %s
                    """, (current_node_id,))
                    count = cursor.fetchone()[0]
                    logger.debug(f"Found {count} total versions for node_id {current_node_id}")
                    if count > 0:
                        # Try to get the latest version
                        cursor.execute("""
                            SELECT cv.content, cv.version_index
                            FROM content_versions cv
                            WHERE cv.node_id = %s
                            ORDER BY cv.version_index DESC
                            LIMIT 1
                        """, (current_node_id,))
                        latest = cursor.fetchone()
                        if latest:
                            logger.info(f"Using latest version {latest[1]} instead of {current_version_index} for chapter {chapter_order}")
                            return latest[0]
                    return None
                
        except Exception as e:
            logger.error(f"Failed to get version control content for chapter {chapter_order}: {e}", exc_info=True)
            return None
    
    def _get_content_from_nodes(self, conn, project_id: str, chapter_order: int) -> Optional[str]:
        """
        Alternative method: Get content directly from content_nodes table.
        
        Args:
            conn: Database connection
            project_id: Project UUID
            chapter_order: Chapter order number
            
        Returns:
            Chapter content, or None if not found
        """
        try:
            with conn.cursor() as cursor:
                # Get the current node from chapter_states, then get content from content_nodes
                cursor.execute("""
                    SELECT cn.content
                    FROM chapter_states cs
                    JOIN content_nodes cn ON cs.current_node_id = cn.id
                    WHERE cs.project_id = %s AND cs.chapter_order = %s
                """, (project_id, chapter_order))
                
                result = cursor.fetchone()
                if result and result[0]:
                    content = result[0]
                    logger.info(f"Retrieved {len(content)} chars from content_nodes for chapter {chapter_order}")
                    return content
                
                return None
                
        except Exception as e:
            logger.debug(f"Failed to get content from content_nodes for chapter {chapter_order}: {e}")
            return None
    
    def summarize_chapter_for_record_keeper(
        self,
        project_id: str,
        chapter: Dict[str, Any],
        model: str = "gemini-2.5-flash",
        provider: str = "gemini",
        workspace_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a chapter and create Record Keeper summary.
        
        Args:
            project_id: Project UUID
            chapter: Chapter dict with order, chapter_name, content
            model: AI model to use
            provider: AI provider (gemini)
            
        Returns:
            Dictionary with Record Keeper fields:
            - chapter_number
            - chapter_title
            - summary
            - character_activity
            - key_events
            - themes_mentioned
            - locations_mentioned
        """
        try:
            chapter_content = chapter.get('content', '')
            chapter_name = chapter.get('chapter_name', f"Chapter {chapter.get('order', 0) + 1}")
            chapter_number = chapter.get('order', 0) + 1
            
            if not chapter_content:
                logger.warning(f"Chapter {chapter_number} ({chapter_name}) has NO content (None or empty)")
                return None
            
            content_length = len(chapter_content.strip())
            if content_length < 100:
                logger.warning(f"Chapter {chapter_number} ({chapter_name}) has insufficient content: {content_length} chars (minimum 100 required)")
                return None
            
            logger.info(f"Chapter {chapter_number} ({chapter_name}) has {content_length} chars - proceeding with analysis")
            
            logger.info(f"Analyzing chapter {chapter_number} ({chapter_name}) with {len(chapter_content)} chars")
            
            # Create prompt for chapter analysis
            # This prompt is flexible - it extracts standard Record Keeper fields
            # Custom categories/fields are handled by the LLM's ability to extract any relevant information
            prompt = f"""You are a literary analysis expert. Analyze the following chapter and extract comprehensive information for record keeping.

CHAPTER: {chapter_name}
CHAPTER NUMBER: {chapter_number}

CHAPTER CONTENT:
{chapter_content}

ANALYSIS REQUIREMENTS:
1. Create a detailed summary of what happened in this chapter
2. Identify all characters who appear and what they did
3. List all key events and plot developments
4. Identify themes mentioned or developed
5. List all locations mentioned
6. Extract any other significant entities (factions, organizations, concepts, etc.) that appear

OUTPUT FORMAT (JSON):
{{
  "summary": "Comprehensive summary of the chapter's events, plot developments, and significance. Should be detailed and capture all important moments.",
  "character_activity": [
    {{
      "name": "Character Name",
      "actions": "What this character did, said, or experienced in this chapter"
    }}
  ],
  "key_events": [
    "Event 1 description",
    "Event 2 description"
  ],
  "themes_mentioned": [
    "Theme 1",
    "Theme 2"
  ],
  "locations_mentioned": [
    "Location 1",
    "Location 2"
  ],
  "other_entities": [
    {{
      "name": "Entity Name",
      "type": "Faction/Organization/Concept/etc.",
      "description": "What this entity is and its role in this chapter"
    }}
  ]
}}

IMPORTANT: Extract ALL relevant information. If you encounter custom entity types (like Factions, Organizations, etc.), 
include them in the "other_entities" array. The system will handle custom fields and categories dynamically.

ANALYSIS:"""
            
            # Create caller for generation request
            caller = self._create_caller(project_id, workspace_id)
            
            # Create generation request
            request = BaseGenerationRequest(
                prompt=prompt,
                provider=provider,
                model=model,
                instruction="Extract chapter analysis data in JSON format.",
                generation_config=GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2000,
                ),
                caller=caller
            )
            
            # Generate analysis
            engine = GenerationEngine(request)
            response = engine.generate(skip_quota=True)
            
            if not response.success:
                logger.error(f"Failed to analyze chapter {chapter_number}: {response.error_message}")
                return None
            
            # Parse JSON response
            try:
                # response.text is the generated text from the LLM
                analysis_data, _ = JSONResponseParser.parse_response(
                    response.text,
                    expected_type="dict",
                    fallback_value={}
                )
                
                # Build Record Keeper entry
                record_keeper_entry = {
                    "chapter_number": str(chapter_number),
                    "chapter_title": chapter_name,
                    "summary": analysis_data.get("summary", ""),
                    "character_activity": analysis_data.get("character_activity", []),
                    "key_events": analysis_data.get("key_events", []),
                    "themes_mentioned": analysis_data.get("themes_mentioned", []),
                    "locations_mentioned": analysis_data.get("locations_mentioned", []),
                }
                
                return record_keeper_entry
                
            except Exception as e:
                logger.error(f"Failed to parse analysis JSON for chapter {chapter_number}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error summarizing chapter for Record Keeper: {e}")
            return None
    
    def create_or_update_record_keeper_entry(
        self,
        project_id: str,
        record_keeper_data: Dict[str, Any]
    ) -> Optional[int]:
        """
        Create or update a Record Keeper entry.
        
        Args:
            project_id: Project UUID
            record_keeper_data: Dictionary with Record Keeper fields
            
        Returns:
            Vertex ID of created/updated entry, or None on error
        """
        try:
            chapter_number = record_keeper_data.get("chapter_number")
            chapter_title = record_keeper_data.get("chapter_title", f"Chapter {chapter_number}")
            
            # Check if Record Keeper entry already exists for this chapter
            existing_entry = self._find_record_keeper_entry(project_id, chapter_number)
            
            if existing_entry:
                # Update existing entry
                vertex_id = existing_entry['vertex_id']
                updated_properties = {
                    **existing_entry.get('properties', {}),
                    **record_keeper_data
                }
                
                success = self.records_manager.update_entity(
                    project_id=project_id,
                    vertex_id=vertex_id,
                    entity_name=chapter_title,
                    properties=updated_properties
                )
                
                if success:
                    return vertex_id
                else:
                    logger.error(f"Failed to update Record Keeper entry for chapter {chapter_number}")
                    return None
            else:
                # Create new entry
                vertex_id = self.records_manager.create_entity(
                    project_id=project_id,
                    entity_name=chapter_title,
                    entity_type="record_keeper",
                    properties=record_keeper_data,
                    vertex_label="RecordKeeper"
                )
                
                return vertex_id
                
        except Exception as e:
            logger.error(f"Error creating/updating Record Keeper entry: {e}")
            return None
    
    def _find_record_keeper_entry(self, project_id: str, chapter_number: str) -> Optional[Dict[str, Any]]:
        """
        Find existing Record Keeper entry for a chapter.
        
        Args:
            project_id: Project UUID
            chapter_number: Chapter number as string
            
        Returns:
            Entity dict if found, None otherwise
        """
        try:
            entities = self.records_manager.get_project_entities(project_id, entity_type="record_keeper")
            
            for entity in entities:
                props = entity.get('properties', {})
                if props.get('chapter_number') == chapter_number:
                    return entity
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding Record Keeper entry: {e}")
            return None
    
    def summarize_entities_by_category(
        self,
        project_id: str,
        workspace_id: str,
        category: str,
        mode: str = "all",
        entity_ids: Optional[List[str]] = None,
        chapter_orders: Optional[List[int]] = None,
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Generate chapter-by-chapter summaries for entities of a specific category.
        
        Args:
            project_id: Project UUID
            workspace_id: Workspace UUID for content retrieval
            category: Category name (e.g., "character", "location", "faction")
            mode: "all" to process all entities, "focused" to process specific entity_ids
            entity_ids: List of vertex_ids to process (for focused mode)
            chapter_orders: Optional list of chapter orders (None = all chapters)
            model: AI model to use
            provider: AI provider
            
        Returns:
            Dictionary with summarization results
        """
        try:
            results = {
                'entities_processed': 0,
                'entities_updated': 0,
                'errors': []
            }
            
            # Map category name to entity_type for querying
            entity_type = category.lower().replace(' ', '_')
            type_mapping = {
                'character': 'character',
                'location': 'location',
                'item': 'item',
                'theme': 'theme',
                'plot point': 'plot_point',
                'plot_point': 'plot_point',
            }
            entity_type = type_mapping.get(entity_type, entity_type)
            
            # Get entities of the specified category
            logger.info(f"Fetching entities for category '{category}' (entity_type='{entity_type}')")
            all_entities = self.records_manager.get_project_entities(project_id, entity_type=entity_type)
            
            if not all_entities:
                # Try to get all entities to see what types exist
                all_project_entities = self.records_manager.get_project_entities(project_id)
                existing_types = set(e.get('type', 'unknown') for e in all_project_entities) if all_project_entities else set()
                logger.warning(f"No {category} entities found (entity_type='{entity_type}'). Project has {len(all_project_entities or [])} total entities of types: {existing_types}")
                return {**results, 'error': f'No {category} entities found. You need to run Entity Extraction for this category first. Existing entity types in project: {list(existing_types)}'}
            
            # Filter to specific entities if in focused mode
            if mode == "focused" and entity_ids:
                entity_ids_set = set(str(eid) for eid in entity_ids)
                entities_to_process = [e for e in all_entities if str(e.get('vertex_id')) in entity_ids_set]
            else:
                entities_to_process = all_entities
            
            if not entities_to_process:
                return {**results, 'error': 'No entities match the specified criteria'}
            
            logger.info(f"Processing {len(entities_to_process)} {category} entities for summarization")
            
            # Get all chapters with content
            all_chapters = self.get_chapters(project_id, workspace_id)
            if not all_chapters:
                return {**results, 'error': 'No chapters found'}
            
            # Filter chapters if specific ones requested
            if chapter_orders is not None:
                chapters_to_process = [ch for ch in all_chapters if ch.get('order') in chapter_orders]
            else:
                chapters_to_process = all_chapters
            
            if not chapters_to_process:
                return {**results, 'error': 'No chapters match the specified orders'}
            
            # Build chapter content map
            chapter_content_map = {}
            for chapter in chapters_to_process:
                chapter_order = chapter.get('order', 0)
                chapter_name = chapter.get('chapter_name', f"Chapter {chapter_order + 1}")
                chapter_content = chapter.get('content', '')
                if chapter_content and len(chapter_content.strip()) >= 100:
                    chapter_content_map[chapter_order] = {
                        'name': chapter_name,
                        'content': chapter_content
                    }
            
            if not chapter_content_map:
                return {**results, 'error': 'No chapters have sufficient content (minimum 100 characters)'}
            
            logger.info(f"Chapter content map has {len(chapter_content_map)} chapters: {list(chapter_content_map.keys())}")
            
            # Create caller for generation requests
            caller = self._create_caller(project_id, workspace_id)
            
            # Process each entity
            for entity in entities_to_process:
                entity_name = entity.get('name', 'Unknown')
                vertex_id = entity.get('vertex_id')
                results['entities_processed'] += 1
                
                try:
                    logger.info(f"Generating summaries for {category} entity: {entity_name}")
                    
                    # Generate chapter summaries for this entity
                    summaries = self._generate_entity_chapter_summaries(
                        entity_name=entity_name,
                        entity_type=category,
                        entity_properties=entity.get('properties', {}),
                        chapter_content_map=chapter_content_map,
                        model=model,
                        provider=provider,
                        caller=caller
                    )
                    
                    print(f"[DEBUG] After _generate_entity_chapter_summaries: got {len(summaries) if summaries else 0} summaries for {entity_name}", flush=True)
                    
                    if summaries:
                        # Update entity with summaries
                        existing_props = entity.get('properties', {})
                        existing_props['_summaries'] = summaries
                        
                        print(f"[DEBUG] Attempting to save {len(summaries)} summaries for {entity_name} (vertex_id: {vertex_id}, type: {type(vertex_id).__name__})", flush=True)
                        logger.info(f"Attempting to save {len(summaries)} summaries for {entity_name} (vertex_id: {vertex_id}, type: {type(vertex_id)})")
                        
                        # Ensure vertex_id is the right type for the records manager
                        vid = vertex_id
                        if isinstance(vertex_id, str):
                            try:
                                vid = int(vertex_id)
                                print(f"[DEBUG] Converted vertex_id from str to int: {vid}", flush=True)
                            except ValueError:
                                print(f"[DEBUG] Could not convert vertex_id '{vertex_id}' to int, using as-is", flush=True)
                                logger.warning(f"Could not convert vertex_id '{vertex_id}' to int, using as-is")
                        
                        print(f"[DEBUG] Calling records_manager.update_entity with project_id={project_id}, vertex_id={vid}", flush=True)
                        success = self.records_manager.update_entity(
                            project_id=project_id,
                            vertex_id=vid,
                            properties=existing_props
                        )
                        print(f"[DEBUG] update_entity returned: {success}", flush=True)
                        
                        if success:
                            results['entities_updated'] += 1
                            print(f"[DEBUG] SUCCESS: Updated {entity_name} with {len(summaries)} chapter summaries", flush=True)
                            logger.info(f"SUCCESS: Updated {entity_name} with {len(summaries)} chapter summaries")
                        else:
                            error_msg = f"FAILED: update_entity returned False for {entity_name} (vertex_id: {vid})"
                            print(f"[DEBUG] {error_msg}", flush=True)
                            logger.error(error_msg)
                            results['errors'].append(error_msg)
                    else:
                        print(f"[DEBUG] No summaries generated for {entity_name} - summaries list is empty", flush=True)
                        logger.warning(f"No summaries generated for {entity_name} - summaries list is empty")
                        
                except Exception as e:
                    error_msg = f"Error processing entity {entity_name}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    results['errors'].append(error_msg)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in summarize_entities_by_category: {e}", exc_info=True)
            return {'error': str(e)}
    
    def _generate_entity_chapter_summaries(
        self,
        entity_name: str,
        entity_type: str,
        entity_properties: Dict[str, Any],
        chapter_content_map: Dict[int, Dict[str, str]],
        model: str,
        provider: str,
        caller: QuotaCaller
    ) -> List[Dict[str, Any]]:
        """
        Generate chapter-by-chapter summaries for a single entity.
        
        Args:
            entity_name: Name of the entity
            entity_type: Type/category of the entity
            entity_properties: Existing properties of the entity
            chapter_content_map: Map of chapter_order -> {name, content}
            model: AI model to use
            provider: AI provider
            caller: QuotaCaller for generation
            
        Returns:
            List of chapter summaries
        """
        try:
            summaries = []
            
            # Build context about the entity
            entity_context = f"Entity Name: {entity_name}\nEntity Type: {entity_type}\n"
            if entity_properties:
                # Include relevant properties (exclude internal ones)
                relevant_props = {k: v for k, v in entity_properties.items() 
                                 if not k.startswith('_') and k not in ['name', 'type']}
                if relevant_props:
                    entity_context += f"Known Properties: {json.dumps(relevant_props, indent=2)}\n"
            
            # Process each chapter
            for chapter_order in sorted(chapter_content_map.keys()):
                chapter_info = chapter_content_map[chapter_order]
                chapter_name = chapter_info['name']
                chapter_content = chapter_info['content']
                
                # Build prompt for this chapter
                prompt = f"""You are analyzing a {entity_type} entity's appearance in a chapter of a story.

ENTITY INFORMATION:
{entity_context}

CHAPTER: {chapter_name} (Chapter {chapter_order + 1})

CHAPTER CONTENT:
{chapter_content}

TASK: Analyze how "{entity_name}" appears in this chapter. If the entity is mentioned or appears:
1. Describe their activity, actions, or role in this chapter
2. Identify key moments involving this entity
3. Note any character development, reveals, or significant events

If the entity does NOT appear in this chapter, respond with:
{{"appears": false}}

If the entity DOES appear, respond with:
{{
  "appears": true,
  "activity": "Detailed description of what {entity_name} does, experiences, or how they are referenced in this chapter",
  "key_moments": ["Specific important moment 1", "Specific important moment 2"]
}}

OUTPUT (JSON only):"""

                # Create generation request
                request = BaseGenerationRequest(
                    prompt=prompt,
                    provider=provider,
                    model=model,
                    instruction=f"Analyze {entity_name}'s appearance in chapter and return JSON.",
                    generation_config=GenerationConfig(
                        temperature=0.5,
                        max_output_tokens=1500,
                    ),
                    caller=caller
                )
                
                # Generate analysis
                engine = GenerationEngine(request)
                response = engine.generate(skip_quota=True)
                
                if not response.success:
                    logger.warning(f"Failed to analyze {entity_name} in chapter {chapter_order + 1}: {response.error_message}")
                    continue
                
                # Parse response
                try:
                    print(f"[DEBUG] Parsing LLM response for {entity_name} in chapter {chapter_order + 1}", flush=True)
                    analysis_data, _ = JSONResponseParser.parse_response(
                        response.text,
                        expected_type="dict",
                        fallback_value={}
                    )
                    
                    print(f"[DEBUG] Analysis result for {entity_name} in chapter {chapter_order + 1}: appears={analysis_data.get('appears')}", flush=True)
                    logger.info(f"Analysis result for {entity_name} in chapter {chapter_order + 1}: appears={analysis_data.get('appears')}")
                    
                    if analysis_data.get('appears', False):
                        summary = {
                            'chapter_number': chapter_order + 1,
                            'chapter_name': chapter_name,
                            'activity': analysis_data.get('activity', ''),
                            'key_moments': analysis_data.get('key_moments', [])
                        }
                        summaries.append(summary)
                        print(f"[DEBUG] {entity_name} APPEARS in chapter {chapter_order + 1} - added to summaries (total: {len(summaries)})", flush=True)
                        logger.info(f"{entity_name} APPEARS in chapter {chapter_order + 1} - added to summaries (total: {len(summaries)})")
                    else:
                        print(f"[DEBUG] {entity_name} does NOT appear in chapter {chapter_order + 1}", flush=True)
                        logger.info(f"{entity_name} does NOT appear in chapter {chapter_order + 1}")
                        
                except Exception as e:
                    logger.warning(f"Failed to parse analysis for {entity_name} in chapter {chapter_order + 1}: {e}")
                    continue
            
            return summaries
            
        except Exception as e:
            logger.error(f"Error generating entity chapter summaries: {e}", exc_info=True)
            return []
    
    def get_collection_types(self, project_id: str) -> Dict[str, Any]:
        """
        Get all collection types (system + custom) with field schemas.

        Args:
            project_id: Project UUID

        Returns:
            Dictionary with system and custom collection types
        """
        from utils.database_utils import utf8_database_connection

        try:
            with utf8_database_connection(self.db_pool, operation_name="get_collection_types") as conn:
                with conn.cursor() as cursor:
                    # Get custom types from database
                    logger.debug(f"Querying custom types for project_id: {project_id}")
                    cursor.execute("""
                        SELECT name, vertex_label, field_schema
                        FROM record_entity_types
                        WHERE project_id = %s AND is_system = false
                    """, (project_id,))
                    
                    custom_types = []
                    rows = cursor.fetchall()
                    logger.debug(f"Found {len(rows)} custom type rows in database")
                    
                    for row in rows:
                        name, vertex_label, field_schema_json = row
                        field_schema = json.loads(field_schema_json) if field_schema_json else []
                        custom_types.append({
                            'name': name,
                            'vertex_label': vertex_label,
                            'field_schema': field_schema,
                            'is_system': False
                        })
                        logger.debug(f"  Custom type: name='{name}', vertex_label='{vertex_label}', fields={len(field_schema)}")
                    
                    # System types (hardcoded - same as Laravel)
                    system_types = [
                        {'name': 'Character', 'vertex_label': 'Character', 'field_schema': [], 'is_system': True},
                        {'name': 'Location', 'vertex_label': 'Location', 'field_schema': [], 'is_system': True},
                        {'name': 'Item', 'vertex_label': 'Item', 'field_schema': [], 'is_system': True},
                        {'name': 'Theme', 'vertex_label': 'Theme', 'field_schema': [], 'is_system': True},
                        {'name': 'Plot Point', 'vertex_label': 'PlotPoint', 'field_schema': [], 'is_system': True},
                    ]
                    
                    logger.info(f"get_collection_types: {len(system_types)} system + {len(custom_types)} custom types for project {project_id}")
                    
                    return {
                        'system': system_types,
                        'custom': custom_types
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get collection types for project {project_id}: {e}", exc_info=True)
            return {'system': [], 'custom': []}
    
    def _build_entity_extraction_prompt(
        self,
        manuscript_content: str,
        categories: List[Dict[str, Any]],
        progressive_summary: str = ""
    ) -> str:
        """
        Build dynamic entity extraction prompt based on categories and field schemas.
        
        Args:
            manuscript_content: Combined content from all chapters
            categories: List of category dicts with name, vertex_label, field_schema
            progressive_summary: Optional progressive summary for context
            
        Returns:
            Formatted prompt string
        """
        # Build category instructions with field schemas
        category_instructions = []
        for category in categories:
            cat_name = category['name']
            field_schema = category.get('field_schema', [])
            cat_lower = cat_name.lower()
            
            instruction = f"\n{cat_name.upper()}S:\n"
            
            # Add category-specific detection guidance
            if cat_lower == 'character':
                instruction += "- Find ALL people, beings, or named individuals (protagonists, antagonists, side characters, mentioned figures)\n"
                instruction += "- Include characters who are only referenced or talked about, not just those who appear directly\n"
                instruction += "- Extract: name, traits, role, description, emotional_state\n"
            elif cat_lower == 'location':
                instruction += "- Find ALL places: cities, buildings, rooms, landscapes, regions, kingdoms, realms\n"
                instruction += "- Include places mentioned in passing or referenced in dialogue\n"
                instruction += "- Extract: name, description, atmosphere, significance\n"
            elif cat_lower == 'item':
                instruction += "- Find ALL significant objects: weapons, artifacts, tools, possessions, documents, clothing\n"
                instruction += "- Include items that characters interact with, mention, or that have plot significance\n"
                instruction += "- Extract: name, description, significance, who_owns_uses\n"
            elif cat_lower == 'theme':
                instruction += "- Identify underlying THEMES: abstract concepts like love, betrayal, power, redemption, identity, survival\n"
                instruction += "- Look for recurring motifs, moral questions, and symbolic meanings in the narrative\n"
                instruction += "- These are NOT physical things - they are ideas and concepts explored through the story\n"
                instruction += "- Extract: name (the theme concept), description (what it represents), significance (how it manifests)\n"
            elif cat_lower in ['plot point', 'plot_point']:
                instruction += "- Identify KEY STORY EVENTS: turning points, revelations, conflicts, decisions, confrontations\n"
                instruction += "- These are significant moments that change the story direction or reveal important information\n"
                instruction += "- Include: battles, discoveries, betrayals, arrivals, departures, deaths, alliances formed\n"
                instruction += "- Extract: name (brief title for the event), description (what happened), significance (impact on story)\n"
            else:
                # CUSTOM CATEGORY - Generate dynamic, intelligent guidance
                # The LLM should understand what to look for based on the category name
                instruction += f"- This is a CUSTOM CATEGORY defined by the user: \"{cat_name}\"\n"
                instruction += f"- Think carefully about what \"{cat_name}\" means in the context of a story/narrative\n"
                instruction += f"- Identify ALL entities that could be classified as \"{cat_name}\"\n"
                instruction += f"- Consider: What would a reader identify as a \"{cat_name}\" in this text?\n"
                instruction += f"- Be creative and thorough - the user created this category for a reason\n"
                instruction += f"- If \"{cat_name}\" suggests groups/organizations, look for collectives, tribes, factions, guilds, etc.\n"
                instruction += f"- If \"{cat_name}\" suggests concepts/ideas, look for abstract themes, philosophies, beliefs, etc.\n"
                instruction += f"- If \"{cat_name}\" suggests events, look for occurrences, incidents, phenomena, etc.\n"
                instruction += f"- Include both explicitly named and contextually referenced {cat_lower}s\n"
            
            if field_schema:
                # User has defined custom fields - use them to guide extraction
                instruction += f"- The user has defined the following fields for this category. Extract these for each {cat_lower}:\n"
                for field in field_schema:
                    field_name = field.get('name', '')
                    field_label = field.get('label', field_name)
                    field_type = field.get('type', 'text')
                    field_desc = field.get('description', '')
                    instruction += f"  * {field_label} ({field_type}){': ' + field_desc if field_desc else ''}\n"
            elif cat_lower not in ['character', 'location', 'item', 'theme', 'plot point', 'plot_point']:
                # Custom category without field schema - use intelligent defaults
                instruction += "- Extract: name, description, significance, and any other relevant attributes you can identify\n"
            
            category_instructions.append(instruction)
        
        categories_text = "\n".join(category_instructions)
        
        # Build JSON template dynamically based on categories
        json_template_parts = []
        for category in categories:
            cat_name = category['name']
            field_schema = category.get('field_schema', [])
            
            # Determine the JSON key (plural form)
            cat_key = cat_name.lower().replace(' ', '_')
            # Only map known system categories, custom categories use their name + 's'
            system_key_mapping = {
                'character': 'characters',
                'location': 'locations',
                'item': 'items',
                'theme': 'themes',
                'plot_point': 'plot_points',
                'plotpoint': 'plot_points',
            }
            json_key = system_key_mapping.get(cat_key, cat_key + 's')  # Custom categories default to plural
            
            # Build example entity structure
            example_fields = []
            if field_schema:
                for field in field_schema:
                    field_name = field.get('name', '')
                    field_type = field.get('type', 'text')
                    if field_type == 'array':
                        example_fields.append(f'      "{field_name}": ["value1", "value2"]')
                    elif field_type == 'number':
                        example_fields.append(f'      "{field_name}": 0')
                    elif field_type == 'boolean':
                        example_fields.append(f'      "{field_name}": true')
                    else:
                        example_fields.append(f'      "{field_name}": "example value"')
            else:
                # Default fields for system categories
                if cat_name.lower() == 'character':
                    example_fields = [
                        '      "name": "Character Name"',
                        '      "traits": ["brave", "intelligent"]',
                        '      "role": "protagonist"',
                        '      "description": "Physical and personality description"',
                        '      "emotional_state": "determined"'
                    ]
                elif cat_name.lower() == 'location':
                    example_fields = [
                        '      "name": "Location Name"',
                        '      "description": "Physical description"',
                        '      "atmosphere": "mood/feeling"',
                        '      "significance": "plot importance"'
                    ]
                elif cat_name.lower() == 'item':
                    example_fields = [
                        '      "name": "Item Name"',
                        '      "description": "Physical description"',
                        '      "significance": "plot importance"',
                        '      "who_owns_uses": "Character or entity who owns/uses this"'
                    ]
                elif cat_name.lower() == 'theme':
                    example_fields = [
                        '      "name": "Theme Name"',
                        '      "description": "What this theme represents"',
                        '      "significance": "How it appears in the story"'
                    ]
                elif cat_name.lower() in ['plot point', 'plotpoint']:
                    example_fields = [
                        '      "name": "Plot Point Name"',
                        '      "description": "What happens"',
                        '      "significance": "Importance to story"'
                    ]
                else:
                    # CUSTOM CATEGORY - Build dynamic template
                    # Always include name and description as base fields
                    example_fields = [
                        f'      "name": "{cat_name} Name"',
                        '      "description": "Detailed description of this entity"',
                        '      "significance": "Why this matters to the story"',
                        '      "related_elements": ["Related character/location/item 1", "Related element 2"]'
                    ]
            
            example_entity = "    {\n" + ",\n".join(example_fields) + "\n    }"
            json_template_parts.append(f'  "{json_key}": [\n{example_entity}\n  ]')
        
        json_template = "{\n" + ",\n".join(json_template_parts) + "\n}"
        
        prompt = f"""You are a narrative entity extraction specialist. Extract SIGNIFICANT entities from the manuscript to build a knowledge graph.

PROGRESSIVE STORY CONTEXT:
{progressive_summary if progressive_summary else "This is the beginning of the story."}

MANUSCRIPT CONTENT:
{manuscript_content}

EXTRACTION REQUIREMENTS:

{categories_text}

OUTPUT FORMAT (JSON):
{json_template}

EXTRACTION GUIDELINES:

1. FOCUS ON SIGNIFICANCE - Extract entities that are:
   - Named explicitly (proper nouns, titles)
   - Play an active role in the story
   - Have relationships with other entities
   - Are referenced multiple times or are plot-relevant

2. AVOID EXTRACTING:
   - Generic descriptions (e.g., "the sky", "the horizon", "the ground")
   - Momentary metaphors or figures of speech
   - Body parts or common objects unless they have story significance
   - Abstract directions or times unless they're named places

3. FOR CUSTOM CATEGORIES (like groups, factions, organizations):
   - Look for named groups (e.g., "the Misaguwan forces", "Lawredinian army")
   - Include races/species if they function as groups
   - Include political factions, military units, religions, guilds
   - A group mentioned as "the enemy" or "the tribe" counts if it has identity

4. USE EXACT NAMES from the text when available
5. ALWAYS INCLUDE THE CATEGORY KEY in your response, even if empty (use [])

Quality over quantity - extract entities that matter to the story.

EXTRACTED ENTITIES:"""
        
        return prompt
    
    def extract_entities(
        self,
        project_id: str,
        workspace_id: str,
        categories: List[str],  # List of category names or ["all_categories"]
        chapter_orders: Optional[List[int]] = None,
        model: str = "gemini-2.5-flash",
        provider: str = "gemini",
        scan_mode: str = "incremental"  # "incremental", "full", or "new_only"
    ) -> Dict[str, Any]:
        """
        Extract entities from manuscript for specified categories.
        
        Args:
            project_id: Project UUID
            workspace_id: Workspace UUID (for content retrieval)
            categories: List of category names or ["all_categories"]
            chapter_orders: Optional list of chapter orders (None = all chapters)
            model: AI model to use
            provider: AI provider
            scan_mode: "incremental" (only changed/new), "full" (rescan all), "new_only" (only unscanned)
            
        Returns:
            Dictionary with extraction results per category
        """
        try:
            # Get chapters based on scan mode
            if chapter_orders is not None:
                # If specific chapters requested, use those
                all_chapters = self.get_chapters(project_id, workspace_id)
                chapters_to_process = [
                    ch for ch in all_chapters 
                    if ch.get('order') in chapter_orders
                ]
                scan_info = {'mode': 'manual', 'chapters_to_process': len(chapters_to_process)}
            else:
                # Use scan mode to determine which chapters to process
                chapters_to_process, scan_info = self.get_chapters_to_process(
                    project_id, workspace_id, mode=scan_mode
                )
            
            if not chapters_to_process:
                return {
                    'error': 'No chapters to process',
                    'scan_info': scan_info,
                    'message': 'All chapters are up-to-date (no changes detected)' if scan_mode == 'incremental' else 'No chapters match criteria'
                }
            
            # Combine chapter content
            manuscript_content = ""
            for chapter in chapters_to_process:
                chapter_name = chapter.get('chapter_name', f"Chapter {chapter.get('order', '')}")
                chapter_content = chapter.get('content', '')
                if chapter_content:
                    manuscript_content += f"\n\n--- {chapter_name} ---\n{chapter_content}"
            
            if not manuscript_content.strip():
                return {'error': 'No content found in chapters'}
            
            # Get collection types
            collection_types = self.get_collection_types(project_id)
            all_types = collection_types['system'] + collection_types['custom']
            
            # Debug logging for category resolution
            logger.info(f"Found {len(collection_types.get('system', []))} system types and {len(collection_types.get('custom', []))} custom types")
            for ct in collection_types.get('custom', []):
                logger.info(f"  Custom type available: name='{ct.get('name')}', vertex_label='{ct.get('vertex_label')}'")
            
            # Filter out Record Keeper (not a category for extraction)
            all_types = [t for t in all_types if t['name'].lower() != 'record keeper']
            
            # Determine which categories to process
            if "all_categories" in categories:
                categories_to_process = all_types
                logger.info(f"Processing ALL categories: {[t['name'] for t in all_types]}")
            else:
                # Map category names to type objects
                categories_to_process = []
                for cat_name in categories:
                    logger.info(f"Looking for category: '{cat_name}'")
                    found = False
                    # Find matching type (case-insensitive)
                    for type_obj in all_types:
                        if type_obj['name'].lower() == cat_name.lower() or \
                           type_obj['vertex_label'].lower() == cat_name.lower().replace(' ', ''):
                            categories_to_process.append(type_obj)
                            logger.info(f"  FOUND: '{type_obj['name']}' (vertex_label: {type_obj['vertex_label']})")
                            found = True
                            break
                    if not found:
                        logger.warning(f"  NOT FOUND: Category '{cat_name}' does not exist in system or custom types")
            
            if not categories_to_process:
                logger.error(f"No valid categories found. Requested: {categories}. Available: {[t['name'] for t in all_types]}")
                return {'error': f'No valid categories found. Requested: {categories}. Available categories: {[t["name"] for t in all_types]}'}
            
            results = {
                'entities_created': 0,
                'entities_updated': 0,
                'categories_processed': {},
                'errors': []
            }
            
            # Create caller for generation requests
            caller = self._create_caller(project_id, workspace_id)
            
            # Process each category
            for category in categories_to_process:
                cat_name = category['name']
                logger.info(f"Extracting {cat_name} entities from manuscript")
                
                try:
                    # Build extraction prompt for this category
                    prompt = self._build_entity_extraction_prompt(
                        manuscript_content=manuscript_content,
                        categories=[category],
                        progressive_summary=""
                    )
                    
                    # Create generation request
                    request = BaseGenerationRequest(
                        prompt=prompt,
                        provider=provider,
                        model=model,
                        instruction=f"Extract {cat_name} entities from manuscript in JSON format.",
                        generation_config=GenerationConfig(
                            temperature=0.7,
                            max_output_tokens=4000,  # More tokens for comprehensive extraction
                        ),
                        caller=caller
                    )
                    
                    # Generate extraction
                    engine = GenerationEngine(request)
                    response = engine.generate(skip_quota=True)
                    
                    if not response.success:
                        error_msg = f"Failed to extract {cat_name} entities: {response.error_message}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                        continue
                    
                    # Parse JSON response - use entity extraction parser that preserves ALL keys
                    from utils.json_response_parser import parse_entity_extraction_response
                    graph_data = parse_entity_extraction_response(response)
                    
                    # Debug: Log raw response for troubleshooting
                    logger.info(f"LLM response for {cat_name}: keys={list(graph_data.keys())}, raw_text_length={len(response.text) if response.text else 0}")
                    if not graph_data:
                        logger.warning(f"Empty graph_data returned for {cat_name}. Raw response: {response.text[:500] if response.text else 'None'}")
                    
                    # Map category to entity type key in response
                    entity_type_key = cat_name.lower().replace(' ', '_')
                    
                    # Map singular system category names to plural form
                    system_category_mapping = {
                        'character': 'characters',
                        'location': 'locations',
                        'item': 'items',
                        'theme': 'themes',
                        'plot_point': 'plot_points',
                        'plotpoint': 'plot_points',  # Handle vertex_label format
                    }
                    
                    # Check if it's a system category and map to plural
                    if entity_type_key in system_category_mapping:
                        entity_type_key = system_category_mapping[entity_type_key]
                        logger.debug(f"System category '{cat_name}' mapped to key '{entity_type_key}'")
                    elif entity_type_key not in ['characters', 'locations', 'items', 'themes', 'plot_points']:
                        # Custom category - search for matching key in response
                        logger.info(f"Looking for custom category key for '{cat_name}' in response keys: {list(graph_data.keys())}")
                        entity_type_key = None
                        cat_lower = cat_name.lower()
                        cat_underscore = cat_lower.replace(' ', '_')
                        
                        for key in graph_data.keys():
                            key_lower = key.lower()
                            # Try multiple matching strategies
                            if (key_lower == cat_lower or                           # exact match
                                key_lower == cat_lower + 's' or                     # plural form  
                                key_lower == cat_underscore or                      # underscore form
                                key_lower == cat_underscore + 's' or                # underscore plural
                                key_lower.rstrip('s') == cat_lower or               # singular from plural
                                key_lower.rstrip('s') == cat_underscore):           # singular underscore
                                entity_type_key = key
                                logger.info(f"MATCHED custom category key '{key}' for category '{cat_name}'")
                                break
                        
                        if not entity_type_key:
                            logger.warning(f"Could not find matching key for custom category '{cat_name}'. Tried: {cat_lower}, {cat_lower}s, {cat_underscore}, {cat_underscore}s")
                    
                    if not entity_type_key or entity_type_key not in graph_data:
                        logger.warning(f"No {cat_name} entities found in extraction response. Available keys: {list(graph_data.keys())}")
                        results['categories_processed'][cat_name] = {
                            'created': 0,
                            'updated': 0
                        }
                        continue
                    
                    entities = graph_data[entity_type_key]
                    cat_created = 0
                    cat_updated = 0
                    
                    # Store entities
                    for entity in entities:
                        entity_name = entity.get('name', '').strip()
                        if not entity_name:
                            continue
                        
                        # Extract properties (exclude name)
                        properties = {k: v for k, v in entity.items() if k != 'name'}
                        
                        # Check if entity exists
                        # Map category name to entity_type for querying (consistent with metadata storage)
                        # System types: "Character" -> "character", "Plot Point" -> "plot_point"
                        # Custom types: use name as-is, converted to lowercase with underscores
                        category_name = category.get('name', '')
                        entity_type_for_query = category_name.lower().replace(' ', '_')
                        
                        # Special handling for system types to match metadata storage
                        # Custom categories use their name as-is (lowercase with underscores)
                        system_type_mapping = {
                            'character': 'character',
                            'location': 'location',
                            'item': 'item',
                            'theme': 'theme',
                            'plot point': 'plot_point',
                            'plotpoint': 'plot_point',  # Handle vertex_label format
                        }
                        entity_type_for_query = system_type_mapping.get(entity_type_for_query, entity_type_for_query)
                        
                        logger.debug(f"Checking for existing {cat_name} entities with entity_type: {entity_type_for_query}")
                        existing_entities = self.records_manager.get_project_entities(
                            project_id, 
                            entity_type=entity_type_for_query
                        )
                        logger.debug(f"Found {len(existing_entities)} existing {cat_name} entities")
                        
                        existing = None
                        for e in existing_entities:
                            if e.get('name', '').lower() == entity_name.lower():
                                existing = e
                                logger.debug(f"Found existing entity: {entity_name} (vertex_id: {e.get('vertex_id')})")
                                break
                        
                        if existing:
                            # Update existing entity (merge properties)
                            updated_properties = {
                                **existing.get('properties', {}),
                                **properties
                            }
                            logger.info(f"Updating existing entity: {entity_name} (vertex_id: {existing['vertex_id']})")
                            success = self.records_manager.update_entity(
                                project_id=project_id,
                                vertex_id=existing['vertex_id'],
                                entity_name=entity_name,
                                properties=updated_properties
                            )
                            if success:
                                cat_updated += 1
                                logger.info(f"Successfully updated entity: {entity_name}")
                            else:
                                logger.error(f"Failed to update entity: {entity_name}")
                        else:
                            # Create new entity
                            # Use consistent entity_type mapping (same as query)
                            logger.info(f"Creating new entity: {entity_name} (type: {entity_type_for_query}, vertex_label: {category['vertex_label']})")
                            vertex_id = self.records_manager.create_entity(
                                project_id=project_id,
                                entity_name=entity_name,
                                entity_type=entity_type_for_query,
                                properties=properties,
                                vertex_label=category['vertex_label']
                            )
                            if vertex_id:
                                cat_created += 1
                                logger.info(f"Successfully created entity: {entity_name} (vertex_id: {vertex_id}, type: {entity_type_for_query})")
                            else:
                                logger.error(f"Failed to create entity: {entity_name} (type: {entity_type_for_query}) - create_entity returned None")
                    
                    results['entities_created'] += cat_created
                    results['entities_updated'] += cat_updated
                    results['categories_processed'][cat_name] = {
                        'created': cat_created,
                        'updated': cat_updated
                    }
                    
                    # Track extracted entity names for this category
                    extracted_names = [e.get('name', '') for e in entities if e.get('name')]
                    if 'entities_by_category' not in results:
                        results['entities_by_category'] = {}
                    results['entities_by_category'][cat_name] = extracted_names
                    
                    logger.info(f"Extracted {cat_name}: {cat_created} created, {cat_updated} updated")
                    
                except Exception as e:
                    error_msg = f"Error extracting {cat_name} entities: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    results['errors'].append(error_msg)
            
            # Update scan metadata for processed chapters
            all_extracted_entities = []
            categories_processed = list(results.get('entities_by_category', {}).keys())
            for cat_entities in results.get('entities_by_category', {}).values():
                all_extracted_entities.extend(cat_entities)
            
            for chapter in chapters_to_process:
                chapter_order = chapter.get('order', 0)
                content_hash = self._compute_content_hash(chapter.get('content', ''))
                self._update_scan_metadata(
                    project_id=project_id,
                    chapter_order=chapter_order,
                    content_hash=content_hash,
                    scan_type='extraction',
                    entities_found=all_extracted_entities,
                    categories_processed=categories_processed,
                    entity_count=len(all_extracted_entities)
                )
            
            # Add scan info to results
            results['scan_info'] = scan_info
            results['chapters_processed'] = len(chapters_to_process)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in extract_entities: {e}", exc_info=True)
            return {'error': str(e)}
    
    def summarize_entities_for_category(
        self,
        project_id: str,
        category: str,
        entity_ids: Optional[List[int]] = None,
        chapters: Optional[List[Dict[str, Any]]] = None,
        model: str = "gemini-2.5-flash",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Summarize entities of a specific category across chapters.
        
        Args:
            project_id: Project UUID
            category: Entity category (character, location, item, etc.)
            entity_ids: Optional list of specific entity IDs to focus on
            chapters: Optional list of chapters to analyze (if None, uses all)
            model: AI model to use
            provider: AI provider
            
        Returns:
            Dictionary with summary results
        """
        # TODO: Implement entity-specific summarization
        # This will analyze how each entity appears across chapters
        # and update entity summaries in their properties
        pass

