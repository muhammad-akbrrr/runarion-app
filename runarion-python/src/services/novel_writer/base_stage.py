"""
Base stage interface for the novel writer pipeline.
Provides consistent method signatures and return types for all stages.
Independent from the deconstructor's base_stage - tailored for novel generation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PipelineStageResult:
    """
    Standardized result container for pipeline stage execution.
    """

    def __init__(self, success: bool, stage_name: str, **kwargs):
        self.success = success
        self.stage_name = stage_name
        self.timestamp = datetime.now().isoformat()
        self.data = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return {
            'success': self.success,
            'stage_name': self.stage_name,
            'timestamp': self.timestamp,
            **self.data
        }

    def add_data(self, **kwargs) -> 'PipelineStageResult':
        """Add additional data to the result."""
        self.data.update(kwargs)
        return self

    @classmethod
    def success_result(cls, stage_name: str, **kwargs) -> 'PipelineStageResult':
        """Create a successful result."""
        return cls(True, stage_name, **kwargs)

    @classmethod
    def error_result(cls, stage_name: str, error: str, **kwargs) -> 'PipelineStageResult':
        """Create an error result."""
        return cls(False, stage_name, error=error, **kwargs)


class PipelineStageContext:
    """
    Context object containing stage execution parameters and metadata.
    Supports both standalone and transactional execution.
    """

    def __init__(self, draft_id: str, user_id: int = None, workspace_id: str = None,
                 test_mode: bool = False, config: Dict[str, Any] = None, **kwargs):
        self.draft_id = draft_id
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.test_mode = test_mode
        self.config = config or {}
        self.execution_timestamp = datetime.now()
        self.metadata = kwargs

        self._derived_values_fetched = bool(self.user_id and self.workspace_id)

    def get_user_id(self, db_pool=None) -> int:
        """
        Get user_id, deriving from draft data if not provided.
        """
        if self.user_id:
            return self.user_id

        if db_pool and not self._derived_values_fetched:
            self._derive_context_from_draft(db_pool)

        return self.user_id or 1

    def get_workspace_id(self, db_pool=None) -> str:
        """
        Get workspace_id, deriving from draft data if not provided.
        """
        if self.workspace_id:
            return self.workspace_id

        if db_pool and not self._derived_values_fetched:
            self._derive_context_from_draft(db_pool)

        return self.workspace_id

    def _derive_context_from_draft(self, db_pool):
        """Derive user_id and workspace_id from draft record."""
        try:
            conn = db_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT d.workspace_id, d.user_id
                        FROM drafts d
                        WHERE d.id = %s
                    """, (self.draft_id,))

                    result = cursor.fetchone()
                    if result:
                        self.workspace_id = result[0]
                        self.user_id = result[1]
                        self._derived_values_fetched = True
            finally:
                db_pool.putconn(conn)
        except Exception:
            pass

    def get(self, key: str, default=None):
        """Get metadata value."""
        return self.metadata.get(key, default)

    def set(self, key: str, value: Any):
        """Set metadata value."""
        self.metadata[key] = value

    def update(self, **kwargs):
        """Update multiple metadata values."""
        self.metadata.update(kwargs)


class BasePipelineStage(ABC):
    """
    Abstract base class for all novel writer pipeline stages.
    Ensures consistent interface and transaction support.
    """

    def __init__(self, db_pool, stage_name: str, generation_engine=None):
        """
        Initialize base stage.

        Args:
            db_pool: Database connection pool
            stage_name: Name of the stage for logging/reporting
            generation_engine: Optional AI generation engine
        """
        self.db_pool = db_pool
        self.stage_name = stage_name
        self.generation_engine = generation_engine
        self.logger = logging.getLogger(f"{__name__}.{stage_name}")

    @abstractmethod
    def _execute_stage(self, context: PipelineStageContext) -> PipelineStageResult:
        """
        Execute the main stage logic.

        Args:
            context: Stage execution context with draft_id and metadata

        Returns:
            PipelineStageResult with success/failure and stage-specific data
        """
        pass

    def run(self, draft_id: str, *args, user_id: int = None, workspace_id: str = None,
            test_mode: bool = False, config: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute the stage with standardized interface.
        """
        context_kwargs = dict(kwargs)

        context = PipelineStageContext(
            draft_id=draft_id,
            user_id=user_id,
            workspace_id=workspace_id,
            test_mode=test_mode,
            config=config or {},
            **context_kwargs
        )

        try:
            self.logger.info(f"Starting {self.stage_name} for draft {draft_id}")
            result = self._execute_stage(context)

            if result.success:
                self.logger.info(f"{self.stage_name} completed successfully for draft {draft_id}")
            else:
                self.logger.error(f"{self.stage_name} failed for draft {draft_id}: {result.data.get('error')}")

            return result.to_dict()

        except Exception as e:
            self.logger.error(f"{self.stage_name} failed with exception for draft {draft_id}: {e}")
            error_result = PipelineStageResult.error_result(
                self.stage_name,
                error=str(e),
                draft_id=draft_id
            )
            return error_result.to_dict()

    def run_with_connection(self, conn, draft_id: str, *args, user_id: int = None,
                            workspace_id: str = None, test_mode: bool = False,
                            config: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute the stage within a database transaction.

        Args:
            conn: Database connection (from orchestrator's cross-stage transaction)
            draft_id: UUID of the draft
            user_id: User ID executing the pipeline
            workspace_id: Workspace ID
            test_mode: Whether running in test mode
            config: Configuration parameters
            **kwargs: Additional stage-specific parameters

        Returns:
            Standardized result dictionary
        """
        context_kwargs = dict(kwargs)

        context = PipelineStageContext(
            draft_id=draft_id,
            user_id=user_id,
            workspace_id=workspace_id,
            test_mode=test_mode,
            config=config or {},
            connection=conn,
            **context_kwargs
        )

        try:
            self.logger.info(
                f"Starting {self.stage_name} (transactional) for draft {draft_id} "
                f"(user_id: {context.get_user_id(self.db_pool)})"
            )
            result = self._execute_stage(context)

            if result.success:
                self.logger.info(f"{self.stage_name} completed successfully (transactional) for draft {draft_id}")
            else:
                self.logger.error(
                    f"{self.stage_name} failed (transactional) for draft {draft_id}: {result.data.get('error')}"
                )

            return result.to_dict()

        except Exception as e:
            self.logger.error(f"{self.stage_name} failed with exception (transactional) for draft {draft_id}: {e}")
            error_result = PipelineStageResult.error_result(
                self.stage_name,
                error=str(e),
                draft_id=draft_id
            )
            return error_result.to_dict()

    def get_database_connection(self, context: PipelineStageContext):
        """
        Get database connection, either from context (transaction) or pool.
        """
        if context.get('connection'):
            return context.get('connection')
        else:
            from utils.database_utils import utf8_database_connection
            return utf8_database_connection(self.db_pool)

    def get_draft_metadata(self, draft_id: str) -> Dict[str, Any]:
        """Retrieve draft metadata from database."""
        try:
            conn = self.db_pool.getconn()

            with conn.cursor() as cursor:
                cursor.execute("SELECT metadata FROM drafts WHERE id = %s", (draft_id,))
                result = cursor.fetchone()

                if result and result[0]:
                    if isinstance(result[0], dict):
                        return result[0]
                    elif isinstance(result[0], str):
                        import json
                        try:
                            return json.loads(result[0])
                        except json.JSONDecodeError:
                            self.logger.warning(f"Invalid JSON in metadata for draft {draft_id}")
                            return {}
                    else:
                        return {}
                return {}

        except Exception as e:
            self.logger.error(f"Failed to get draft metadata for {draft_id}: {e}")
            return {}
        finally:
            if 'conn' in locals():
                self.db_pool.putconn(conn)

    def update_draft_metadata(self, draft_id: str, metadata_updates: Dict[str, Any]) -> None:
        """Update draft metadata in database."""
        try:
            from utils.database_utils import utf8_database_connection, ensure_utf8_json

            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT metadata FROM drafts WHERE id = %s", (draft_id,))
                result = cursor.fetchone()

                current_metadata = {}
                if result and result[0]:
                    if isinstance(result[0], dict):
                        current_metadata = result[0]
                    elif isinstance(result[0], str):
                        import json
                        try:
                            current_metadata = json.loads(result[0])
                        except json.JSONDecodeError:
                            current_metadata = {}

                current_metadata.update(metadata_updates)

                metadata_json = ensure_utf8_json(current_metadata)
                cursor.execute(
                    "UPDATE drafts SET metadata = %s WHERE id = %s",
                    (metadata_json, draft_id)
                )

                conn.commit()
                self.logger.debug(f"Updated metadata for draft {draft_id}")

        except Exception as e:
            self.logger.error(f"Failed to update draft metadata for {draft_id}: {e}")
            raise

    def validate_required_parameters(self, context: PipelineStageContext,
                                     required_params: list) -> Optional[PipelineStageResult]:
        """
        Validate that required parameters are present in context.

        Returns:
            None if validation passes, PipelineStageResult error if it fails.
        """
        missing_params = []
        for param in required_params:
            if context.get(param) is None:
                missing_params.append(param)

        if missing_params:
            return PipelineStageResult.error_result(
                self.stage_name,
                error=f"Missing required parameters: {missing_params}",
                missing_parameters=missing_params
            )

        return None
