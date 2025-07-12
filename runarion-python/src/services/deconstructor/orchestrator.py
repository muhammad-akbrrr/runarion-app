"""
Main orchestrator for the novel deconstruction pipeline.
Coordinates all 7 stages of processing and manages database operations.
"""

import os
import logging
import traceback
import time
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager

from utils.logging_config import get_pipeline_logger
from models.deconstructor.status import DraftStatus

from .stage_1_ingestion import PDFIngestionStage
from .stage_2_cleaning import TextCleaningStage
# from .stage_3_sceneExtract import SceneDetectionStage
# from .stage_4_analysis.analyzer_4a import SceneBySceneAnalysisStage
# from .stage_4_analysis.analyzer_4b import ProgressiveGraphAnalysisStage
# from .stage_4_analysis.analyzer_4c_reports import ComprehensiveReportingStage
# from .stage_5_coherence import CoherenceCheckStage
# from .stage_6_enhancement import EnhancementStage
# from .stage_7_chaptering import ChapteringStage

logger = get_pipeline_logger(__name__)

class DeconstructorOrchestrator:
    """
    Orchestrates the complete novel deconstruction pipeline.
    Manages stage execution, database operations, and error handling.
    """
    
    def __init__(self, generation_engine, db_pool):
        """
        Initialize the orchestrator with dependencies.
        
        Args:
            generation_engine: AI generation engine instance
            db_pool: Database connection pool
        """
        self.generation_engine = generation_engine
        self.db_pool = db_pool
        
        # Initialize all stages
        self.stages = {
            1: PDFIngestionStage(db_pool),
            2: TextCleaningStage(db_pool, generation_engine),
            # 3: SceneDetectionStage(db_pool, generation_engine),
            # 4: {
            #     'a': SceneBySceneAnalysisStage(db_pool, generation_engine),
            #     'b': ProgressiveGraphAnalysisStage(db_pool, generation_engine),
            #     'c': ComprehensiveReportingStage(db_pool, generation_engine)
            # },
            # 5: CoherenceCheckStage(db_pool, generation_engine),
            # 6: EnhancementStage(db_pool, generation_engine),
            # 7: ChapteringStage(db_pool, generation_engine)
        }
        
    def run_pipeline(self, draft_id: str, file_name: str, 
                    chaptering_mode: str = 'flexible', target_chapter_length: int = 2500,
                    use_transactions: bool = True) -> Dict[str, Any]:
        """
        Run the complete deconstruction pipeline.
        
        Args:
            draft_id: UUID of the draft to process
            file_name: Name of the uploaded file
            chaptering_mode: Chaptering approach ('flexible' or 'constrained')
            target_chapter_length: Target word count per chapter
            use_transactions: Whether to use database transactions for stages
            
        Returns:
            Pipeline execution results
        """
        start_time = datetime.now()
        pipeline_results = {
            'draft_id': draft_id,
            'file_name': file_name,
            'started_at': start_time.isoformat(),
            'stages_completed': [],
            'success': False,
            'error': None
        }
        
        try:
            # Set logging context for this pipeline run
            logger.set_context(
                draft_id=draft_id,
                file_name=file_name,
                chaptering_mode=chaptering_mode,
                target_chapter_length=target_chapter_length,
                use_transactions=use_transactions
            )
            
            logger.pipeline_start(draft_id, file_name=file_name)
            
            # Construct full file path
            upload_path = os.getenv('UPLOAD_PATH', '/app/uploads')
            file_path = os.path.join(upload_path, file_name)
            
            # Update draft status to processing
            self._update_draft_status(draft_id, DraftStatus.PROCESSING.value)
            
            # Choose execution method based on use_transactions flag
            execute_stage = self._execute_stage_with_transaction if use_transactions else self._execute_stage_with_retry
            
            # Stage 1: Ingestion
            stage_start_time = datetime.now()
            logger.stage_start("1", draft_id, stage_name="ingestion")
            stage_1_result = execute_stage(self.stages[1], "1", draft_id, file_path)
            self._update_draft_status(draft_id, DraftStatus.STAGE_1_COMPLETE.value)
            stage_duration = (datetime.now() - stage_start_time).total_seconds()
            logger.stage_complete("1", draft_id, duration_seconds=stage_duration, stage_name="ingestion")
            pipeline_results['stages_completed'].append({
                'stage': 1,
                'name': 'ingestion',
                'completed_at': datetime.now().isoformat(),
                'result': stage_1_result
            })
            
            # Stage 2: Cleaning
            logger.info(f"Starting Stage 2: Cleaning for draft {draft_id}")
            stage_2_result = execute_stage(self.stages[2], "2", draft_id)
            self._update_draft_status(draft_id, DraftStatus.STAGE_2_COMPLETE.value)
            pipeline_results['stages_completed'].append({
                'stage': 2,
                'name': 'cleaning',
                'completed_at': datetime.now().isoformat(),
                'result': stage_2_result
            })
            logger.info(f"Stage 2 completed for draft {draft_id}")
            
            # # Stage 3: Scene Detection
            # logger.info(f"Starting Stage 3: Scene Detection for draft {draft_id}")
            # stage_3_result = execute_stage(self.stages[3], "3", draft_id)
            # self._update_draft_status(draft_id, DraftStatus.STAGE_3_COMPLETE.value)
            # pipeline_results['stages_completed'].append({
            #     'stage': 3,
            #     'name': 'scene_detection',
            #     'completed_at': datetime.now().isoformat(),
            #     'result': stage_3_result
            # })
            # logger.info(f"Stage 3 completed for draft {draft_id}")
            # 
            # # Stage 4: Deep Analysis (3 sub-stages)
            # logger.info(f"Starting Stage 4: Deep Analysis for draft {draft_id}")
            # 
            # # Stage 4A: Scene-by-scene analysis
            # stage_4a_result = execute_stage(self.stages[4]['a'], "4A", draft_id, chaptering_mode, target_chapter_length)
            # pipeline_results['stages_completed'].append({
            #     'stage': '4a',
            #     'name': 'scene_analysis',
            #     'completed_at': datetime.now().isoformat(),
            #     'result': stage_4a_result
            # })
            # 
            # # Stage 4B: Graph analysis
            # stage_4b_result = execute_stage(self.stages[4]['b'], "4B", draft_id, chaptering_mode, target_chapter_length)
            # pipeline_results['stages_completed'].append({
            #     'stage': '4b',
            #     'name': 'graph_analysis',
            #     'completed_at': datetime.now().isoformat(),
            #     'result': stage_4b_result
            # })
            # 
            # # Stage 4C: Comprehensive reporting
            # stage_4c_result = execute_stage(self.stages[4]['c'], "4C", draft_id, chaptering_mode, target_chapter_length)
            # self._update_draft_status(draft_id, DraftStatus.STAGE_4_COMPLETE.value)
            # pipeline_results['stages_completed'].append({
            #     'stage': '4c',
            #     'name': 'comprehensive_reporting',
            #     'completed_at': datetime.now().isoformat(),
            #     'result': stage_4c_result
            # })
            # logger.info(f"Stage 4 completed for draft {draft_id}")
            # 
            # # Stage 5: Coherence Check
            # logger.info(f"Starting Stage 5: Coherence Check for draft {draft_id}")
            # stage_5_result = execute_stage(self.stages[5], "5", draft_id, chaptering_mode, target_chapter_length)
            # self._update_draft_status(draft_id, DraftStatus.STAGE_5_COMPLETE.value)
            # pipeline_results['stages_completed'].append({
            #     'stage': 5,
            #     'name': 'coherence_check',
            #     'completed_at': datetime.now().isoformat(),
            #     'result': stage_5_result
            # })
            # logger.info(f"Stage 5 completed for draft {draft_id}")
            # 
            # # Stage 6: Enhancement
            # logger.info(f"Starting Stage 6: Enhancement for draft {draft_id}")
            # stage_6_result = execute_stage(self.stages[6], "6", draft_id, chaptering_mode, target_chapter_length)
            # self._update_draft_status(draft_id, DraftStatus.STAGE_6_COMPLETE.value)
            # pipeline_results['stages_completed'].append({
            #     'stage': 6,
            #     'name': 'enhancement',
            #     'completed_at': datetime.now().isoformat(),
            #     'result': stage_6_result
            # })
            # logger.info(f"Stage 6 completed for draft {draft_id}")
            # 
            # # Stage 7: Chaptering
            # logger.info(f"Starting Stage 7: Chaptering for draft {draft_id}")
            # stage_7_result = execute_stage(self.stages[7], "7", draft_id, chaptering_mode, target_chapter_length)
            # pipeline_results['stages_completed'].append({
            #     'stage': 7,
            #     'name': 'chaptering',
            #     'completed_at': datetime.now().isoformat(),
            #     'result': stage_7_result
            # })
            # logger.info(f"Stage 7 completed for draft {draft_id}")
            
            # Mark as completed
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            self._update_draft_status(
                draft_id, 
                DraftStatus.COMPLETED.value, 
                metadata={'processing_time_seconds': processing_time}
            )
            
            pipeline_results.update({
                'success': True,
                'completed_at': end_time.isoformat(),
                'processing_time_seconds': processing_time
            })
            
            logger.pipeline_complete(draft_id, duration_seconds=processing_time)
            
        except Exception as e:
            error_message = str(e)
            error_trace = traceback.format_exc()
            
            logger.pipeline_failed(draft_id, error=error_message)
            logger.debug("Full traceback", traceback=error_trace)
            
            # Update draft status to failed
            self._update_draft_status(draft_id, DraftStatus.FAILED.value, error_message=error_message)
            
            pipeline_results.update({
                'success': False,
                'error': error_message,
                'failed_at': datetime.now().isoformat()
            })
        finally:
            # Clear logging context
            logger.clear_context()
        
        return pipeline_results
    
    def _execute_stage_with_retry(self, stage, stage_number: str, draft_id: str, *args, max_retries: int = 10) -> Dict[str, Any]:
        """
        Execute a stage with retry mechanism.
        
        Args:
            stage: Stage instance to execute
            stage_number: Stage identifier (for logging)
            draft_id: UUID of the draft
            *args: Arguments to pass to the stage
            max_retries: Maximum number of retry attempts
            
        Returns:
            Stage execution result
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                if attempt > 0:
                    logger.stage_retry(stage_number, draft_id, attempt + 1, max_retries + 1)
                
                # Execute the stage
                result = stage.run(draft_id, *args)
                
                return result
                
            except Exception as e:
                last_exception = e
                error_message = str(e)
                
                if attempt < max_retries:
                    # Calculate exponential backoff delay (1s, 2s, 4s, 8s, etc., max 60s)
                    delay = min(2 ** attempt, 60)
                    logger.stage_retry(stage_number, draft_id, attempt + 1, max_retries + 1, error=error_message)
                    logger.debug(f"Retrying stage {stage_number} in {delay} seconds", delay_seconds=delay)
                    time.sleep(delay)
                else:
                    logger.stage_failed(stage_number, draft_id, error=error_message)
                    break
        
        # All retries failed, raise the last exception
        raise last_exception
    
    @contextmanager
    def _database_transaction(self):
        """
        Context manager for database transactions with automatic rollback on error.
        """
        conn = None
        try:
            conn = self.db_pool.getconn()
            conn.autocommit = False  # Ensure we're in transaction mode
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
                logger.error(f"Database transaction rolled back due to error: {e}")
            raise
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def _execute_stage_with_transaction(self, stage, stage_number: str, draft_id: str, *args, max_retries: int = 10) -> Dict[str, Any]:
        """
        Execute a stage within a database transaction with retry mechanism.
        
        Args:
            stage: Stage instance to execute
            stage_number: Stage identifier (for logging)
            draft_id: UUID of the draft
            *args: Arguments to pass to the stage
            max_retries: Maximum number of retry attempts
            
        Returns:
            Stage execution result
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                logger.info(f"Executing stage {stage_number} for draft {draft_id} (attempt {attempt + 1}/{max_retries + 1})")
                
                # Execute the stage within a transaction
                with self._database_transaction() as conn:
                    # Pass connection to stage if it supports it
                    if hasattr(stage, 'run_with_connection'):
                        result = stage.run_with_connection(conn, draft_id, *args)
                    else:
                        result = stage.run(draft_id, *args)
                
                logger.info(f"Stage {stage_number} completed successfully for draft {draft_id}")
                return result
                
            except Exception as e:
                last_exception = e
                logger.warning(f"Stage {stage_number} failed for draft {draft_id} (attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
                
                if attempt < max_retries:
                    # Calculate exponential backoff delay (1s, 2s, 4s, 8s, etc., max 60s)
                    delay = min(2 ** attempt, 60)
                    logger.info(f"Retrying stage {stage_number} in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"Stage {stage_number} failed permanently for draft {draft_id} after {max_retries + 1} attempts")
                    break
        
        # All retries failed, raise the last exception
        raise last_exception
    
    def _update_draft_status(self, draft_id: str, status: str, 
                           error_message: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the draft status in the database.
        
        Args:
            draft_id: UUID of the draft
            status: New status value
            error_message: Optional error message
            metadata: Optional metadata to store
            
        Raises:
            ValueError: If status is not valid
        """
        # Validate status
        if not DraftStatus.is_valid(status):
            raise ValueError(f"Invalid status '{status}'. Valid statuses are: {DraftStatus.get_valid_statuses()}")
        
        conn = None
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                if status == DraftStatus.COMPLETED.value:
                    cursor.execute("""
                        UPDATE drafts 
                        SET status = %s, 
                            processing_completed_at = NOW(),
                            error_message = %s,
                            metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
                        WHERE id = %s
                    """, (status, error_message, metadata or {}, draft_id))
                
                elif status == DraftStatus.FAILED.value:
                    cursor.execute("""
                        UPDATE drafts 
                        SET status = %s, 
                            error_message = %s,
                            processing_completed_at = NOW()
                        WHERE id = %s
                    """, (status, error_message, draft_id))
                
                else:
                    cursor.execute("""
                        UPDATE drafts 
                        SET status = %s,
                            metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
                        WHERE id = %s
                    """, (status, metadata or {}, draft_id))
                
                conn.commit()
            
            logger.debug(f"Updated draft {draft_id} status to {status}")
            
        except Exception as e:
            logger.error(f"Failed to update draft status: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def get_pipeline_status(self, draft_id: str) -> Dict[str, Any]:
        """
        Get the current pipeline status for a draft.
        
        Args:
            draft_id: UUID of the draft
            
        Returns:
            Status information
        """
        conn = None
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT status, processing_started_at, processing_completed_at, 
                           error_message, metadata
                    FROM drafts 
                    WHERE id = %s
                """, (draft_id,))
                
                result = cursor.fetchone()
                
                if not result:
                    return {'error': 'Draft not found'}
                
                status, started_at, completed_at, error_message, metadata = result
                
                status_info = {
                    'draft_id': draft_id,
                    'status': status,
                    'processing_started_at': started_at.isoformat() if started_at else None,
                    'processing_completed_at': completed_at.isoformat() if completed_at else None,
                    'error_message': error_message,
                    'metadata': metadata or {}
                }
                
                # Add progress details
                progress_details = self._get_progress_details(cursor, draft_id)
                status_info['progress'] = progress_details
                
                return status_info
            
        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}")
            return {'error': str(e)}
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def _get_progress_details(self, cursor, draft_id: str) -> Dict[str, Any]:
        """
        Get detailed progress information.
        
        Args:
            cursor: Database cursor
            draft_id: UUID of the draft
            
        Returns:
            Progress details
        """
        details = {}
        
        try:
            # Count chunks
            cursor.execute("SELECT COUNT(*) FROM draft_chunks WHERE draft_id = %s", (draft_id,))
            details['chunks_created'] = cursor.fetchone()[0]
            
            # Count scenes
            cursor.execute("SELECT COUNT(*) FROM scenes WHERE draft_id = %s", (draft_id,))
            details['scenes_extracted'] = cursor.fetchone()[0]
            
            # Count analyzed scenes
            cursor.execute("""
                SELECT COUNT(*) FROM scenes 
                WHERE draft_id = %s AND analysis_json IS NOT NULL
            """, (draft_id,))
            details['scenes_analyzed'] = cursor.fetchone()[0]
            
            # Count plot issues
            cursor.execute("SELECT COUNT(*) FROM plot_issues WHERE draft_id = %s", (draft_id,))
            details['plot_issues_found'] = cursor.fetchone()[0]
            
            # # Count analysis reports
            # cursor.execute("SELECT COUNT(*) FROM analysis_reports WHERE draft_id = %s", (draft_id,))
            # details['analysis_reports_generated'] = cursor.fetchone()[0]
            # 
            # # Count chapters
            # cursor.execute("SELECT COUNT(*) FROM chapters WHERE draft_id = %s", (draft_id,))
            # details['chapters_created'] = cursor.fetchone()[0]
            
        except Exception as e:
            logger.warning(f"Could not get all progress details: {e}")
        
        return details
    
    def cleanup_failed_processing(self, draft_id: str, cleanup_level: str = 'partial') -> Dict[str, Any]:
        """
        Clean up data from a failed processing attempt with comprehensive cleanup options.
        
        Args:
            draft_id: UUID of the draft
            cleanup_level: 'partial' (keep original data), 'full' (remove everything), 'reset' (reset to pending)
            
        Returns:
            Cleanup results with statistics
        """
        cleanup_stats = {
            'draft_id': draft_id,
            'cleanup_level': cleanup_level,
            'tables_cleaned': {},
            'success': False,
            'error': None
        }
        
        conn = None
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                # Track what we're cleaning
                tables_to_clean = []
                
                if cleanup_level in ['partial', 'full', 'reset']:
                    # Always clean generated content
                    tables_to_clean.extend([
                        # ('chapters', 'draft_id'),
                        # ('final_manuscripts', 'draft_id'),
                        # ('analysis_reports', 'draft_id'),
                        ('plot_issues', 'draft_id')
                    ])
                
                if cleanup_level in ['full', 'reset']:
                    # Clean processed data but keep original
                    tables_to_clean.extend([
                        ('scenes', 'draft_id')
                    ])
                
                if cleanup_level == 'full':
                    # Remove everything including chunks
                    tables_to_clean.append(('draft_chunks', 'draft_id'))
                
                # Clean up Apache AGE graph data if available
                try:
                    # Try to clean graph nodes and relationships
                    cursor.execute("""
                        SELECT ag_catalog.cypher('novel_pipeline_graph', $$
                            MATCH (n {draft_id: $draft_id})
                            DETACH DELETE n
                        $$, %s)
                    """, (f'{{"draft_id": "{draft_id}"}}',))
                    cleanup_stats['graph_cleaned'] = True
                except Exception as graph_error:
                    logger.warning(f"Could not clean graph data for draft {draft_id}: {graph_error}")
                    cleanup_stats['graph_cleaned'] = False
                
                # Clean up related data in reverse dependency order
                for table_name, id_column in tables_to_clean:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {id_column} = %s", (draft_id,))
                        count_before = cursor.fetchone()[0]
                        
                        cursor.execute(f"DELETE FROM {table_name} WHERE {id_column} = %s", (draft_id,))
                        deleted_count = cursor.rowcount
                        
                        cleanup_stats['tables_cleaned'][table_name] = {
                            'rows_before': count_before,
                            'rows_deleted': deleted_count
                        }
                        
                        logger.debug(f"Cleaned {deleted_count} rows from {table_name} for draft {draft_id}")
                        
                    except Exception as table_error:
                        logger.error(f"Failed to clean table {table_name} for draft {draft_id}: {table_error}")
                        cleanup_stats['tables_cleaned'][table_name] = {
                            'error': str(table_error)
                        }
                
                # Update draft status based on cleanup level
                if cleanup_level == 'reset':
                    # Reset to pending for reprocessing
                    cursor.execute("""
                        UPDATE drafts 
                        SET status = %s, 
                            processing_started_at = NULL,
                            processing_completed_at = NULL,
                            error_message = NULL,
                            metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
                        WHERE id = %s
                    """, (DraftStatus.PENDING.value, {'last_cleanup': datetime.now().isoformat(), 'cleanup_level': cleanup_level}, draft_id))
                elif cleanup_level == 'full':
                    # Reset everything
                    cursor.execute("""
                        UPDATE drafts 
                        SET status = %s,
                            processing_started_at = NULL,
                            processing_completed_at = NULL,
                            error_message = NULL,
                            metadata = %s::jsonb
                        WHERE id = %s
                    """, (DraftStatus.PENDING.value, {'last_cleanup': datetime.now().isoformat(), 'cleanup_level': cleanup_level}, draft_id))
                else:  # partial
                    # Keep current status but mark as cleaned
                    cursor.execute("""
                        UPDATE drafts 
                        SET metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
                        WHERE id = %s
                    """, ({'last_cleanup': datetime.now().isoformat(), 'cleanup_level': cleanup_level}, draft_id))
                
                # Check if draft exists and was updated
                cursor.execute("SELECT status FROM drafts WHERE id = %s", (draft_id,))
                draft_result = cursor.fetchone()
                
                if draft_result:
                    cleanup_stats['final_status'] = draft_result[0]
                    conn.commit()
                    cleanup_stats['success'] = True
                    
                    total_cleaned = sum(
                        table_data.get('rows_deleted', 0) 
                        for table_data in cleanup_stats['tables_cleaned'].values()
                        if isinstance(table_data, dict) and 'rows_deleted' in table_data
                    )
                    
                    logger.info(f"Successfully cleaned up {total_cleaned} rows for draft {draft_id} (level: {cleanup_level})")
                else:
                    cleanup_stats['error'] = f"Draft {draft_id} not found"
                    logger.warning(f"Draft {draft_id} not found during cleanup")
            
        except Exception as e:
            cleanup_stats['error'] = str(e)
            logger.error(f"Failed to cleanup processing for draft {draft_id}: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.db_pool.putconn(conn)
        
        return cleanup_stats
    
    def cleanup_orphaned_data(self) -> Dict[str, Any]:
        """
        Clean up orphaned data across all tables (maintenance operation).
        
        Returns:
            Cleanup statistics
        """
        cleanup_stats = {
            'orphaned_chunks': 0,
            'orphaned_scenes': 0,
            'orphaned_issues': 0,
            'orphaned_reports': 0,
            'orphaned_chapters': 0,
            'orphaned_manuscripts': 0,
            'success': False,
            'error': None
        }
        
        conn = None
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                # Clean orphaned draft_chunks
                cursor.execute("""
                    DELETE FROM draft_chunks 
                    WHERE draft_id NOT IN (SELECT id FROM drafts)
                """)
                cleanup_stats['orphaned_chunks'] = cursor.rowcount
                
                # Clean orphaned scenes
                cursor.execute("""
                    DELETE FROM scenes 
                    WHERE draft_id NOT IN (SELECT id FROM drafts)
                """)
                cleanup_stats['orphaned_scenes'] = cursor.rowcount
                
                # Clean orphaned plot_issues
                cursor.execute("""
                    DELETE FROM plot_issues 
                    WHERE draft_id NOT IN (SELECT id FROM drafts)
                """)
                cleanup_stats['orphaned_issues'] = cursor.rowcount
                
                # # Clean orphaned analysis_reports
                # cursor.execute("""
                #     DELETE FROM analysis_reports 
                #     WHERE draft_id NOT IN (SELECT id FROM drafts)
                # """)
                # cleanup_stats['orphaned_reports'] = cursor.rowcount
                # 
                # # Clean orphaned chapters
                # cursor.execute("""
                #     DELETE FROM chapters 
                #     WHERE draft_id NOT IN (SELECT id FROM drafts)
                # """)
                # cleanup_stats['orphaned_chapters'] = cursor.rowcount
                # 
                # # Clean orphaned final_manuscripts
                # cursor.execute("""
                #     DELETE FROM final_manuscripts 
                #     WHERE draft_id NOT IN (SELECT id FROM drafts)
                # """)
                # cleanup_stats['orphaned_manuscripts'] = cursor.rowcount
                
                # Clean orphaned graph data if available
                try:
                    cursor.execute("""
                        SELECT ag_catalog.cypher('novel_pipeline_graph', $$
                            MATCH (n)
                            WHERE n.draft_id IS NOT NULL 
                            AND NOT exists(
                                SELECT 1 FROM ag_catalog.ag_label_vertex('drafts') d 
                                WHERE d.properties->>'id' = n.draft_id
                            )
                            DETACH DELETE n
                        $$)
                    """)
                    cleanup_stats['graph_orphans_cleaned'] = True
                except Exception:
                    cleanup_stats['graph_orphans_cleaned'] = False
                
                conn.commit()
                cleanup_stats['success'] = True
                
                total_cleaned = sum([
                    cleanup_stats['orphaned_chunks'],
                    cleanup_stats['orphaned_scenes'],
                    cleanup_stats['orphaned_issues'],
                    cleanup_stats['orphaned_reports'],
                    cleanup_stats['orphaned_chapters'],
                    cleanup_stats['orphaned_manuscripts']
                ])
                
                logger.info(f"Cleaned up {total_cleaned} orphaned records across all tables")
                
        except Exception as e:
            cleanup_stats['error'] = str(e)
            logger.error(f"Failed to cleanup orphaned data: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self.db_pool.putconn(conn)
        
        return cleanup_stats