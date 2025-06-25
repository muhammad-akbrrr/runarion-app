import json
import os
import time
from math import ceil
from typing import Literal, NamedTuple, Optional

from models.deconstructor.author_style import AuthorStyle
from models.deconstructor.story_rewrite import ContentRewriteConfig, RewrittenContent, WritingPerspective
from models.request import CallerInfo, GenerationConfig
from models.response import BaseGenerationResponse
from psycopg2.pool import SimpleConnectionPool
from services.generation_engine import GenerationEngine
from ulid import ULID
from services.usecase_handler.content_rewrite_handler import ContentRewriteHandler
from utils.get_model_max_token import get_model_max_token

from ..utils.paragraph_extractor import ParagraphExtractor
from ..utils.token_counter import TokenCounter


class ContentChunk(NamedTuple):
    source: str  # source file name
    chunk_num: int  # chunk number
    text: str  # text content
    original_paragraphs: list[int]  # indices of original paragraphs


class ContentRewritePipeline:
    """
    Handles the configuration and execution of content rewriting pipeline.
    This pipeline takes PDF content, analyzes it, and rewrites it in a specified author's style
    with a chosen writing perspective.
    """

    def __init__(
        self,
        paragraph_extractors: list[ParagraphExtractor],
        author_style: AuthorStyle,
        writing_perspective: WritingPerspective,
        caller: CallerInfo,
        connection_pool: SimpleConnectionPool,
        provider: Optional[str] = "gemini",
        model: Optional[str] = None,
        generation_config: Optional[GenerationConfig] = None,
        rewrite_config: Optional[ContentRewriteConfig] = None,
        chunk_overlap: bool = False,
        store_intermediate: bool = False,
    ):
        """
        Args:
            paragraph_extractors (list[ParagraphExtractor]): List of paragraph extractors, each associated with a source file.
            author_style (AuthorStyle): The author style to apply to the content.
            writing_perspective (WritingPerspective): The writing perspective to use.
            caller (CallerInfo): Caller information.
            connection_pool (SimpleConnectionPool): Database connection pool for storing results.
            provider (Optional[str]): The model provider (e.g., "openai", "gemini").
            model (Optional[str]): The model name.
            generation_config (Optional[GenerationConfig]): Configuration for LLM generation.
            rewrite_config (Optional[ContentRewriteConfig]): Additional rewriting configuration.
            chunk_overlap (bool): Whether to allow overlapping content in chunks.
            store_intermediate (bool): Whether to store intermediate results.
        """
        self.paragraph_extractors = paragraph_extractors
        self.author_style = author_style
        self.writing_perspective = writing_perspective
        self.caller = caller
        self.connection_pool = connection_pool
        self.provider = provider or "gemini"
        self.model = model or "gemini-2.0-flash"
        self.generation_config = generation_config or GenerationConfig()  # type: ignore
        self.rewrite_config = rewrite_config or ContentRewriteConfig(
            author_style=author_style,
            writing_perspective=writing_perspective
        )
        self.chunk_overlap = chunk_overlap
        self.store_intermediate = store_intermediate

        # Calculate max tokens for content chunks
        RESERVED_TOKENS_FOR_SAFETY = 200
        self.token_counter = TokenCounter(self.provider, self.model)
        model_max_token = (
            get_model_max_token(self.provider, self.model) -
            RESERVED_TOKENS_FOR_SAFETY
        )

        # Estimate prompt tokens (this would need to be calculated more precisely)
        estimated_prompt_tokens = 1000  # Conservative estimate
        self.max_content_tokens = model_max_token - estimated_prompt_tokens

        # ID for the rewrite session
        self.id = str(ULID())

        # List of source file names
        self.sources = [
            os.path.basename(extractor.file_path) for extractor in paragraph_extractors
        ]

    def construct_content_chunks(self) -> list[ContentChunk]:
        """
        Constructs content chunks from the extracted paragraphs
        considering overlap and token limits.

        Returns:
            list[ContentChunk]: List of constructed content chunks.
        """
        # Dictionary with source file names as keys and lists of paragraphs as values
        all_paragraphs: dict[str, list[str]] = {}
        for i, source in enumerate(self.sources):
            extractor = self.paragraph_extractors[i]
            paragraphs = extractor.run()
            all_paragraphs[source] = paragraphs
            extractor.clear()

        # Dictionary with source file names as keys and lists of token counts as values
        token_counts: dict[str, list[int]] = {}
        for source, paragraphs in all_paragraphs.items():
            token_counts[source] = [
                self.token_counter.count_tokens(p) for p in paragraphs
            ]

        chunks: list[ContentChunk] = []
        for source in self.sources:
            chunk: list[str] = []  # list of paragraphs in the current chunk
            # indices of paragraphs in the chunk
            chunk_paragraph_indices: list[int] = []
            token_count = 0  # token count of the current chunk
            chunk_num = 1  # current chunk number
            index = 0  # index of paragraphs

            while index < len(all_paragraphs[source]):
                paragraph = all_paragraphs[source][index]
                paragraph_token_count = token_counts[source][index]
                index += 1

                # if the current paragraph can fit in the chunk, add it
                if (token_count + paragraph_token_count) < self.max_content_tokens:
                    chunk.append(paragraph)
                    chunk_paragraph_indices.append(index - 1)
                    token_count += paragraph_token_count
                    continue

                # otherwise, store the current chunk
                if chunk:
                    chunk_text = "".join(chunk)
                    chunks.append(ContentChunk(
                        source, chunk_num, chunk_text, chunk_paragraph_indices
                    ))

                # if overlap is enabled, include the last paragraph again in the next chunk
                if self.chunk_overlap:
                    index -= 1
                    paragraph = all_paragraphs[source][index]
                    paragraph_token_count = token_counts[source][index]

                # start a new chunk
                chunk = [paragraph]
                chunk_paragraph_indices = [index - 1]
                chunk_num += 1
                token_count = paragraph_token_count

            # store the last chunk
            if chunk:
                chunk_text = "".join(chunk)
                chunks.append(ContentChunk(
                    source, chunk_num, chunk_text, chunk_paragraph_indices
                ))

        return chunks

    def _call_llm(self, original_text: str) -> BaseGenerationResponse:
        """
        Calls the LLM to rewrite the given text.

        Args:
            original_text (str): The original text to rewrite.
        Returns:
            BaseGenerationResponse: The response from the LLM.
        """
        request = ContentRewriteHandler().build_request({
            "mode": "rewrite",
            "provider": self.provider,
            "model": self.model,
            "original_text": original_text,
            "rewrite_config": self.rewrite_config,
            "generation_config": self.generation_config,
            "caller": self.caller,
        })

        engine = GenerationEngine(request)
        response = engine.generate()

        if not response.success:
            raise RuntimeError(f"LLM call failed: {response.error_message}")

        return response

    def _store_intermediate_deconstructor(self, rewrite: RewrittenContent, chunk: ContentChunk) -> None:
        """
        Stores the intermediate rewrite result in the intermediate_deconstructor table.

        Args:
            rewrite (RewrittenContent): The rewrite result to store.
            chunk (ContentChunk): The chunk that was rewritten.
        """
        if not self.store_intermediate or not self.request_id:
            return
        try:
            with self.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO intermediate_deconstructor (
                            request_id, project_id, session_id, original_story, rewritten_story, 
                            applied_style, applied_perspective, duration_ms, token_count, style_intensity, 
                            original_content, chunk_num, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """,
                        (
                            self.request_id,  # Use the ULID request_id from the API
                            self.caller.project_id,
                            self.id,  # session_id
                            chunk.text,  # original_story
                            rewrite.rewritten_text,  # rewritten_story
                            json.dumps(rewrite.applied_style.dict()),
                            json.dumps(rewrite.applied_perspective.dict()),
                            rewrite.processing_time_ms,  # duration_ms
                            rewrite.token_count,
                            getattr(self.rewrite_config,
                                    'style_intensity', None),
                            chunk.text,  # original_content
                            chunk.chunk_num,
                        ),
                    )
                    conn.commit()
        except Exception as e:
            raise RuntimeError(
                f"Failed to store intermediate deconstructor: {str(e)}")

    def _store_rewrite_session(self, rewrites: list[RewrittenContent], started_at: str, total_time_ms: int) -> None:
        """
        Stores the complete rewrite session in the database.

        Args:
            rewrites (list[RewrittenContent]): List of all rewrite results.
            started_at (str): The start timestamp of the process.
            total_time_ms (int): The total processing time in milliseconds.
        """
        try:
            with self.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO deconstructor_sessions (id, user_id, workspace_id, project_id, 
                                                    author_style, writing_perspective, rewrite_config,
                                                    total_rewrites, started_at, total_time_ms, original_content, 
                                                    created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """,
                        (
                            self.id,
                            self.caller.user_id,
                            self.caller.workspace_id,
                            self.caller.project_id,
                            json.dumps(self.author_style.dict()),
                            json.dumps(self.writing_perspective.dict()),
                            json.dumps(self.rewrite_config.dict()),
                            len(rewrites),
                            started_at,
                            total_time_ms,
                            "\n".join(self.sources),
                        ),
                    )
                    conn.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to store rewrite session: {str(e)}")

    def _rewrite_chunk(self, chunk: ContentChunk) -> RewrittenContent:
        """
        Rewrites a single content chunk.

        Args:
            chunk (ContentChunk): The chunk to rewrite.

        Returns:
            RewrittenContent: The rewritten content.
        """
        start_time = time.monotonic()

        response = self._call_llm(chunk.text)

        processing_time_ms = int((time.monotonic() - start_time) * 1000)

        rewrite = RewrittenContent(
            original_text=chunk.text,
            rewritten_text=response.text,
            applied_style=self.author_style,
            applied_perspective=self.writing_perspective,
            processing_time_ms=processing_time_ms,
            token_count=response.metadata.output_tokens,
            style_confidence=0.8,  # This could be calculated based on response quality
        )

        self._store_intermediate_deconstructor(rewrite, chunk)
        return rewrite

    def run(self) -> list[RewrittenContent]:
        """
        Executes the content rewriting pipeline.

        Returns:
            list[RewrittenContent]: List of rewritten content chunks.
        """
        start_time = time.monotonic()
        start_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Extract and chunk the content
        chunks = self.construct_content_chunks()

        # Rewrite each chunk
        rewrites = [self._rewrite_chunk(chunk) for chunk in chunks]

        # Store the complete session
        total_time_ms = int((time.monotonic() - start_time) * 1000)
        self._store_rewrite_session(rewrites, start_at, total_time_ms)

        return rewrites
