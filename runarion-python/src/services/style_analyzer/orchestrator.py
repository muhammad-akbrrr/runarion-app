import logging
import time
import traceback
from typing import Literal, Optional, TypedDict

from models.request import CallerInfo
from models.style_analyzer.author_style import (
    AuthorStyle,
    AuthorStyleExamples,
    AuthorStyleTechniques,
)
from psycopg2.extras import Json
from psycopg2.pool import SimpleConnectionPool
from ulid import ULID
from utils.database_utils import utf8_database_connection

from .stage_1_sampling import SamplingStage
from .stage_2_profiling import ProfilingStage

logger = logging.getLogger(__name__)

AuthorStyleStatus = Literal[
    "init_failed",
    "init_completed",
    "sampling_completed",
    "sampling_failed",
    "profiling_completed",
    "profiling_failed",
]


class StyleAnalyzerResult(TypedDict):
    author_style_id: str
    total_time_ms: int


class StyleAnalyzerSuccess(StyleAnalyzerResult):
    status: Literal["profiling_completed"]
    stored_sample_paths: list[str]
    author_style: AuthorStyle
    error_message: None


class StyleAnalyzerFailed(StyleAnalyzerResult):
    status: Literal["init_failed", "sampling_failed", "profiling_failed"]
    stored_sample_paths: Optional[list[str]]
    author_style: None
    error_message: str


class StyleAnalyzerOrchestrator:
    """
    Orchestrates the complete author style analysis process.
    Manages stage execution, database operations, and error handling.
    """

    def __init__(
        self,
        db_pool: SimpleConnectionPool,
        sampling_stage: SamplingStage,
        profiling_stage: ProfilingStage,
    ):
        """
        Initialize the orchestrator with stages and other dependencies.

        Args:
            db_pool (SimpleConnectionPool): Database connection pool.
            sampling_stage (SamplingStage): Instance of the sampling stage.
            profiling_stage (ProfilingStage): Instance of the profiling stage.

        """
        self.db_pool = db_pool
        self.sampling_stage = sampling_stage
        self.profiling_stage = profiling_stage

    def _get_author_style(
        self, workspace_id: str, author_name: str
    ) -> tuple[Optional[str], Optional[dict], Optional[dict]]:
        """
        Retrieve the author style from the database by its ID.

        Args:
            workspace_id (str): Unique identifier for the workspace.
            author_name (str): Author name that is unique within the workspace.

        Returns:
            Optional[str]: Author style ID if found, otherwise None.
            Optional[dict]: AuthorStyle techniques JSON if found, otherwise None.
            Optional[dict]: AuthorStyle examples JSON if found, otherwise None.
        """
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, techniques_json, examples_json
                    FROM structured_author_styles
                    WHERE workspace_id = %s AND author_name = %s
                    """,
                    (workspace_id, author_name),
                )
                row = cursor.fetchone()
                if row:
                    id, techniques_json, examples_json = row
                    return id, techniques_json, examples_json
                return None, None, None
        except Exception as e:
            logger.error(f"Failed to retrieve author style: {e}")
            raise

    def _soft_delete_author_style_relations(self, author_style_id: str):
        """
        Soft delete all relations of an author style in the database.

        Args:
            author_style_id (str): Unique identifier for the author's style.
        """
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE author_styles_to_samples SET deleted_at = NOW() WHERE author_style_id = %s",
                    (author_style_id,),
                )
                cursor.execute(
                    "UPDATE author_style_chunks SET deleted_at = NOW() WHERE author_style_id = %s",
                    (author_style_id,),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to soft delete author style relations: {e}")
            raise

    def _create_author_style(
        self,
        author_style_id: str,
        author_name: str,
        caller: CallerInfo,
    ):
        """
        Create a new author style in the database.

        Args:
            author_style_id (str): Unique identifier for the author's style.
            author_name (str): Author name that is unique within the workspace.
            caller (CallerInfo): Information about the caller.
        """
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO structured_author_styles 
                    (id, workspace_id, project_id, user_id, author_name, status, started_at)
                    VALUES (%s, %s, %s, %s, %s, 'init_completed', NOW())
                    ON CONFLICT ON CONSTRAINT unique_workspace_author_name
                    DO UPDATE SET
                        project_id = EXCLUDED.project_id,
                        user_id = EXCLUDED.user_id,
                        status = 'init_completed',
                        started_at = NOW(),
                        updated_at = NOW()
                    """,
                    (
                        author_style_id,
                        caller.workspace_id,
                        caller.project_id,
                        caller.user_id,
                        author_name,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to create author style: {e}")
            raise

    def _update_author_style(
        self,
        author_style_id: str,
        author_style: Optional[AuthorStyle],
        status: AuthorStyleStatus,
        error_message: Optional[str],
        total_time_ms: Optional[int],
    ):
        """
        Update the author style in the database.

        Args:
            author_style_id (str): Unique identifier for the author's style.
            author_style (Optional[AuthorStyle]): The analyzed author style data.
            status (AuthorStyleStatus): Current status of the analysis.
            error_message (Optional[str]): Error message if the analysis failed.
            total_time_ms (Optional[int]): Total time taken for the analysis in milliseconds.
        """
        try:
            if author_style is None:
                techniques = None
                examples = None
            else:
                techniques = Json(author_style.techniques.model_dump(mode="json"))
                examples = Json(author_style.examples.model_dump(mode="json"))

            if error_message is not None:
                error_message = error_message + "\n\n" + traceback.format_exc()

            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE structured_author_styles
                    SET techniques_json = %s, examples_json = %s,
                        status = %s, error_message = %s,
                        total_time_ms = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        techniques,
                        examples,
                        status,
                        error_message,
                        total_time_ms,
                        author_style_id,
                    ),
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to store author style result: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def _calc_total_time(self, start_time: float) -> int:
        """
        Calculate the total time in milliseconds since the start time.

        Args:
            start_time (float): The start time in seconds.

        Returns:
            int: Total time in milliseconds.
        """
        return int((time.time() - start_time) * 1000)

    def check_and_clean(
        self,
        author_name: str,
        caller: CallerInfo,
        on_exist: Literal["update", "get", "error"] = "error",
    ) -> tuple[Optional[str], Optional[AuthorStyle]]:
        """
        Check if the author style already exists and delete its relations if on_exist is 'update'.
        Raise an error if query error or if exists and on_exist is 'error'.

        Args:
            author_name (str): Author name that is unique within the workspace.
            caller (CallerInfo): Information about the caller.
            on_exist (Literal["update", "get", "error"]): Behavior when author style already exists.

        Returns:
            tuple[Optional[str], Optional[AuthorStyle]]: Author style ID and existing author style if found.
        """
        author_style_id, techniques_json, examples_json = self._get_author_style(
            caller.workspace_id, author_name
        )

        if author_style_id is not None:
            if on_exist == "update":
                self._soft_delete_author_style_relations(author_style_id)
                return author_style_id, None
            elif on_exist == "get":
                if techniques_json is not None and examples_json is not None:
                    return author_style_id, AuthorStyle(
                        techniques=AuthorStyleTechniques(**techniques_json),
                        examples=AuthorStyleExamples(**examples_json),
                    )
            elif on_exist == "error":
                raise ValueError("Author style already exists")

        return None, None

    def run_pipeline(
        self,
        author_style_id: Optional[str],
        author_name: str,
        file_paths: list[str],
        caller: CallerInfo,
    ) -> StyleAnalyzerSuccess | StyleAnalyzerFailed:
        """
        Safely run the complete style analysis pipeline for the given author style ID and file paths.

        Args:
            author_style_id (Optional[str]): Unique identifier for the author's style, if existing.
            author_name (str): Author name that is unique within the workspace.
            file_paths (list[str]): List of file paths to be processed.
            caller (CallerInfo): Information about the caller.

        Returns:
            StyleAnalyzerResult: Result of the style analysis process.
        """
        start_time = time.time()
        if author_style_id is None:
            author_style_id = str(ULID())
        try:
            self._create_author_style(author_style_id, author_name, caller)
        except Exception as e:
            logger.error(str(e), exc_info=True)
            return {
                "author_style_id": author_style_id,
                "stored_sample_paths": None,
                "total_time_ms": self._calc_total_time(start_time),
                "status": "init_failed",
                "author_style": None,
                "error_message": str(e),
            }

        try:
            samples = self.sampling_stage.run(author_style_id, file_paths)
            stored_samples = [
                sample["file_path"] for sample in samples if sample["success"]
            ]
        except Exception as e:
            error_text = f"Sampling failed: {e}"
            logger.error(error_text, exc_info=True)
            total_time_ms = self._calc_total_time(start_time)
            try:
                self._update_author_style(
                    author_style_id,
                    None,
                    "sampling_failed",
                    error_text,
                    total_time_ms,
                )
            except Exception:
                logger.error(
                    "Failed to update author style after sampling failure",
                    exc_info=True,
                )
            return {
                "author_style_id": author_style_id,
                "stored_sample_paths": None,
                "total_time_ms": total_time_ms,
                "status": "sampling_failed",
                "author_style": None,
                "error_message": error_text,
            }

        try:
            author_style = self.profiling_stage.run(author_style_id, caller)
            status = "profiling_completed"
            error_text = None
        except Exception as e:
            error_text = f"Profiling failed: {e}"
            logger.error(error_text, exc_info=True)
            author_style = None
            status = "profiling_failed"

        total_time_ms = self._calc_total_time(start_time)
        try:
            self._update_author_style(
                author_style_id, author_style, status, error_text, total_time_ms
            )
        except Exception as e:
            logger.error(
                f"Failed to update author style after profiling: {e}", exc_info=True
            )

        if author_style is not None:
            return {
                "author_style_id": author_style_id,
                "stored_sample_paths": stored_samples,
                "total_time_ms": total_time_ms,
                "status": "profiling_completed",
                "author_style": author_style,
                "error_message": None,
            }
        else:
            return {
                "author_style_id": author_style_id,
                "stored_sample_paths": stored_samples,
                "total_time_ms": total_time_ms,
                "status": "profiling_failed",
                "author_style": None,
                "error_message": str(error_text),
            }
