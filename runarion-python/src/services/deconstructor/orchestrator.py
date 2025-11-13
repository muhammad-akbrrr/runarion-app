"""
Main orchestrator for the novel deconstruction pipeline.
Coordinates all 7 stages of processing and manages database operations.
"""

import os
import traceback
import time
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager

from utils.logging_config import get_pipeline_logger
from utils.database_utils import ensure_utf8_json
from models.deconstructor.status import DraftStatus
from services.graph_database_service import GraphDatabaseService, GraphDatabaseNotAvailableError

from .stage_1_ingestion import PDFIngestionStage
from .stage_2_cleaning import TextCleaningStage
from .stage_3_sceneExtract import SceneDetectionStage
from .stage_4_analysis.analyzer_4a import SceneBySceneAnalysisStage
from .stage_4_analysis.analyzer_4b import ProgressiveGraphAnalysisStage
from .stage_4_analysis.analyzer_4c_reports import ComprehensiveReportingStage
from .stage_5_coherence import CoherenceCheckStage
from .stage_6_enhancement import EnhancementStage
from .stage_7_chaptering import ChapteringStage

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
        
        # Initialize graph service for cleanup operations
        try:
            self.graph_service = GraphDatabaseService(db_pool)
        except GraphDatabaseNotAvailableError:
            logger.warning("AGE not available, graph cleanup will be skipped")
            self.graph_service = None
        
        # Initialize all stages
        self.stages = {
            1: PDFIngestionStage(db_pool),
            2: TextCleaningStage(db_pool, generation_engine),
            3: SceneDetectionStage(db_pool, generation_engine),
            4: {
                'a': SceneBySceneAnalysisStage(db_pool, generation_engine),
                'b': ProgressiveGraphAnalysisStage(db_pool, generation_engine),
                'c': ComprehensiveReportingStage(db_pool, generation_engine)
            },
            5: CoherenceCheckStage(db_pool, generation_engine),
            6: EnhancementStage(db_pool, generation_engine),
            7: ChapteringStage(db_pool, generation_engine)
        }
        
    def run_pipeline(self, draft_id: str, file_name: str, 
                    chaptering_mode: str = 'flexible', target_chapter_length: int = 2500,
                    use_transactions: bool = True, user_id: int = None, 
                    workspace_id: str = None, test_mode: bool = False,
                    config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run the complete deconstruction pipeline.
        
        Args:
            draft_id: UUID of the draft to process
            file_name: Name of the uploaded file
            chaptering_mode: Chaptering approach ('flexible' or 'constrained')
            target_chapter_length: Target word count per chapter
            use_transactions: Whether to use database transactions for stages
            user_id: User ID executing the pipeline (derived from draft if not provided)
            workspace_id: Workspace ID (derived from draft if not provided)
            test_mode: Whether running in test mode
            config: Configuration parameters for validation and processing
            
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

        # Store chaptering parameters in draft metadata at the start
        self._store_chaptering_metadata_at_start(draft_id, chaptering_mode, target_chapter_length)

        # Update draft status to processing
        self._update_draft_status(draft_id, DraftStatus.PROCESSING.value)

        # Initialize cross-stage transaction
        # Get single connection for entire pipeline (all 7 stages)
        conn = None
        pipeline_conn = None

        try:
            conn = self.db_pool.getconn()
            conn.autocommit = False  # Enable transaction mode
            pipeline_conn = conn
            logger.debug(f"Initialized cross-stage transaction for draft {draft_id}")

            # Stage 1: Ingestion
            stage_start_time = datetime.now()
            logger.stage_start("ingestion", draft_id)
            stage_1_result = self.stages[1].run_with_connection(
                pipeline_conn, draft_id, file_path,
                user_id=user_id, workspace_id=workspace_id,
                test_mode=test_mode, config=config or {}
            )
            stage_duration = (datetime.now() - stage_start_time).total_seconds()
            logger.stage_complete("ingestion", draft_id, duration_seconds=stage_duration)
            pipeline_results['stages_completed'].append({
                'stage': 1,
                'name': 'ingestion',
                'completed_at': datetime.now().isoformat(),
                'result': stage_1_result
            })

            # Validate Stage 1 before continuing
            validation_result = self._validate_stage_result(1, 'ingestion', stage_1_result)
            if not validation_result.get('valid', False):
                error_msg = validation_result.get('error', 'Stage 1 validation failed')
                logger.error(f"Pipeline stopped at Stage 1: {error_msg}")

                # ROLLBACK cross-stage transaction
                if pipeline_conn:
                    pipeline_conn.rollback()
                    logger.warning(f"✗ Cross-stage transaction rolled back (Stage 1 validation failure)")

                self._update_draft_status(draft_id, DraftStatus.FAILED.value, error_message=error_msg)
                pipeline_results.update({
                    'success': False,
                    'error': error_msg,
                    'failed_at_stage': 1,
                    'failed_at': datetime.now().isoformat()
                })
                return pipeline_results

            self._update_draft_status(draft_id, DraftStatus.STAGE_1_COMPLETE.value)

            # Stage 2: Cleaning
            logger.info(f"Starting Stage 2: Cleaning for draft {draft_id}")
            stage_2_result = self.stages[2].run_with_connection(
                pipeline_conn, draft_id,
                user_id=user_id, workspace_id=workspace_id,
                test_mode=test_mode, config=config or {}
            )
            self._update_draft_status(draft_id, DraftStatus.STAGE_2_COMPLETE.value)
            pipeline_results['stages_completed'].append({
                'stage': 2,
                'name': 'cleaning',
                'completed_at': datetime.now().isoformat(),
                'result': stage_2_result
            })
            logger.info(f"Stage 2 completed for draft {draft_id}")

            # Stage 3: Scene Detection
            logger.info(f"Starting Stage 3: Scene Detection for draft {draft_id}")
            stage_3_result = self.stages[3].run_with_connection(
                pipeline_conn, draft_id,
                user_id=user_id, workspace_id=workspace_id,
                test_mode=test_mode, config=config or {}
            )
            pipeline_results['stages_completed'].append({
                'stage': 3,
                'name': 'scene_detection',
                'completed_at': datetime.now().isoformat(),
                'result': stage_3_result
            })

            # Validate Stage 3 before continuing (CRITICAL - prevents cascading failures)
            validation_result = self._validate_stage_result(3, 'scene_detection', stage_3_result)
            if not validation_result.get('valid', False):
                error_msg = validation_result.get('error', 'Stage 3 validation failed')
                logger.error(f"Pipeline stopped at Stage 3: {error_msg}")

                # ROLLBACK cross-stage transaction
                if pipeline_conn:
                    pipeline_conn.rollback()
                    logger.warning(f"✗ Cross-stage transaction rolled back (Stage 3 validation failure)")

                self._update_draft_status(draft_id, DraftStatus.FAILED.value, error_message=error_msg)
                pipeline_results.update({
                    'success': False,
                    'error': error_msg,
                    'failed_at_stage': 3,
                    'failed_at': datetime.now().isoformat()
                })
                return pipeline_results

            self._update_draft_status(draft_id, DraftStatus.STAGE_3_COMPLETE.value)
            logger.info(f"Stage 3 completed and validated for draft {draft_id}")

            # Stage 4: Deep Analysis (3 sub-stages)
            logger.info(f"Starting Stage 4: Deep Analysis for draft {draft_id}")
            #
            # Stage 4A: Scene-by-scene analysis (chaptering params from metadata)
            stage_4a_result = self.stages[4]['a'].run_with_connection(
                pipeline_conn, draft_id,
                user_id=user_id, workspace_id=workspace_id,
                test_mode=test_mode, config=config or {}
            )
            pipeline_results['stages_completed'].append({
                'stage': '4a',
                'name': 'scene_analysis',
                'completed_at': datetime.now().isoformat(),
                'result': stage_4a_result
            })

            # Stage 4B: Graph analysis (chaptering params from metadata)
            stage_4b_result = self.stages[4]['b'].run_with_connection(
                pipeline_conn, draft_id,
                user_id=user_id, workspace_id=workspace_id,
                test_mode=test_mode, config=config or {}
            )
            pipeline_results['stages_completed'].append({
                'stage': '4b',
                'name': 'graph_analysis',
                'completed_at': datetime.now().isoformat(),
                'result': stage_4b_result
            })
            #

            # Stage 4C: Comprehensive reporting
            stage_4c_result = self.stages[4]['c'].run_with_connection(
                pipeline_conn, draft_id,
                user_id=user_id, workspace_id=workspace_id,
                test_mode=test_mode, config=config or {}
            )
            self._update_draft_status(draft_id, DraftStatus.STAGE_4_COMPLETE.value)
            pipeline_results['stages_completed'].append({
                'stage': '4c',
                'name': 'comprehensive_reporting',
                'completed_at': datetime.now().isoformat(),
                'result': stage_4c_result
            })
            logger.info(f"Stage 4 Deep Analysis completed for draft {draft_id}")

            # Validate Stage 4 results
            # Stage 4A validation
            if stage_4a_result.get('failed_analyses', 0) > 0:
                error_msg = (
                    f"Stage 4A failed to analyze {stage_4a_result['failed_analyses']} scenes. "
                    f"Possible causes: truncated AI responses, parsing failures, or insufficient tokens. "
                    f"Successfully analyzed: {stage_4a_result.get('scenes_analyzed', 0)}"
                )
                logger.error(error_msg)
                pipeline_conn.rollback()
                self._update_draft_status(draft_id, DraftStatus.FAILED.value, error_message=error_msg)
                return {
                    'success': False,
                    'draft_id': draft_id,
                    'error': error_msg,
                    'stage_failed': '4a',
                    'processing_time_seconds': (datetime.now() - pipeline_start_time).total_seconds(),
                    'stages_completed': pipeline_results['stages_completed']
                }

            # Stage 4B validation (if AGE enabled)
            if stage_4b_result.get('entities_created', 0) == 0 and stage_4b_result.get('skipped') is False:
                # Only fail if graph analysis was attempted but produced no entities
                logger.warning(
                    f"Stage 4B created no graph entities. "
                    f"This may indicate AI extraction failure or empty character/location lists. "
                    f"Relationships created: {stage_4b_result.get('relationships_created', 0)}"
                )
                # Don't fail the pipeline - graph data is supplementary

            # Stage 5: Coherence Check
            logger.info(f"Starting Stage 5: Coherence Check for draft {draft_id}")
            stage_5_result = self.stages[5].run_with_connection(
                pipeline_conn, draft_id,
                user_id=user_id, workspace_id=workspace_id,
                test_mode=test_mode, config=config or {}
            )
            self._update_draft_status(draft_id, DraftStatus.STAGE_5_COMPLETE.value)
            pipeline_results['stages_completed'].append({
                'stage': 5,
                'name': 'coherence_check',
                'completed_at': datetime.now().isoformat(),
                'result': stage_5_result
            })
            logger.info(f"Stage 5 completed for draft {draft_id}")

            # Validate Stage 5 results
            issues_found = stage_5_result.get('issues_found', 0)
            if issues_found < 0:  # Negative value indicates failure
                error_msg = (
                    f"Stage 5 coherence check failed. "
                    f"Possible causes: truncated AI responses, parsing failures, or database errors."
                )
                logger.error(error_msg)
                pipeline_conn.rollback()
                self._update_draft_status(draft_id, DraftStatus.FAILED.value, error_message=error_msg)
                return {
                    'success': False,
                    'draft_id': draft_id,
                    'error': error_msg,
                    'stage_failed': '5',
                    'processing_time_seconds': (datetime.now() - pipeline_start_time).total_seconds(),
                    'stages_completed': pipeline_results['stages_completed']
                }

            # Stage 6: Enhancement
            logger.info(f"Starting Stage 6: Enhancement for draft {draft_id}")
            stage_6_result = self.stages[6].run_with_connection(
                pipeline_conn, draft_id,
                user_id=user_id, workspace_id=workspace_id,
                test_mode=test_mode, config=config or {}
            )
            self._update_draft_status(draft_id, DraftStatus.STAGE_6_COMPLETE.value)
            pipeline_results['stages_completed'].append({
                'stage': 6,
                'name': 'enhancement',
                'completed_at': datetime.now().isoformat(),
                'result': stage_6_result
            })
            logger.info(f"Stage 6 completed for draft {draft_id}")

            # Stage 7: Chaptering
            logger.info(f"Starting Stage 7: Chaptering for draft {draft_id}")
            stage_7_result = self.stages[7].run_with_connection(
                pipeline_conn, draft_id,
                user_id=user_id, workspace_id=workspace_id,
                test_mode=test_mode, config=config or {}
            )
            pipeline_results['stages_completed'].append({
                'stage': 7,
                'name': 'chaptering',
                'completed_at': datetime.now().isoformat(),
                'result': stage_7_result
            })

            # Validate Stage 7 (final stage - critical for output)
            validation_result = self._validate_stage_result(7, 'chaptering', stage_7_result)

            # DIAGNOSTIC: Print validation result to ensure code executes (appears in logs regardless of logging config)
            print(f"🔍 VALIDATION CHECK - Stage 7 result: {stage_7_result}")
            print(f"🔍 VALIDATION CHECK - Validation outcome: {validation_result}")

            if not validation_result.get('valid', False):
                error_msg = validation_result.get('error', 'Stage 7 validation failed')
                print(f"❌ VALIDATION FAILED: {error_msg}")
                logger.error(f"Pipeline stopped at Stage 7: {error_msg}")

                # ROLLBACK cross-stage transaction
                if pipeline_conn:
                    pipeline_conn.rollback()
                    logger.warning(f"✗ Cross-stage transaction rolled back (Stage 7 validation failure)")

                self._update_draft_status(draft_id, DraftStatus.FAILED.value, error_message=error_msg)
                pipeline_results.update({
                    'success': False,
                    'error': error_msg,
                    'failed_at_stage': 7,
                    'failed_at': datetime.now().isoformat()
                })
                return pipeline_results

            print(f"✅ VALIDATION PASSED - Stage 7 validated successfully")
            logger.info(f"Stage 7 completed and validated for draft {draft_id}")

            # Validate pipeline success by checking all stage results
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            # Determine pipeline success based on stage validation
            pipeline_success = self._validate_pipeline_success(pipeline_results)

            # COMMIT or ROLLBACK based on validation
            if pipeline_success:
                if pipeline_conn:
                    pipeline_conn.commit()
                    logger.info(f"✓ Cross-stage transaction committed for draft {draft_id}")

                # Monitor finish_reason across all stages to detect token limit issues
                truncation_warnings = []
                for stage_info in pipeline_results.get('stages_completed', []):
                    stage_name = stage_info.get('name', 'unknown')
                    stage_number = stage_info.get('stage', 'unknown')
                    # Check if any stage result indicates truncation happened
                    # (This is informational - we already recovered via retries, but log for monitoring)
                    if 'truncation_detected' in str(stage_info.get('result', {})):
                        truncation_warnings.append(f"Stage {stage_number} ({stage_name})")

                if truncation_warnings:
                    logger.warning(
                        f"⚠️ Pipeline completed successfully, but {len(truncation_warnings)} stage(s) "
                        f"hit token limits and required retry with increased tokens: {', '.join(truncation_warnings)}. "
                        f"Consider increasing base max_output_tokens for these stages to reduce API overhead."
                    )

                self._update_draft_status(
                    draft_id,
                    DraftStatus.COMPLETED.value,
                    metadata={'processing_time_seconds': processing_time}
                )
                logger.pipeline_complete(draft_id, duration_seconds=processing_time)
            else:
                # Pipeline failed validation - rollback everything
                if pipeline_conn:
                    pipeline_conn.rollback()
                    logger.warning(f"✗ Cross-stage transaction rolled back (pipeline validation failure)")

                # Collect failed stage information
                failed_stages = [
                    s for s in pipeline_results['stages_completed']
                    if not s.get('result', {}).get('success', False)
                ]
                error_summary = f"Pipeline validation failed: {len(failed_stages)} stage(s) reported failures"

                self._update_draft_status(
                    draft_id,
                    DraftStatus.FAILED.value,
                    error_message=error_summary
                )
                logger.pipeline_failed(draft_id, error=error_summary)

            pipeline_results.update({
                'success': pipeline_success,  # Now validated against all stages
                'completed_at': end_time.isoformat(),
                'processing_time_seconds': processing_time
            })

            # Add failed stages info if validation failed
            if not pipeline_success:
                failed_stages = [
                    s for s in pipeline_results['stages_completed']
                    if not s.get('result', {}).get('success', False)
                ]
                pipeline_results['failed_stages'] = failed_stages

            return pipeline_results

        except Exception as e:
            error_message = str(e)
            error_trace = traceback.format_exc()

            logger.pipeline_failed(draft_id, error=error_message)
            logger.debug("Full traceback", traceback=error_trace)

            # ROLLBACK cross-stage transaction on exception
            if pipeline_conn:
                pipeline_conn.rollback()
                logger.error(f"✗ Cross-stage transaction rolled back due to exception")

            # Update draft status to failed
            self._update_draft_status(draft_id, DraftStatus.FAILED.value, error_message=error_message)

            pipeline_results.update({
                'success': False,
                'error': error_message,
                'failed_at': datetime.now().isoformat()
            })

            return pipeline_results

        finally:
            # Return connection to pool
            if conn:
                self.db_pool.putconn(conn)

            # Clear logging context
            logger.clear_context()

    def _execute_stage_with_retry(self, stage, stage_number: str, draft_id: str, *args,
                                 user_id: int = None, workspace_id: str = None, 
                                 test_mode: bool = False, config: Dict[str, Any] = None,
                                 max_retries: int = 10) -> Dict[str, Any]:
        """
        Execute a stage with retry mechanism.
        
        Args:
            stage: Stage instance to execute
            stage_number: Stage identifier (for logging)
            draft_id: UUID of the draft
            user_id: User ID executing the pipeline
            workspace_id: Workspace ID
            test_mode: Whether running in test mode
            config: Configuration parameters for validation and processing
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
                
                # Execute the stage with dynamic context parameters
                result = stage.run(
                    draft_id, user_id=user_id, workspace_id=workspace_id,
                    test_mode=test_mode, config=config, *args
                )
                
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
    
    # ============================================================================
    # COMMENTED OUT: PER-STAGE TRANSACTION ARCHITECTURE (Phase 1 Cleanup)
    # This context manager created separate transactions for each stage.
    # Problem: If Stage 7 failed, Stages 1-6 had already committed (orphaned data).
    # Replaced with: Single cross-stage transaction in run_pipeline()
    # Date: 2025-11-12
    # ============================================================================
    #
    # @contextmanager
    # def _database_transaction(self):
    #     """
    #     Context manager for database transactions with automatic rollback on error.
    #     """
    #     conn = None
    #     try:
    #         conn = self.db_pool.getconn()
    #         conn.autocommit = False  # Ensure we're in transaction mode
    #         yield conn
    #         conn.commit()
    #     except Exception as e:
    #         if conn:
    #             conn.rollback()
    #             logger.error(f"Database transaction rolled back due to error: {e}")
    #         raise
    #     finally:
    #         if conn:
    #             self.db_pool.putconn(conn)
    
    # ============================================================================
    # COMMENTED OUT: PER-STAGE TRANSACTIONAL EXECUTION (Phase 1 Cleanup)
    # This method created a NEW transaction for EACH stage independently.
    # Problem: Each stage committed separately, causing orphaned data on late failures.
    # Replaced with: Direct stage.run_with_connection(pipeline_conn, ...) calls
    # Date: 2025-11-12
    # ============================================================================
    #
    # def _execute_stage_with_transaction(self, stage, stage_number: str, draft_id: str, *args,
    #                                    user_id: int = None, workspace_id: str = None,
    #                                    test_mode: bool = False, config: Dict[str, Any] = None,
    #                                    max_retries: int = 10) -> Dict[str, Any]:
    #     """
    #     Execute a stage within a database transaction with retry mechanism.
    #
    #     Args:
    #         stage: Stage instance to execute
    #         stage_number: Stage identifier (for logging)
    #         draft_id: UUID of the draft
    #         user_id: User ID executing the pipeline
    #         workspace_id: Workspace ID
    #         test_mode: Whether running in test mode
    #         config: Configuration parameters for validation and processing
    #         *args: Arguments to pass to the stage
    #         max_retries: Maximum number of retry attempts
    #
    #     Returns:
    #         Stage execution result
    #
    #     Raises:
    #         Exception: If all retry attempts fail
    #     """
    #     last_exception = None
    #
    #     for attempt in range(max_retries + 1):  # +1 for initial attempt
    #         try:
    #             logger.info(f"Executing stage {stage_number} for draft {draft_id} (attempt {attempt + 1}/{max_retries + 1})")
    #
    #             # Execute the stage within a transaction
    #             with self._database_transaction() as conn:
    #                 # All stages inherit from BasePipelineStage and support transactional interface
    #                 result = stage.run_with_connection(
    #                     conn, draft_id, user_id=user_id, workspace_id=workspace_id,
    #                     test_mode=test_mode, config=config, *args
    #                 )
    #
    #             logger.info(f"Stage {stage_number} completed successfully for draft {draft_id}")
    #             return result
    #
    #         except Exception as e:
    #             last_exception = e
    #             logger.warning(f"Stage {stage_number} failed for draft {draft_id} (attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
    #
    #             if attempt < max_retries:
    #                 # Calculate exponential backoff delay (1s, 2s, 4s, 8s, etc., max 60s)
    #                 delay = min(2 ** attempt, 60)
    #                 logger.info(f"Retrying stage {stage_number} in {delay} seconds...")
    #                 time.sleep(delay)
    #             else:
    #                 logger.error(f"Stage {stage_number} failed permanently for draft {draft_id} after {max_retries + 1} attempts")
    #                 break
    #
    #     # All retries failed, raise the last exception
    #     raise last_exception
    
    def _store_chaptering_metadata_at_start(self, draft_id: str, chaptering_mode: str, target_chapter_length: int) -> None:
        """
        Store chaptering parameters in draft metadata at pipeline start.
        
        Args:
            draft_id: UUID of the draft
            chaptering_mode: Chaptering approach
            target_chapter_length: Target word count per chapter
        """
        try:
            conn = self.db_pool.getconn()
            
            with conn.cursor() as cursor:
                # Get current metadata
                cursor.execute("SELECT metadata FROM drafts WHERE id = %s", (draft_id,))
                result = cursor.fetchone()
                
                current_metadata = {}
                if result and result[0]:
                    # Handle both cases: JSON string or already-parsed dict
                    if isinstance(result[0], dict):
                        current_metadata = result[0]
                    elif isinstance(result[0], str):
                        import json
                        try:
                            current_metadata = json.loads(result[0])
                        except json.JSONDecodeError:
                            current_metadata = {}
                    else:
                        current_metadata = {}
                
                # Update with chaptering parameters
                current_metadata.update({
                    'chaptering_mode': chaptering_mode,
                    'target_chapter_length': target_chapter_length,
                    'chaptering_set_at_pipeline_start': True
                })
                
                # Store updated metadata
                from utils.database_utils import ensure_utf8_json
                metadata_json = ensure_utf8_json(current_metadata)
                cursor.execute(
                    "UPDATE drafts SET metadata = %s WHERE id = %s",
                    (metadata_json, draft_id)
                )
                
                conn.commit()
                logger.debug(f"Stored chaptering metadata at pipeline start for draft {draft_id}: mode={chaptering_mode}, length={target_chapter_length}")
                
        except Exception as e:
            logger.error(f"Failed to store chaptering metadata for draft {draft_id}: {e}")
            raise
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def _validate_stage_result(self, stage_num: Any, stage_name: str,
                              stage_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate individual stage result and outputs.

        Args:
            stage_num: Stage number (can be int or string like '4a')
            stage_name: Name of the stage
            stage_result: Result dictionary from stage execution

        Returns:
            Dictionary with 'valid' boolean and optional 'error' message
        """
        # Check basic success flag
        if not stage_result.get('success', False):
            error = stage_result.get('error', 'Unknown error')
            logger.error(f"Stage {stage_num} ({stage_name}) reported failure: {error}")
            return {
                'valid': False,
                'error': error,
                'validation_type': 'success_flag'
            }

        # Validate stage-specific outputs for critical stages
        if stage_num == 1:  # Ingestion
            chunks_created = stage_result.get('chunks_created', 0)
            if chunks_created == 0:
                error = "Stage 1 created 0 chunks - invalid input file"
                logger.error(error)
                return {
                    'valid': False,
                    'error': error,
                    'validation_type': 'output_validation'
                }
            logger.info(f"Stage 1 validation passed: {chunks_created} chunks created")

        elif stage_num == 3:  # Scene Detection (CRITICAL)
            scenes_extracted = stage_result.get('scenes_extracted', 0)
            if scenes_extracted == 0:
                error = "Stage 3 extracted 0 scenes - LLM parsing failed"
                logger.error(error)
                return {
                    'valid': False,
                    'error': error,
                    'validation_type': 'output_validation'
                }

            # Check hydration quality
            hydration_stats = stage_result.get('hydration_stats', {})
            if hydration_stats:
                success_rate = hydration_stats.get('success_rate', 1.0)
                failed_count = hydration_stats.get('failed', 0)
                attempted_count = hydration_stats.get('attempted', 0)

                if success_rate < 0.75:  # Less than 75% hydration success
                    error = (
                        f"Stage 3 hydration quality too low: {success_rate*100:.1f}% "
                        f"({failed_count}/{attempted_count} scenes failed hydration). "
                        "Cannot proceed with incomplete scene content."
                    )
                    logger.error(error)
                    return {
                        'valid': False,
                        'error': error,
                        'validation_type': 'hydration_quality',
                        'hydration_stats': hydration_stats
                    }

                if success_rate < 0.9:  # 75-90% - warning but continue
                    logger.warning(
                        f"Stage 3 hydration quality degraded: {success_rate*100:.1f}% "
                        f"({failed_count}/{attempted_count} scenes failed). "
                        "Continuing but quality may be affected."
                    )

            logger.info(f"Stage 3 validation passed: {scenes_extracted} scenes extracted")

        elif stage_num == 6:  # Enhancement
            # Check for validation failures in enhancement
            failed_validations = stage_result.get('failed_validations', 0)
            scenes_enhanced = stage_result.get('scenes_enhanced', 0)
            total_scenes = failed_validations + scenes_enhanced

            if total_scenes > 0:
                failure_rate = failed_validations / total_scenes

                # Hard failure threshold: >30% failures
                if failure_rate > 0.3:
                    error = (
                        f"Stage 6 validation failure rate too high: {failure_rate*100:.1f}% "
                        f"({failed_validations}/{total_scenes} scenes failed validation). "
                        "Enhancement quality compromised."
                    )
                    logger.error(error)
                    return {
                        'valid': False,
                        'error': error,
                        'validation_type': 'enhancement_quality',
                        'failure_rate': failure_rate
                    }

                # Warning threshold: 10-30% failures
                elif failure_rate > 0.1:
                    logger.warning(
                        f"Stage 6 validation failure rate elevated: {failure_rate*100:.1f}% "
                        f"({failed_validations}/{total_scenes} scenes). Quality may be affected."
                    )

            logger.info(f"Stage 6 validation passed: {scenes_enhanced} scenes enhanced successfully")

        elif stage_num == 7:  # Chaptering
            chapters_created = stage_result.get('chapters_created', 0)
            chapters_stored = stage_result.get('chapters_stored', 0)

            # Check if chapters were generated by LLM
            if chapters_created == 0:
                error = "Stage 7 created 0 chapters - LLM chaptering failed"
                logger.error(error)
                return {
                    'valid': False,
                    'error': error,
                    'validation_type': 'output_validation'
                }

            # CRITICAL: Check if chapters were actually stored in database
            if chapters_stored == 0:
                error = f"Stage 7 generated {chapters_created} chapters but stored 0 in database - storage failed"
                logger.error(error)
                return {
                    'valid': False,
                    'error': error,
                    'validation_type': 'database_validation'
                }

            logger.info(f"Stage 7 validation passed: {chapters_created} chapters created, {chapters_stored} stored in DB")

        return {'valid': True}

    def _validate_pipeline_success(self, pipeline_results: Dict[str, Any]) -> bool:
        """
        Validate that all stages completed successfully.

        Args:
            pipeline_results: Dictionary containing stages_completed list

        Returns:
            True if all stages succeeded, False otherwise
        """
        stages_completed = pipeline_results.get('stages_completed', [])

        if not stages_completed:
            logger.error("No stages completed")
            return False

        # Check each stage's success flag
        failed_stages = []
        for stage_info in stages_completed:
            stage_num = stage_info.get('stage', 'unknown')
            stage_name = stage_info.get('name', 'unknown')
            stage_result = stage_info.get('result', {})

            # Check if this stage reported success
            if not stage_result.get('success', False):
                failed_stages.append({
                    'stage': stage_num,
                    'name': stage_name,
                    'error': stage_result.get('error', 'Unknown error')
                })

        # Log all failures
        if failed_stages:
            logger.error(f"Pipeline validation failed: {len(failed_stages)} stage(s) reported failures")
            for failure in failed_stages:
                logger.error(f"  Stage {failure['stage']} ({failure['name']}): {failure['error']}")
            return False

        logger.info("Pipeline validation passed: all stages reported success")
        return True

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
                    # Get current metadata and merge with new metadata
                    cursor.execute("SELECT metadata FROM drafts WHERE id = %s", (draft_id,))
                    result = cursor.fetchone()
                    current_metadata = {}
                    if result and result[0]:
                        # Handle both cases: JSON string or already-parsed dict
                        if isinstance(result[0], dict):
                            current_metadata = result[0]
                        elif isinstance(result[0], str):
                            import json
                            try:
                                current_metadata = json.loads(result[0])
                            except json.JSONDecodeError:
                                current_metadata = {}
                        else:
                            current_metadata = {}
                    
                    # Merge with new metadata
                    if metadata:
                        current_metadata.update(metadata)
                    
                    cursor.execute("""
                        UPDATE drafts 
                        SET status = %s, 
                            processing_completed_at = NOW(),
                            error_message = %s,
                            metadata = %s
                        WHERE id = %s
                    """, (status, error_message, ensure_utf8_json(current_metadata), draft_id))
                
                elif status == DraftStatus.FAILED.value:
                    cursor.execute("""
                        UPDATE drafts 
                        SET status = %s, 
                            error_message = %s,
                            processing_completed_at = NOW()
                        WHERE id = %s
                    """, (status, error_message, draft_id))
                
                else:
                    # Get current metadata and merge with new metadata
                    cursor.execute("SELECT metadata FROM drafts WHERE id = %s", (draft_id,))
                    result = cursor.fetchone()
                    current_metadata = {}
                    if result and result[0]:
                        # Handle both cases: JSON string or already-parsed dict
                        if isinstance(result[0], dict):
                            current_metadata = result[0]
                        elif isinstance(result[0], str):
                            import json
                            try:
                                current_metadata = json.loads(result[0])
                            except json.JSONDecodeError:
                                current_metadata = {}
                        else:
                            current_metadata = {}
                    
                    # Merge with new metadata
                    if metadata:
                        current_metadata.update(metadata)
                    
                    cursor.execute("""
                        UPDATE drafts 
                        SET status = %s,
                            metadata = %s
                        WHERE id = %s
                    """, (status, ensure_utf8_json(current_metadata), draft_id))
                
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
                
                # Clean up Apache AGE graph data using GraphDatabaseService
                try:
                    if self.graph_service:
                        deleted_count = self.graph_service.cleanup_draft_data(draft_id)
                        cleanup_stats['graph_cleaned'] = True
                        cleanup_stats['graph_items_deleted'] = deleted_count
                        logger.debug(f"Cleaned {deleted_count} graph items for draft {draft_id}")
                    else:
                        cleanup_stats['graph_cleaned'] = 'skipped'
                        logger.debug(f"Graph service not available, skipping graph cleanup for draft {draft_id}")
                except GraphDatabaseNotAvailableError as e:
                    logger.warning(f"AGE not available for graph cleanup: {e}")
                    cleanup_stats['graph_cleaned'] = 'age_unavailable'
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
                    # Get current metadata and merge with cleanup info
                    cursor.execute("SELECT metadata FROM drafts WHERE id = %s", (draft_id,))
                    result = cursor.fetchone()
                    current_metadata = {}
                    if result and result[0]:
                        # Handle both cases: JSON string or already-parsed dict
                        if isinstance(result[0], dict):
                            current_metadata = result[0]
                        elif isinstance(result[0], str):
                            import json
                            try:
                                current_metadata = json.loads(result[0])
                            except json.JSONDecodeError:
                                current_metadata = {}
                        else:
                            current_metadata = {}
                    
                    current_metadata.update({'last_cleanup': datetime.now().isoformat(), 'cleanup_level': cleanup_level})
                    
                    # Reset to pending for reprocessing
                    cursor.execute("""
                        UPDATE drafts 
                        SET status = %s, 
                            processing_started_at = NULL,
                            processing_completed_at = NULL,
                            error_message = NULL,
                            metadata = %s
                        WHERE id = %s
                    """, (DraftStatus.PENDING.value, ensure_utf8_json(current_metadata), draft_id))
                elif cleanup_level == 'full':
                    # Reset everything
                    cursor.execute("""
                        UPDATE drafts 
                        SET status = %s,
                            processing_started_at = NULL,
                            processing_completed_at = NULL,
                            error_message = NULL,
                            metadata = %s
                        WHERE id = %s
                    """, (DraftStatus.PENDING.value, ensure_utf8_json({'last_cleanup': datetime.now().isoformat(), 'cleanup_level': cleanup_level}), draft_id))
                else:  # partial
                    # Get current metadata and merge with cleanup info
                    cursor.execute("SELECT metadata FROM drafts WHERE id = %s", (draft_id,))
                    result = cursor.fetchone()
                    current_metadata = {}
                    if result and result[0]:
                        # Handle both cases: JSON string or already-parsed dict
                        if isinstance(result[0], dict):
                            current_metadata = result[0]
                        elif isinstance(result[0], str):
                            import json
                            try:
                                current_metadata = json.loads(result[0])
                            except json.JSONDecodeError:
                                current_metadata = {}
                        else:
                            current_metadata = {}
                    
                    current_metadata.update({'last_cleanup': datetime.now().isoformat(), 'cleanup_level': cleanup_level})
                    
                    # Keep current status but mark as cleaned
                    cursor.execute("""
                        UPDATE drafts 
                        SET metadata = %s
                        WHERE id = %s
                    """, (ensure_utf8_json(current_metadata), draft_id))
                
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
                
                # Clean orphaned graph data using GraphDatabaseService
                try:
                    if self.graph_service:
                        orphaned_count = self.graph_service.cleanup_orphaned_graph_data()
                        cleanup_stats['graph_orphans_cleaned'] = True
                        cleanup_stats['graph_orphans_deleted'] = orphaned_count
                        logger.debug(f"Cleaned {orphaned_count} orphaned graph items")
                    else:
                        cleanup_stats['graph_orphans_cleaned'] = 'skipped'
                        logger.debug("Graph service not available, skipping orphaned graph cleanup")
                except GraphDatabaseNotAvailableError as e:
                    logger.warning(f"AGE not available for orphaned graph cleanup: {e}")
                    cleanup_stats['graph_orphans_cleaned'] = 'age_unavailable'
                except Exception as e:
                    logger.warning(f"Could not clean orphaned graph data: {e}")
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
