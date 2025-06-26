import json
import os
import time
from math import ceil
from typing import Literal, NamedTuple, Optional

import demjson3
from flask import current_app
from models.deconstructor.author_style import AuthorStyle
from models.request import CallerInfo, GenerationConfig
from models.response import BaseGenerationResponse
from psycopg2.pool import SimpleConnectionPool
from pydantic import ValidationError
from services.generation_engine import GenerationEngine
from services.usecase_handler.author_style_handler import (
    COMBINED_AUTHOR_STYLE,
    PARTIAL_AUTHOR_STYLE,
    AuthorStyleHandler,
)
from ulid import ULID
from utils.get_model_max_token import get_model_max_token

from ..utils.paragraph_extractor import ParagraphExtractor
from ..utils.token_counter import TokenCounter


class Passage(NamedTuple):
    source: str  # source file name of the passage
    num: int  # passage number
    text: str  # text content


# dictionary with source file names as keys and lists of passage numbers as values
StylePassages = dict[str, list[int]]


class Style(NamedTuple):
    text: str  # style content
    token: int  # number of tokens in the text
    processing_time_ms: int  # LLM processing time in milliseconds
    passages: StylePassages


class AuthorStyleConfiguration:
    """
    Handles the configuration and execution of author style analysis.
    """

    def __init__(
        self,
        paragraph_extractors: list[ParagraphExtractor],
        caller: CallerInfo,
        connection_pool: SimpleConnectionPool,
        author_name: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        generation_config: Optional[dict] = None,
        paragraph_overlap: Optional[bool] = False,
        store_intermediate: Optional[bool] = False,
    ):
        """
        Args:
            paragraph_extractors (list[ParagraphExtractor]): List of paragraph extractors, each associated with a source file.
            caller (CallerInfo): Caller information.
            connection_pool (SimpleConnectionPool): Database connection pool for storing results.
            author_name (str): Name for identifying the author style.
            provider (Optional[str]): The model provider, defaults to "gemini".
            model (Optional[str]): The model name, defaults to "gemini-2.0-flash".
            generation_config (Optional[dict]): Override configuration for LLM generation.
            paragraph_overlap (Optional[bool]): Whether to allow overlaping paragraphs in the passages, defaults to False.
            store_intermediate (Optional[bool]): Whether to store intermediate styles, defaults to False.
        """
        default_generation_config = {
            "temperature": 0.7,
            "max_output_tokens": 2000,
            "nucleus_sampling": 1.0,
            "tail_free_sampling": 1.0,
            "top_k": 0.0,
            "top_a": 0.0,
            "phrase_bias": None,
            "banned_tokens": None,
            "stop_sequences": None,
            "repetition_penalty": 0.0,
        }

        self.paragraph_extractors = paragraph_extractors
        self.caller = caller
        self.connection_pool = connection_pool
        self.author_name = author_name
        self.provider = provider or "gemini"
        self.model = model or "gemini-2.0-flash"
        # Only merge if generation_config is a dict, else use default
        if isinstance(generation_config, dict):
            merged_config = {**default_generation_config, **generation_config}
        else:
            merged_config = default_generation_config
        self.generation_config = GenerationConfig(**merged_config)
        self.paragraph_overlap = paragraph_overlap or False
        self.store_intermediate = store_intermediate or False

        # calculate max token of content in partial and combined prompts
        RESERVED_TOKENS_FOR_SAFETY = 100
        self.token_counter = TokenCounter(self.provider, self.model)
        model_max_token = (
            get_model_max_token(self.provider, self.model) -
            RESERVED_TOKENS_FOR_SAFETY
        )
        partial_prompt_token = self.token_counter.count_tokens(
            PARTIAL_AUTHOR_STYLE)
        combined_prompt_token = self.token_counter.count_tokens(
            COMBINED_AUTHOR_STYLE)
        self.partial_max_token = model_max_token - partial_prompt_token
        self.combined_max_token = model_max_token - combined_prompt_token

        # id for the structured style
        self.id = str(ULID())

        # list of source file names
        self.sources = [
            os.path.basename(extractor.file_path) for extractor in paragraph_extractors
        ]

    def construct_passages(self) -> list[Passage]:
        """
        Constructs passages from the extracted paragraphs
        considering overlap and token limits.

        Returns:
            list[Passage]: List of constructed passages.
        """
        # dictionary with source file names as keys and lists of paragraphs as values
        all_paragraphs: dict[str, list[str]] = {}
        for i, source in enumerate(self.sources):
            extractor = self.paragraph_extractors[i]
            paragraphs = extractor.run()
            all_paragraphs[source] = paragraphs

        # dictionary with source file names as keys and lists of token counts as values
        token_counts: dict[str, list[int]] = {}
        for source, paragraphs in all_paragraphs.items():
            token_counts[source] = [
                self.token_counter.count_tokens(p) for p in paragraphs
            ]

        passages: list[Passage] = []
        for source in self.sources:
            # list of paragraphs in the current passage
            passage: list[str] = []
            token_count = 0  # token count of the current passage
            passage_num = 1  # current passage number
            index = 0  # index of paragraphs
            while index < len(all_paragraphs[source]):
                paragraph = all_paragraphs[source][index]
                paragraph_token_count = token_counts[source][index]
                index += 1

                # if the current paragraph can fit in the passage, add it
                if (token_count + paragraph_token_count) < self.partial_max_token:
                    passage.append(paragraph)
                    token_count += paragraph_token_count
                    continue

                # otherwise, store the current passage
                if passage:
                    passage_text = "".join(passage)
                    passages.append(Passage(source, passage_num, passage_text))

                # if overlap is enabled, include the last paragraph again in the next passage
                if self.paragraph_overlap:
                    index -= 1
                    paragraph = all_paragraphs[source][index]
                    paragraph_token_count = token_counts[source][index]

                # start a new passage
                passage = [paragraph]
                passage_num += 1
                token_count = paragraph_token_count

            # store the last passage
            if passage:
                passage_text = "".join(passage)
                passages.append(Passage(source, passage_num, passage_text))

        return passages

    def _call_llm(
        self, text: str, mode: Literal["partial", "combined", "structured"]
    ) -> BaseGenerationResponse:
        """
        Calls the LLM with the given text and mode.

        Args:
            text (str): The text to send to the LLM.
            mode (Literal["partial", "combined", "structured"]): The mode of the request.
        Returns:
            GenerationResponse: The response from the LLM.
        """

        request = AuthorStyleHandler().build_request(
            {
                "mode": mode,
                "provider": self.provider,
                "model": self.model,
                "text": text,
                "generation_config": self.generation_config,
                "caller": self.caller,
            }
        )

        engine = GenerationEngine(request)

        response = engine.generate()

        if not response.success:
            error_text = f"LLM call failed: {response.error_message}"
            current_app.logger.error(error_text)
            raise RuntimeError(error_text)

        return response

    def _store_intermediate_style(self, style: Style) -> None:
        """
        Stores the intermediate style in the database.

        Args:
            style (Style): The style to store.
        """
        if not self.store_intermediate:
            return
        try:
            with self.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO intermediate_author_styles (id, structured_style_id, style, processing_time_ms, passages)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            str(ULID()),
                            self.id,
                            style.text,
                            style.processing_time_ms,
                            json.dumps(style.passages),
                        ),
                    )
                    conn.commit()
        except Exception as e:
            error_text = f"Failed to store intermediate style: {str(e)}"
            current_app.logger.error(error_text)
            raise RuntimeError(error_text)
        finally:
            self.connection_pool.putconn(conn)

    def _store_structured_style(
        self, data: dict, started_at: str, total_time_ms: int
    ) -> None:
        """
        Stores the structured style in the database.

        Args:
            data (dict): The structured style data.
            started_at (str): The start timestamp of the process.
            total_time_ms (int): The total processing time in milliseconds.
        """
        try:
            with self.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO structured_author_styles (id, workspace_id, project_id, user_id, author_name, style, sources, started_at, total_time_ms)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            self.id,
                            self.caller.workspace_id,
                            self.caller.project_id,
                            self.caller.user_id,
                            self.author_name,
                            json.dumps(data),
                            ", ".join(self.sources),
                            started_at,
                            total_time_ms,
                        ),
                    )
                    conn.commit()
        except Exception as e:
            error_text = f"Failed to store structured style: {str(e)}"
            current_app.logger.error(error_text)
            raise RuntimeError(error_text)
        finally:
            self.connection_pool.putconn(conn)

    def _merge_style_passage(self, styles: list[Style]) -> StylePassages:
        """
        Merges passage information from multiple styles.

        Args:
            styles (list[Style]): List of styles to merge.

        Returns:
            StylePassages: Merged passage information.
        """
        merged_passages: StylePassages = {}
        for style in styles:
            for source, nums in style.passages.items():
                if source not in merged_passages:
                    merged_passages[source] = []
                merged_passages[source].extend(nums)
        return merged_passages

    def _handle_partial_style(self, passage: Passage) -> Style:
        """
        Performs style analysis for a single passage and stores the result.

        Args:
            passage (Passage): The passage to analyze.

        Returns:
            Style: The analyzed style for the passage.
        """
        response = self._call_llm(passage.text, mode="partial")

        # title is useful for next LLM calls
        title = f"PASSAGE {passage.num} from FILE {passage.source}\n\n"

        style = Style(
            text=title + response.text,
            token=response.metadata.output_tokens,
            processing_time_ms=response.metadata.processing_time_ms,
            passages={passage.source: [passage.num]},
        )

        self._store_intermediate_style(style)

        return style

    def _handle_combined_style(
        self, styles: list[Style], recursion_depth: int = 0
    ) -> Style:
        """
        Combines multiple styles into a single style.
        When the styles are too many, they are split and processed recursively.

        Args:
            styles (list[Style]): List of styles to combine.
            recursion_depth (int): Current recursion depth.

        Returns:
            Style: The combined style.
        """
        if recursion_depth > 5:
            error_text = "Recursion depth exceeded while combining styles"
            current_app.logger.error(error_text)
            raise RuntimeError(error_text)

        # recursion base case 1:
        # if there is only one style, return it directly
        if len(styles) == 1:
            return styles[0]

        total_token = sum(s.token for s in styles)

        # recursion base case 2:
        # if the total token count is within the limit,
        # perform combined style analysis and store the result
        if total_token < self.combined_max_token:
            response = self._call_llm(
                "\n\n".join([s.text for s in styles]), mode="combined"
            )

            # title can be useful for next LLM calls
            title = "Analyzed Author Style from Multiple (but possibly not all) PASSAGEs and FILEs\n\n"

            style = Style(
                text=title + response.text,
                token=response.metadata.output_tokens,
                passages=self._merge_style_passage(styles),
                processing_time_ms=response.metadata.processing_time_ms,
            )
            self._store_intermediate_style(style)
            return style

        # otherwise:
        # split the styles, handle each split, and merge the results into reduced_styles
        # splitting example: split 22 into 4 -> [6, 6, 5, 5]
        n_splits = ceil(total_token / self.combined_max_token)
        style_base_count = len(styles) // n_splits
        style_remainder = len(styles) % n_splits
        reduced_styles: list[Style] = []
        for i in range(n_splits):
            start = i * style_base_count + min(i, style_remainder)
            end = start + style_base_count + (1 if i < style_remainder else 0)
            combined_style = self._handle_combined_style(
                styles[start:end], recursion_depth + 1
            )  # this call here should reach the base case
            reduced_styles.append(combined_style)

        # recursively handle the reduced_styles
        return self._handle_combined_style(reduced_styles, recursion_depth + 1)

    def _parse_structured_response(self, text: str) -> AuthorStyle:
        """
        Parses the LLM response and returns an AuthorStyle object.

        Args:
            text (str): The text response from the LLM, expected to be in JSON format.

        Returns:
            AuthorStyle: The parsed author style object.
        """
        start_index = text.find("{")
        end_index = text.rfind("}")
        if start_index == -1 or end_index == -1 or start_index >= end_index:
            error_text = "Invalid structured response format: No valid JSON found"
            current_app.logger.error(error_text)
            raise ValueError(error_text)
        clean_text = text[start_index: end_index + 1]

        try:
            data_dict = demjson3.decode(clean_text)
        except demjson3.JSONDecodeError:
            current_app.logger.error(
                "Invalid LLM output: Not a valid JSON. Output was: %s", clean_text
            )
            raise

        try:
            author_style = AuthorStyle(**data_dict)
        except ValidationError:
            current_app.logger.error(
                "Failed to parse dict into AuthorStyle: %s", str(data_dict)
            )
            raise

        return author_style

    def run(self) -> AuthorStyle:
        """
        Executes the author style analysis process.

        Returns:
            AuthorStyle: The extracted structured author style.
        """
        start_time = time.monotonic()
        start_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        passages = self.construct_passages()
        partial_styles = [self._handle_partial_style(
            passage) for passage in passages]
        combined_style = self._handle_combined_style(partial_styles)

        response = self._call_llm(combined_style.text, mode="structured")

        # Debug: print the LLM response text before JSON decode
        print("[DEBUG] LLM structured response.text:", repr(response.text))

        try:
            author_style = self._parse_structured_response(response.text)
        except Exception:
            # if parsing fails, try to call the LLM and parse the response once again
            response = self._call_llm(combined_style.text, mode="structured")
            author_style = self._parse_structured_response(response.text)

        total_time_ms = int((time.monotonic() - start_time) * 1000)
        self._store_structured_style(
            author_style.model_dump(), start_at, total_time_ms)

        return author_style
