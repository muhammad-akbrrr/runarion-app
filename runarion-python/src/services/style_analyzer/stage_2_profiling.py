import json
import logging
import os
from math import ceil
from typing import Literal, Optional, TypedDict

from models.request import BaseGenerationRequest, CallerInfo, GenerationConfig
from models.response import BaseGenerationResponse
from models.style_analyzer import AuthorStyle
from psycopg2.pool import SimpleConnectionPool
from pydantic import ValidationError
from services.generation_engine import GenerationEngine
from ulid import ULID
from utils.database_utils import clean_text_for_database, utf8_database_connection
from utils.document_processor import ChunkWithStart, DocumentProcessor
from utils.json_response_parser import JSONResponseParser, ResponseFormat

from .prompt_template import (
    COMBINED_AUTHOR_STYLE,
    INPUT_CONTENT,
    PARTIAL_AUTHOR_STYLE,
    STRUCTURED_AUTHOR_STYLE,
)

logger = logging.getLogger(__name__)


class SimpleAuthorSample(TypedDict):
    id: str
    name: str
    text: str


class StyleChunk(ChunkWithStart):
    sample_id: str
    sample_name: str


class Style(TypedDict):
    text: str  # style text
    token: int  # number of tokens in the text
    processing_time_ms: int  # LLM processing time in milliseconds
    chunk: Optional[StyleChunk]  # chunk information
    ref_style_ids: Optional[
        list[str]
    ]  # IDs of other styles used for obtaining this style


class StyleWithId(Style):
    id: str  # ID of the style in the database


class ProfilingStage:
    """
    Stage 2 of the Author Style Analyzer: Profiling Stage.
    This stage processes the samples collected in the Sampling Stage to analyze the author style and store the results.
    """

    def __init__(
        self,
        db_pool: SimpleConnectionPool,
        provider: Optional[str] = "gemini",
        model: Optional[str] = "gemini-2.0-flash",
        max_output_tokens: Optional[int] = 2000,
        generation_config: Optional[dict] = None,
        min_success_partial_style: Optional[int | float] = 0.5,
    ):
        """
        Initialize the profiling stage with document processor and generation configuration.

        Args:
            db_pool (SimpleConnectionPool): Database connection pool for storing processed samples.
            provider (Optional[str]): The provider for the document processor.
            model (Optional[str]): The model to be used for processing.
            max_output_tokens (Optional[int]): Maximum number of output tokens for the document processor.
            generation_config (Optional[dict]): Override configuration for LLM generation.
            min_success_partial_style (Optional[int | float]): Minimum successful partial styles to proceed with combined style analysis, float means ratio, int means count.
        """
        self.db_pool = db_pool
        self.min_success_partial_style = (
            min_success_partial_style if min_success_partial_style is not None else 0.5
        )

        self._provider = provider if provider else "gemini"
        self._model = model if model else "gemini-2.0-flash"

        default_generation_config = {
            "temperature": 0.7,
            "nucleus_sampling": 1.0,
            "tail_free_sampling": 1.0,
            "top_k": 0.0,
            "top_a": 0.0,
            "phrase_bias": None,
            "banned_tokens": None,
            "stop_sequences": None,
            "repetition_penalty": 0.0,
        }
        if isinstance(generation_config, dict):
            merged_config = {**default_generation_config, **generation_config}
        else:
            merged_config = default_generation_config
        merged_config["max_output_tokens"] = (
            max_output_tokens if max_output_tokens is not None else 2000
        )
        self.generation_config = GenerationConfig(**merged_config)

        safety_margin = 200
        self.document_processor = DocumentProcessor(
            provider=self._provider,
            model=self._model,
            model_token_safety_margin=(
                merged_config["max_output_tokens"] + safety_margin
            ),
        )
        instruction_tokens = self.document_processor.token_counter.safe_count(
            COMBINED_AUTHOR_STYLE
        )
        self.document_processor.chunk_token_limit -= instruction_tokens

    def _call_llm(
        self,
        text: str,
        mode: Literal["partial", "combined", "structured"],
        caller: CallerInfo,
        raise_errors: bool = False,
    ) -> BaseGenerationResponse:
        """
        Calls the LLM with the given text and mode.

        Args:
            text (str): The text to send to the LLM.
            mode (Literal["partial", "combined", "structured"]): The mode of the request.
            caller (CallerInfo): Information about the caller.
            raise_errors (bool): Whether to raise errors or return them in the response.

        Returns:
            BaseGenerationResponse: The response from the LLM.
        """
        instructions = {
            "partial": PARTIAL_AUTHOR_STYLE,
            "combined": COMBINED_AUTHOR_STYLE,
            "structured": STRUCTURED_AUTHOR_STYLE,
        }
        instruction = instructions[mode]

        prompt = INPUT_CONTENT.format(text=text)

        request = BaseGenerationRequest(
            usecase="author_style",
            provider=self._provider,
            model=self._model,
            prompt=prompt,
            instruction=instruction,
            generation_config=self.generation_config,
            caller=caller,
        )

        engine = GenerationEngine(request)

        response = engine.generate()

        if not response.success and raise_errors:
            error_message = f"LLM call failed for mode {mode}: {response.error_message}"
            logger.error(error_message)
            raise RuntimeError(error_message)

        return response

    def _get_samples(self, author_style_id: str) -> list[SimpleAuthorSample]:
        """
        Retrieve samples to be processed for obtaining author style.

        Args:
            author_style_id (str): The ID of the author style.

        Returns:
            list[SimpleAuthorSample]: A list of samples to be processed.
        """
        try:
            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT asa.id, asa.document_path, asa.text_content
                    FROM author_samples asa
                    INNER JOIN author_styles_to_samples asts ON asa.id = asts.author_sample_id
                    WHERE asts.author_style_id = %s AND asa.text_content IS NOT NULL
                    """,
                    (author_style_id,),
                )
                rows = cursor.fetchall()
                samples: list[SimpleAuthorSample] = []
                for row in rows:
                    sample: SimpleAuthorSample = {
                        "id": row[0],
                        "name": os.path.basename(row[1]),
                        "text": row[2],
                    }
                    samples.append(sample)
                return samples

        except Exception as e:
            logger.error(f"Failed to retrieve author samples: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def _store_style_chunk(
        self,
        author_style_id: str,
        style: Style,
        error_message: Optional[str],
    ) -> StyleWithId:
        """
        Store the author style of chunks in the database.

        Args:
            author_style_id (str): The ID of the author style.
            style (Style): The style to store.
            error_message (Optional[str]): Error message if any occurred during processing.

        Returns:
            StyleWithId: The stored style with its ID.
        """
        try:
            id = str(ULID())
            text = clean_text_for_database(style["text"])

            with utf8_database_connection(self.db_pool) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO author_style_chunks (
                        id, author_style_id, author_sample_id,
                        chunk_number, chunk_start_index, chunk_char_count, chunk_token_count,
                        author_style_chunk_ids, style_text, style_text_token_count, 
                        error_message, processing_time_ms
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        id,
                        author_style_id,
                        style["chunk"]["sample_id"] if style["chunk"] else None,
                        style["chunk"]["chunk_number"] if style["chunk"] else None,
                        style["chunk"]["start"] if style["chunk"] else None,
                        style["chunk"]["character_count"] if style["chunk"] else None,
                        style["chunk"]["token_count"] if style["chunk"] else None,
                        json.dumps(style["ref_style_ids"]),
                        text,
                        style["token"],
                        error_message,
                        style["processing_time_ms"],
                    ),
                )
                conn.commit()

            style_with_id: StyleWithId = {
                "id": id,
                **style,
            }
            return style_with_id

        except Exception as e:
            logger.error(f"Failed to store style chunk: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def _chunk_samples(self, samples: list[SimpleAuthorSample]) -> list[StyleChunk]:
        """
        Chunk the samples into list of StyleChunk.

        Args:
            samples (list[SimpleAuthorSample]): List of samples to chunk.

        Returns:
            list[StyleChunk]: List of StyleChunk objects.
        """
        style_chunks: list[StyleChunk] = []
        for sample in samples:
            chunks = self.document_processor.chunk_text(sample["text"])
            chunks_with_start = self.document_processor.add_start_to_chunks(
                sample["text"], chunks
            )
            for chunk in chunks_with_start:
                style_chunk: StyleChunk = {
                    **chunk,
                    "sample_id": sample["id"],
                    "sample_name": sample["name"],
                }
                style_chunks.append(style_chunk)
        return style_chunks

    def _handle_partial_style(
        self, author_style_id: str, chunk: StyleChunk, caller: CallerInfo
    ) -> StyleWithId:
        """
        Performs style analysis for a single chunk and stores the result.

        Args:
            author_style_id (str): The ID of the author style.
            chunk (StyleChunk): The chunk to analyze.
            caller (CallerInfo): Information about the caller.

        Returns:
            StyleWithId: The analyzed style.
        """
        response = self._call_llm(chunk["raw_text"], "partial", caller)

        if response.success:
            # title is useful for next LLM calls
            title = (
                f"PASSAGE {chunk['chunk_number']} from FILE {chunk['sample_name']}\n\n"
            )
            text = title + response.text
            token = response.metadata.output_tokens
            error_text = None

        else:
            text = ""
            token = -1
            error_text = (
                f"LLM call to obtain partial style failed: {response.error_message}"
            )
            logger.error(error_text)

        style = Style(
            text=text,
            token=token,
            processing_time_ms=response.metadata.processing_time_ms,
            chunk=chunk,
            ref_style_ids=None,
        )

        style_with_id = self._store_style_chunk(
            author_style_id,
            style,
            error_text,
        )

        return style_with_id

    def _handle_combined_style(
        self,
        author_style_id: str,
        styles: list[StyleWithId],
        caller: CallerInfo,
        recursion_depth: int = 0,
    ) -> StyleWithId:
        """
        Combines multiple styles into a single style.
        When the styles are too many, they are split and processed recursively.

        Args:
            author_style_id (str): The ID of the author style.
            styles (list[StyleWithId]): List of styles to combine.
            caller (CallerInfo): Information about the caller.
            recursion_depth (int): Current recursion depth.

        Returns:
            StyleWithId: The combined style.
        """
        if recursion_depth > 5:
            error_text = "Recursion depth exceeded while combining styles"
            logger.error(error_text)
            raise RuntimeError(error_text)

        # recursion base case 1:
        # if there is only one style, return it directly
        if len(styles) == 1:
            return styles[0]

        total_token = sum(s["token"] for s in styles)

        # recursion base case 2:
        # if the total token count is within the limit,
        # perform combined style analysis and store the result
        if total_token < self.document_processor.chunk_token_limit:
            response = self._call_llm(
                "\n\n".join([s["text"] for s in styles]), "combined", caller
            )

            if response.success:
                # title can be useful for next LLM calls
                title = "Analyzed Author Style from Multiple (but possibly not all) PASSAGEs and FILEs\n\n"
                text = title + response.text
                token = response.metadata.output_tokens
                error_text = None

            else:
                text = ""
                token = -1
                error_text = f"LLM call to obtain combined style failed: {response.error_message}"
                logger.error(error_text)

            style = Style(
                text=text,
                token=token,
                processing_time_ms=response.metadata.processing_time_ms,
                chunk=None,
                ref_style_ids=[s["id"] for s in styles],
            )

            style_with_id = self._store_style_chunk(
                author_style_id,
                style,
                error_text,
            )

            if error_text:
                raise RuntimeError(error_text)

            return style_with_id

        # otherwise:
        # split the styles, handle each split, and merge the results into reduced_styles
        # splitting example: split 22 into 4 -> [6, 6, 5, 5]
        n_splits = ceil(total_token / self.document_processor.chunk_token_limit)
        style_base_count = len(styles) // n_splits
        style_remainder = len(styles) % n_splits
        reduced_styles: list[StyleWithId] = []
        for i in range(n_splits):
            start = i * style_base_count + min(i, style_remainder)
            end = start + style_base_count + (1 if i < style_remainder else 0)
            combined_style = self._handle_combined_style(
                author_style_id,
                styles[start:end],
                caller,
                recursion_depth=recursion_depth + 1,
            )  # this call here should reach the base case
            reduced_styles.append(combined_style)

        # recursively handle the reduced_styles
        return self._handle_combined_style(
            author_style_id, reduced_styles, caller, recursion_depth=recursion_depth + 1
        )

    def _handle_structured_style(
        self, combined_style: StyleWithId, caller: CallerInfo
    ) -> AuthorStyle:
        """
        Converts the combined style text into a structured AuthorStyle object.

        Args:
            combined_style (StyleWithId): The combined style to analyze.
            caller (CallerInfo): Information about the caller.

        Returns:
            AuthorStyle: The structured author style.
        """
        response = self._call_llm(
            combined_style["text"], "structured", caller, raise_errors=True
        )

        try:
            author_style = self._parse_structured_response(response.text)
        except Exception:
            # if parsing fails, try to call the LLM and parse the response once again
            response = self._call_llm(
                combined_style["text"], "structured", caller, raise_errors=True
            )
            author_style = self._parse_structured_response(response.text)

        return author_style

    def _parse_structured_response(self, text: str) -> AuthorStyle:
        """
        Parses the LLM response and returns an AuthorStyle object.

        Args:
            text (str): The text response from the LLM, expected to be in JSON format.

        Returns:
            AuthorStyle: The parsed author style object.
        """
        parsed, fmt = JSONResponseParser.parse_response(
            text, expected_type="dict", fallback_value=None
        )

        if parsed is None or fmt in (
            ResponseFormat.EMPTY_RESPONSE,
            ResponseFormat.NON_JSON,
        ):
            error_text = "Invalid structured response format: No valid JSON found"
            logger.error(
                "%s | Parser Input: %s | Parser Output: %s", error_text, text, fmt
            )
            raise ValueError(error_text)

        try:
            author_style = AuthorStyle(**parsed)
        except ValidationError:
            logger.error("Failed to parse dict into AuthorStyle: %s", str(parsed))
            raise

        return author_style

    def run(self, author_style_id: str, caller: CallerInfo) -> AuthorStyle:
        """
        Executes the author style analysis process.

        Args:
            author_style_id (str): The ID of the author style.
            caller (CallerInfo): Information about the caller.

        Returns:
            dict: The final structured style data.
        """
        samples = self._get_samples(author_style_id)
        chunks = self._chunk_samples(samples)

        partial_styles = [
            self._handle_partial_style(author_style_id, chunk, caller)
            for chunk in chunks
        ]

        success_count = sum(1 for s in partial_styles if s["token"] > 0)
        if isinstance(self.min_success_partial_style, int):
            okay = success_count >= self.min_success_partial_style
        else:
            okay = success_count / len(partial_styles) >= self.min_success_partial_style
        if not okay:
            error_text = f"Not enough successful partial styles: {success_count} out of {len(partial_styles)}"
            logger.error(error_text)
            raise RuntimeError(error_text)

        combined_style = self._handle_combined_style(
            author_style_id, partial_styles, caller
        )

        structured_style = self._handle_structured_style(combined_style, caller)

        return structured_style
