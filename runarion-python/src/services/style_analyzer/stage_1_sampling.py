import hashlib
import logging
from typing import Optional, TypedDict

from psycopg2.pool import SimpleConnectionPool
from ulid import ULID

from src.utils.database_utils import clean_text_for_database, utf8_database_connection
from src.utils.document_reader import DocumentReader

logger = logging.getLogger(__name__)


class SamplingResult(TypedDict):
    file_path: str
    success: bool


class SamplingStage:
    """
    Stage 1 of the Author Style Analyzer: Sampling Stage.
    This stage processes document files to extract, clean, and store their text content.
    It skips documents that have already been processed.
    """

    def __init__(
        self,
        db_pool: SimpleConnectionPool,
        min_success_samples: Optional[int | float] = 0.5,
    ):
        """
        Initialize the sampling stage with document reader configuration.

        Args:
            db_pool: Database connection pool for storing processed documents
            min_success_samples (Optional[int | float]): Minimum number of successful samples, float means ratio, int means count.
        """
        self.db_pool = db_pool
        self.document_reader = DocumentReader()
        self.min_success_samples = (
            min_success_samples if min_success_samples is not None else 0.5
        )

    @staticmethod
    def calc_md5_hash(file_path: str) -> str:
        """
        Calculates the MD5 hash of a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            str: The hexadecimal MD5 hash of the file.
        """
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            # Read the file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def _check_file_processed(self, md5_hash: str) -> tuple[str | None, bool]:
        """
        Check if the file has already been processed by looking for its MD5 hash in the database.

        Args:
            md5_hash (str): The MD5 hash of the file.

        Returns:
            str | None: The sample id if found, None otherwise.
            bool: True if the text is not null.
        """
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, text_content IS NOT NULL FROM author_samples WHERE document_hash = %s",
                    (md5_hash,),
                )
                result = cursor.fetchone()
                if result:
                    id, okay = result
                    return id, okay
                else:
                    return None, False

        except Exception as e:
            logger.error(f"Failed to check file processed: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def _store_author_sample(
        self,
        path: str,
        md5_hash: Optional[str],
        text_content: Optional[str],
        error_message: Optional[str],
    ) -> str:
        """
        Store the the processing result to the database.

        Args:
            path (str): The path to the document file.
            md5_hash (Optional[str]): The MD5 hash of the document file.
            text_content (Optional[str]): The cleaned text content of the document.
            error_message (Optional[str]): Error message if any occurred during processing.

        Returns:
            str: The sample id of the stored document.
        """
        try:
            cleaned_text = (
                clean_text_for_database(text_content) if text_content else None
            )
            id = str(ULID())

            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO author_samples (id, document_path, document_hash, text_content, error_message)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (id, path, md5_hash, cleaned_text, error_message),
                )
                conn.commit()

            return id

        except Exception as e:
            logger.error(f"Failed to store author sample: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def _store_author_style_to_sample(
        self, author_style_id: str, sample_ids: list[str]
    ) -> None:
        """
        Store the relationship between an author style and a sample in the database.

        Args:
            author_style_id (str): The ID of the author style.
            sample_ids (list[str]): List of sample IDs to associate with the author style.
        """
        try:
            data = [
                (str(ULID()), author_style_id, sample_id) for sample_id in sample_ids
            ]

            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                cursor.executemany(
                    """
                    INSERT INTO author_styles_to_samples (id, author_style_id, author_sample_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT ON CONSTRAINT unique_author_styles_sample
                    DO UPDATE SET deleted_at = NULL
                    """,
                    data,
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to store author style to sample: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def process_file(self, file_path: str, md5_hash: str) -> tuple[str, bool]:
        """
        Process a single document file to extract and store its text content.

        Args:
            file_path (str): The path to the document file.
            md5_hash (str): The hash of the document file.

        Returns:
            str: The sample id of the processed document.
            bool: If the process works properly.
        """
        # Check if the file has already been processed
        existing_sample_id, okay = self._check_file_processed(md5_hash)
        if existing_sample_id:
            return existing_sample_id, okay

        # Extract and clean the document content
        text_content = self.document_reader.extract(file_path)
        cleaned_text = self.document_reader.clean(text_content)

        # Store the processed file in the database
        sample_id = self._store_author_sample(file_path, md5_hash, cleaned_text, None)

        return sample_id, True

    def run(self, author_style_id: str, file_paths: list[str]) -> list[SamplingResult]:
        """
        Run the sampling stage for a list of document files.

        Args:
            author_style_id (str): The ID of the author style to associate with the samples.
            file_paths (list[str]): List of paths to document files to process.

        Returns:
            list[SamplingResult]: List of results containing file paths and success status.
        """
        sample_ids, results = [], []
        for file_path in file_paths:
            md5_hash = self.calc_md5_hash(file_path)
            try:
                sample_id, success = self.process_file(file_path, md5_hash)
            except Exception as e:
                logger.warning(f"Error processing file {file_path}: {e}")
                sample_id = self._store_author_sample(file_path, md5_hash, None, str(e))
                success = False
            if success:
                sample_ids.append(sample_id)
            results.append({"file_path": file_path, "success": success})

        success_count = sum(1 for result in results if result["success"])
        if isinstance(self.min_success_samples, int):
            okay = success_count >= self.min_success_samples
        else:
            okay = success_count / len(results) >= self.min_success_samples
        if not okay:
            error_text = f"Sampling failed with only {success_count} successful samples out of {len(results)}"
            logger.error(error_text)
            raise Exception(error_text)

        # Store the relationship between the author style and the processed samples
        if sample_ids:
            self._store_author_style_to_sample(author_style_id, sample_ids)

        return results
