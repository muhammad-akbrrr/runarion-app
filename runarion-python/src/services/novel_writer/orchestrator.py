"""
Main orchestrator for the novel writer pipeline.
Coordinates all 5 stages of processing and manages database transactions.
Follows the same cross-stage transaction pattern as the DeconstructorOrchestrator.
"""

import traceback
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from utils.database_utils import ensure_utf8_json
from models.deconstructor.status import DraftStatus
from services.graph_database_service import GraphDatabaseService, GraphDatabaseNotAvailableError

from .base_stage import PipelineStageContext, PipelineStageResult
from .entity_profiler import EntityProfilingStage
from .scene_generator import ProseGenerationStage
from .stage_3_quality import QualityAssessmentStage
from .stage_4_improvement import SceneImprovementStage
from .stage_5_assembly import ManuscriptAssemblyStage

logger = logging.getLogger(__name__)


class NovelWriterOrchestrator:
    """
    Orchestrates the complete novel writer pipeline.
    Manages stage execution, database transactions, and error handling.

    Uses a single shared PipelineStageContext so that in-memory data
    (story_context, quality_assessments) flows between stages without
    requiring database serialization.
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

        # Initialize graph service (graceful if AGE unavailable)
        try:
            self.graph_service = GraphDatabaseService(db_pool)
        except GraphDatabaseNotAvailableError:
            logger.warning("AGE not available, graph data loading will be skipped")
            self.graph_service = None

        # Initialize all stages
        self.stage_1 = EntityProfilingStage(db_pool, generation_engine, self.graph_service)
        self.stage_2 = ProseGenerationStage(db_pool, generation_engine)
        self.stage_3 = QualityAssessmentStage(db_pool, generation_engine)
        self.stage_4 = SceneImprovementStage(db_pool, generation_engine)
        self.stage_5 = ManuscriptAssemblyStage(db_pool)

    def run_pipeline(self, draft_id: str, user_id: int = None,
                     workspace_id: str = None,
                     target_chapter_length: int = 2500,
                     author_style_name: str = None,
                     quality_threshold: float = 6.0,
                     max_improvement_passes: int = 2,
                     config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run the complete novel writer pipeline.

        Uses a single shared PipelineStageContext across all 5 stages so that
        in-memory data (StoryContext, quality assessments) persists between stages.

        Args:
            draft_id: UUID of the draft to process
            user_id: User ID executing the pipeline
            workspace_id: Workspace ID
            target_chapter_length: Target word count per chapter
            author_style_name: Optional specific author style to use
            quality_threshold: Minimum quality score (chapters below this get improved)
            max_improvement_passes: Maximum improvement iterations per chapter
            config: Additional configuration parameters

        Returns:
            Pipeline execution results
        """
        start_time = datetime.now()
        pipeline_config = {
            'target_chapter_length': target_chapter_length,
            'author_style_name': author_style_name,
            'quality_threshold': quality_threshold,
            'max_improvement_passes': max_improvement_passes,
            **(config or {}),
        }

        pipeline_results = {
            'draft_id': draft_id,
            'started_at': start_time.isoformat(),
            'stages_completed': [],
            'success': False,
            'error': None,
        }

        logger.info(
            f"Starting novel writer pipeline for draft {draft_id} "
            f"(target_chapter_length={target_chapter_length}, "
            f"quality_threshold={quality_threshold})"
        )

        # Update draft status to novel_writing
        self._update_draft_status(draft_id, DraftStatus.NOVEL_WRITING.value)

        # Initialize cross-stage transaction
        conn = None
        pipeline_conn = None

        try:
            conn = self.db_pool.getconn()
            conn.autocommit = False
            pipeline_conn = conn
            logger.debug(f"Initialized cross-stage transaction for draft {draft_id}")

            # Create a SINGLE shared context for the entire pipeline.
            # Stages store in-memory data (story_context, quality_assessments)
            # in context.metadata, and downstream stages read from the same object.
            shared_context = PipelineStageContext(
                draft_id=draft_id,
                user_id=user_id,
                workspace_id=workspace_id,
                config=pipeline_config,
                connection=pipeline_conn,
            )

            # ── Stage 1: Entity Profiling ──
            stage_1_result = self._run_stage(
                self.stage_1, shared_context, 1, 'entity_profiling',
                pipeline_results, pipeline_conn, draft_id, critical=True,
            )
            if stage_1_result is None:
                return pipeline_results
            self._update_draft_status(draft_id, DraftStatus.NW_STAGE_1_COMPLETE.value)

            # ── Stage 2: Prose Generation ──
            stage_2_result = self._run_stage(
                self.stage_2, shared_context, 2, 'prose_generation',
                pipeline_results, pipeline_conn, draft_id, critical=True,
            )
            if stage_2_result is None:
                return pipeline_results
            self._update_draft_status(draft_id, DraftStatus.NW_STAGE_2_COMPLETE.value)

            # ── Stage 3: Quality Assessment ──
            # Non-critical: assessment failure doesn't stop the pipeline
            self._run_stage(
                self.stage_3, shared_context, 3, 'quality_assessment',
                pipeline_results, pipeline_conn, draft_id, critical=False,
            )
            self._update_draft_status(draft_id, DraftStatus.NW_STAGE_3_COMPLETE.value)

            # ── Stage 4: Scene Improvement ──
            # Non-critical: improvement is best-effort
            self._run_stage(
                self.stage_4, shared_context, 4, 'scene_improvement',
                pipeline_results, pipeline_conn, draft_id, critical=False,
            )
            self._update_draft_status(draft_id, DraftStatus.NW_STAGE_4_COMPLETE.value)

            # ── Stage 5: Manuscript Assembly ──
            stage_5_result = self._run_stage(
                self.stage_5, shared_context, 5, 'manuscript_assembly',
                pipeline_results, pipeline_conn, draft_id, critical=True,
            )
            if stage_5_result is None:
                return pipeline_results

            # ── Commit and finalize ──
            pipeline_conn.commit()
            logger.info(f"Cross-stage transaction committed for draft {draft_id}")

            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            self._update_draft_status(
                draft_id, DraftStatus.NW_COMPLETED.value,
                metadata={'processing_time_seconds': processing_time}
            )

            pipeline_results.update({
                'success': True,
                'completed_at': end_time.isoformat(),
                'processing_time_seconds': processing_time,
            })

            logger.info(
                f"Novel writer pipeline completed for draft {draft_id} "
                f"in {processing_time:.1f}s"
            )

            return pipeline_results

        except Exception as e:
            error_message = str(e)
            error_trace = traceback.format_exc()

            logger.error(f"Novel writer pipeline failed for draft {draft_id}: {error_message}")
            logger.debug(f"Full traceback: {error_trace}")

            if pipeline_conn:
                pipeline_conn.rollback()
                logger.warning("Cross-stage transaction rolled back due to exception")

            self._update_draft_status(
                draft_id, DraftStatus.NW_FAILED.value, error_message=error_message
            )

            pipeline_results.update({
                'success': False,
                'error': error_message,
                'failed_at': datetime.now().isoformat(),
            })

            return pipeline_results

        finally:
            if conn:
                self.db_pool.putconn(conn)

    def _run_stage(self, stage, context: PipelineStageContext,
                   stage_num: int, stage_name: str,
                   pipeline_results: Dict[str, Any],
                   pipeline_conn, draft_id: str,
                   critical: bool = True) -> Optional[PipelineStageResult]:
        """
        Execute a single stage using the shared context.

        Args:
            stage: The stage instance to execute
            context: Shared PipelineStageContext
            stage_num: Stage number for logging
            stage_name: Stage name for logging
            pipeline_results: Accumulator for pipeline results
            pipeline_conn: Pipeline DB connection (for rollback on failure)
            draft_id: UUID of the draft
            critical: If True, pipeline stops on failure

        Returns:
            PipelineStageResult on success, None if the stage failed critically
            (and pipeline_results has been updated with error info).
        """
        logger.info(f"Starting Stage {stage_num}: {stage_name} for draft {draft_id}")

        try:
            result = stage._execute_stage(context)
        except Exception as e:
            logger.error(f"Stage {stage_num} ({stage_name}) raised exception: {e}")
            result = PipelineStageResult.error_result(
                stage_name, error=str(e)
            )

        result_dict = result.to_dict()
        pipeline_results['stages_completed'].append({
            'stage': stage_num,
            'name': stage_name,
            'completed_at': datetime.now().isoformat(),
            'result': result_dict,
        })

        if result.success:
            logger.info(f"Stage {stage_num} ({stage_name}) completed for draft {draft_id}")
            return result
        else:
            error_msg = result_dict.get('error', f'Stage {stage_num} failed')
            if critical:
                logger.error(f"Pipeline stopped at Stage {stage_num}: {error_msg}")
                pipeline_conn.rollback()
                self._update_draft_status(
                    draft_id, DraftStatus.NW_FAILED.value, error_message=error_msg
                )
                pipeline_results.update({
                    'success': False,
                    'error': error_msg,
                    'failed_at_stage': stage_num,
                })
                return None
            else:
                logger.warning(
                    f"Stage {stage_num} ({stage_name}) failed but is non-critical: {error_msg}"
                )
                return result

    def _update_draft_status(self, draft_id: str, status: str,
                             error_message: Optional[str] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Update draft status using a separate connection (persists even on rollback).

        Args:
            draft_id: UUID of the draft
            status: New status value (validated against DraftStatus)
            error_message: Optional error message
            metadata: Optional metadata to merge
        """
        if not DraftStatus.is_valid(status):
            raise ValueError(
                f"Invalid status '{status}'. "
                f"Valid statuses: {DraftStatus.get_valid_statuses()}"
            )

        conn = None
        try:
            conn = self.db_pool.getconn()

            with conn.cursor() as cursor:
                if status in (DraftStatus.NW_COMPLETED.value, DraftStatus.NW_FAILED.value):
                    # Terminal statuses: set completion time
                    cursor.execute("SELECT metadata FROM drafts WHERE id = %s", (draft_id,))
                    result = cursor.fetchone()
                    current_metadata = self._parse_metadata(result)

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
                else:
                    # Intermediate statuses
                    cursor.execute("SELECT metadata FROM drafts WHERE id = %s", (draft_id,))
                    result = cursor.fetchone()
                    current_metadata = self._parse_metadata(result)

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
            logger.error(f"Failed to update draft status for {draft_id}: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def _parse_metadata(self, result) -> Dict[str, Any]:
        """Parse metadata from a DB query result row."""
        if not result or not result[0]:
            return {}
        if isinstance(result[0], dict):
            return result[0]
        if isinstance(result[0], str):
            import json
            try:
                return json.loads(result[0])
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def get_pipeline_status(self, draft_id: str) -> Dict[str, Any]:
        """
        Get the current pipeline status for a draft.

        Args:
            draft_id: UUID of the draft

        Returns:
            Status information dictionary
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
                    'metadata': metadata or {},
                }

                # Add novel writer progress details
                progress = self._get_nw_progress(cursor, draft_id, status, metadata)
                status_info['progress'] = progress

                return status_info

        except Exception as e:
            logger.error(f"Failed to get pipeline status: {e}")
            return {'error': str(e)}
        finally:
            if conn:
                self.db_pool.putconn(conn)

    def _get_nw_progress(self, cursor, draft_id: str, status: str,
                         metadata: Any) -> Dict[str, Any]:
        """Get novel writer-specific progress details."""
        from models.novel_writer.status import NovelWriterStatus

        progress = {
            'stage': 'unknown',
            'percentage': 0,
        }

        status_mapping = {
            NovelWriterStatus.NOVEL_WRITING: {'stage': 'starting', 'percentage': 5},
            NovelWriterStatus.STAGE_1_COMPLETE: {'stage': 'entity_profiling', 'percentage': 15},
            NovelWriterStatus.STAGE_2_COMPLETE: {'stage': 'prose_generation', 'percentage': 50},
            NovelWriterStatus.STAGE_3_COMPLETE: {'stage': 'quality_assessment', 'percentage': 65},
            NovelWriterStatus.STAGE_4_COMPLETE: {'stage': 'scene_improvement', 'percentage': 85},
            NovelWriterStatus.COMPLETED: {'stage': 'completed', 'percentage': 100},
            NovelWriterStatus.FAILED: {'stage': 'failed', 'percentage': 0},
        }

        if status in status_mapping:
            progress.update(status_mapping[status])

        # Extract novel writer progress from metadata
        if metadata and isinstance(metadata, dict):
            nw_meta = {
                k: v for k, v in metadata.items()
                if k.startswith('nw_')
            }
            if nw_meta:
                progress['details'] = nw_meta

        # Get chapter and manuscript counts
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM chapters WHERE draft_id = %s",
                (draft_id,)
            )
            progress['chapters_stored'] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM final_manuscripts WHERE draft_id = %s",
                (draft_id,)
            )
            progress['manuscript_stored'] = cursor.fetchone()[0] > 0
        except Exception:
            pass

        return progress
