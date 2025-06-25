import time
import json
from typing import Optional, Union

from models.deconstructor.author_style import AuthorStyle
from models.deconstructor.story_rewrite import (
    ContentRewriteConfig,
    RewrittenContent,
    WritingPerspective,
    StoryRewriteRequest,
    StoryRewriteResponse,
    NewAuthorStyleRequest,
    ExistingAuthorStyleRequest
)
from models.request import CallerInfo, GenerationConfig
from psycopg2.pool import SimpleConnectionPool
from services.deconstructor.author_style_configuration.author_style_configuration import AuthorStyleConfiguration
from services.deconstructor.story_rewrite_configuration.story_rewrite_configuration import ContentRewritePipeline
from services.deconstructor.utils.paragraph_extractor import ParagraphExtractor
from ulid import ULID


class StoryRewritePipeline:
    """
    Main pipeline for story rewriting following the user workflow:
    1. Process user's rough draft PDF
    2. Handle author style selection (new or existing)
    3. Apply writing perspective
    4. Rewrite the story
    """

    def __init__(
        self,
        caller: CallerInfo,
        connection_pool: SimpleConnectionPool,
        provider: Optional[str] = "gemini",
        model: Optional[str] = None,
        generation_config: Optional[GenerationConfig] = None,
        request_id: Optional[str] = None,
    ):
        """
        Args:
            caller (CallerInfo): Caller information.
            connection_pool (SimpleConnectionPool): Database connection pool.
            provider (Optional[str]): The model provider.
            model (Optional[str]): The model name.
            generation_config (Optional[GenerationConfig]): Configuration for LLM generation.
            request_id (Optional[str]): Request ID for tracking.
        """
        self.caller = caller
        self.connection_pool = connection_pool
        self.provider = provider or "gemini"
        self.model = model or "gemini-2.0-flash"
        self.generation_config = generation_config or GenerationConfig()  # type: ignore
        self.request_id = request_id

    def process_request(self, request: StoryRewriteRequest) -> StoryRewriteResponse:
        """
        Process a complete story rewrite request.

        Args:
            request (StoryRewriteRequest): The complete rewrite request.

        Returns:
            StoryRewriteResponse: The rewritten story and metadata.
        """
        start_time = time.monotonic()
        session_id = str(ULID())

        try:
            print(
                f"[Pipeline] Starting story rewrite pipeline (Session: {session_id})")

            # Step 1: Extract the rough draft content
            print("[Pipeline] Step 1: Extracting rough draft content...")
            rough_draft_extractor = ParagraphExtractor(
                file_path=request.rough_draft_file,
                start_page=1,
                end_page=None,  # Process all pages
                min_char_len=150,
                max_char_len=3000,
            )

            rough_draft_paragraphs = rough_draft_extractor.run()
            print(
                f"[Pipeline] Extracted {len(rough_draft_paragraphs)} paragraphs from rough draft.")
            original_story = "".join(rough_draft_paragraphs)
            rough_draft_extractor.clear()

            # Step 2: Handle author style (new or existing)
            print("[Pipeline] Step 2: Processing author style...")
            author_style, author_style_id = self._handle_author_style(
                request.author_style_request, session_id
            )
            print(f"[Pipeline] Author style ID: {author_style_id}")

            # Step 3: Rewrite the story
            print("[Pipeline] Step 3: Rewriting story...")
            rewritten_content = self._rewrite_story(
                rough_draft_paragraphs,
                author_style,
                request.writing_perspective,
                request.rewrite_config,
                request.store_intermediate,
                request.chunk_overlap,
            )
            print(
                f"[Pipeline] Rewritten content chunks: {len(rewritten_content)}")

            # Step 4: Combine results
            rewritten_story = "".join(
                [chunk.rewritten_text for chunk in rewritten_content])

            # Format as chapters for project_content
            chapters = self._format_chapters(rewritten_content)

            # Calculate metadata
            total_time_ms = int((time.monotonic() - start_time) * 1000)
            total_chunks = len(rewritten_content)
            total_original_chars = len(original_story)
            total_rewritten_chars = len(rewritten_story)
            total_tokens = sum(
                chunk.token_count for chunk in rewritten_content)
            average_confidence = (
                sum(chunk.style_confidence for chunk in rewritten_content) / total_chunks
                if total_chunks > 0 else 0.0
            )

            print(f"[Pipeline] Pipeline completed in {total_time_ms}ms")

            # Update deconstructor_logs as completed
            try:
                with self.connection_pool.getconn() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            UPDATE deconstructor_logs
                            SET completed_at = NOW(),
                                duration_ms = %s,
                                response_metadata = %s,
                                status = 'completed'
                            WHERE id = %s
                            """,
                            (
                                total_time_ms,
                                json.dumps({
                                    "total_chunks": total_chunks,
                                    "total_original_chars": total_original_chars,
                                    "total_rewritten_chars": total_rewritten_chars,
                                    "total_tokens": total_tokens,
                                    "processing_time_ms": total_time_ms,
                                    "average_style_confidence": average_confidence,
                                }),
                                self.request_id,
                            )
                        )
                        conn.commit()
            except Exception as e:
                print(
                    f"[Pipeline] Warning: Failed to update deconstructor_logs: {str(e)}")

            # Insert into deconstructor_responses
            self._insert_deconstructor_response(
                request_id=self.request_id,
                session_id=session_id,
                author_style_id=author_style_id,
                project_id=self.caller.project_id,
                original_story=original_story,
                rewritten_story=rewritten_story,
                metadata={
                    "total_chunks": total_chunks,
                    "total_original_chars": total_original_chars,
                    "total_rewritten_chars": total_rewritten_chars,
                    "total_tokens": total_tokens,
                    "processing_time_ms": total_time_ms,
                    "average_style_confidence": average_confidence,
                }
            )

            # Insert into project_content
            self._insert_project_content(
                project_id=self.caller.project_id,
                last_edited_by=self.caller.user_id,
                chapters=chapters,
                metadata={
                    "total_chunks": total_chunks,
                    "total_original_chars": total_original_chars,
                    "total_rewritten_chars": total_rewritten_chars,
                    "total_tokens": total_tokens,
                    "processing_time_ms": total_time_ms,
                    "average_style_confidence": average_confidence,
                }
            )

            print(f"[Pipeline] Returning response for session {session_id}")
            return {
                "original_story": original_story,
                "rewritten_story": rewritten_story,
                "author_style": author_style,
                "total_chunks": total_chunks,
                "total_original_chars": total_original_chars,
                "total_rewritten_chars": total_rewritten_chars,
                "total_tokens": total_tokens,
                "processing_time_ms": total_time_ms,
                "average_style_confidence": average_confidence,
                "session_id": session_id,
                "author_style_id": author_style_id,
                "chapters": chapters,
            }
        except Exception as e:
            print(f"[Pipeline] ERROR: {type(e).__name__}: {e}")
            # On error, update deconstructor_logs as failed
            try:
                with self.connection_pool.getconn() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            UPDATE deconstructor_logs
                            SET completed_at = NOW(),
                                status = 'failed',
                                error_message = %s
                            WHERE id = %s
                            """,
                            (str(e), self.request_id)
                        )
                        conn.commit()
            except Exception as log_e:
                print(
                    f"[Pipeline] Warning: Failed to update deconstructor_logs on error: {str(log_e)}")
            raise

    def _handle_author_style(
        self,
        author_style_request: Union[NewAuthorStyleRequest, ExistingAuthorStyleRequest],
        session_id: str
    ) -> tuple[AuthorStyle, str]:
        """
        Handle author style selection (new or existing).

        Args:
            author_style_request: Either new or existing author style request.
            session_id: Session ID for tracking.

        Returns:
            tuple[AuthorStyle, str]: The author style and its ID.
        """
        if isinstance(author_style_request, NewAuthorStyleRequest):
            return self._create_new_author_style(author_style_request, session_id)
        else:
            return self._get_existing_author_style(author_style_request.author_style_id)

    def _create_new_author_style(
        self,
        request: NewAuthorStyleRequest,
        session_id: str
    ) -> tuple[AuthorStyle, str]:
        """
        Create a new author style from uploaded samples.

        Args:
            request (NewAuthorStyleRequest): Request with sample files.
            session_id (str): Session ID for tracking.

        Returns:
            tuple[AuthorStyle, str]: The new author style and its ID.
        """
        print(
            f"Creating new author style from {len(request.sample_files)} sample files...")

        # Create paragraph extractors for each sample file
        style_extractors = []
        for file_path in request.sample_files:
            extractor = ParagraphExtractor(
                file_path=file_path,
                start_page=1,
                end_page=None,  # Process all pages
                min_char_len=150,
                max_char_len=3000,
            )
            style_extractors.append(extractor)

        # Analyze the author style
        style_config = AuthorStyleConfiguration(
            paragraph_extractors=style_extractors,
            caller=self.caller,
            connection_pool=self.connection_pool,
            author_name=request.author_name,
            provider=self.provider,
            model=self.model,
            generation_config=self.generation_config,
            store_intermediate=True,
        )

        author_style = style_config.run()
        author_style_id = style_config.id

        # Store additional metadata if author name is provided
        if request.author_name:
            self._store_author_metadata(author_style_id, request.author_name)

        print(f"Author style created with ID: {author_style_id}")
        return author_style, author_style_id

    def _get_existing_author_style(self, author_style_id: str) -> tuple[AuthorStyle, str]:
        """
        Retrieve an existing author style from the database.

        Args:
            author_style_id (str): ID of the existing author style.

        Returns:
            tuple[AuthorStyle, str]: The author style and its ID.
        """
        print(f"Retrieving existing author style: {author_style_id}")

        try:
            with self.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT style FROM structured_author_styles 
                        WHERE id = %s
                        """,
                        (author_style_id,)
                    )
                    result = cursor.fetchone()

                    if not result:
                        raise ValueError(
                            f"Author style with ID {author_style_id} not found")

                    style_data = result[0]
                    author_style = AuthorStyle(**style_data)

                    return author_style, author_style_id

        except Exception as e:
            raise RuntimeError(f"Failed to retrieve author style: {str(e)}")

    def _rewrite_story(
        self,
        rough_draft_paragraphs: list[str],
        author_style: AuthorStyle,
        writing_perspective: WritingPerspective,
        rewrite_config: Optional[ContentRewriteConfig] = None,
        store_intermediate: bool = False,
        chunk_overlap: bool = False,
    ) -> list[RewrittenContent]:
        """
        Rewrite the story in the specified author style and perspective.

        Args:
            rough_draft_paragraphs (list[str]): Original story paragraphs.
            author_style (AuthorStyle): Author style to apply.
            writing_perspective (WritingPerspective): Writing perspective to use.
            rewrite_config (Optional[ContentRewriteConfig]): Additional configuration.
            store_intermediate (bool): Whether to store intermediate results.
            chunk_overlap (bool): Whether to allow chunk overlap.

        Returns:
            list[RewrittenContent]: List of rewritten content chunks.
        """
        # Create rewrite_config if not provided
        if rewrite_config is None:
            rewrite_config = ContentRewriteConfig(
                author_style=author_style,
                writing_perspective=writing_perspective
            )

        # Create a temporary file-like extractor for the rough draft
        # This is a workaround since we already have the paragraphs
        class MemoryParagraphExtractor:
            def __init__(self, paragraphs: list[str]):
                self.paragraphs = paragraphs
                self.file_path = "memory_rough_draft"

            def run(self) -> list[str]:
                return self.paragraphs.copy()

            def clear(self):
                pass

        memory_extractor = MemoryParagraphExtractor(rough_draft_paragraphs)

        # Create the rewrite pipeline
        rewrite_pipeline = ContentRewritePipeline(
            paragraph_extractors=[memory_extractor],
            author_style=author_style,
            writing_perspective=writing_perspective,
            caller=self.caller,
            connection_pool=self.connection_pool,
            provider=self.provider,
            model=self.model,
            generation_config=self.generation_config,
            rewrite_config=rewrite_config,
            chunk_overlap=chunk_overlap,
            store_intermediate=store_intermediate,
            request_id=self.request_id,
        )

        return rewrite_pipeline.run()

    def _store_author_metadata(self, author_style_id: str, author_name: str) -> None:
        """
        Store additional metadata about the author.

        Args:
            author_style_id (str): ID of the author style.
            author_name (str): Name of the author.
        """
        try:
            with self.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE structured_author_styles 
                        SET author_name = %s 
                        WHERE id = %s
                        """,
                        (author_name, author_style_id)
                    )
                    conn.commit()
        except Exception as e:
            print(f"Warning: Failed to store author metadata: {str(e)}")
            # Don't fail the entire pipeline for this

    def _format_chapters(self, rewritten_content):
        """
        Format the rewritten content as an array of chapters for project_content.
        If there are multiple chunks, each is a chapter; otherwise, treat the whole as one chapter.
        """
        if not rewritten_content:
            return []
        if len(rewritten_content) == 1:
            return [{
                "order": 0,
                "chapter_name": "Chapter 1",
                "content": rewritten_content[0].rewritten_text,
            }]
        chapters = []
        for idx, chunk in enumerate(rewritten_content):
            chapters.append({
                "order": idx,
                "chapter_name": f"Chapter {idx+1}",
                "content": chunk.rewritten_text,
            })
        return chapters

    def _insert_deconstructor_response(self, request_id, session_id, author_style_id, project_id, original_story, rewritten_story, metadata):
        try:
            with self.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO deconstructor_responses (
                            request_id, session_id, author_style_id, project_id, original_story, rewritten_story, metadata, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (request_id) DO NOTHING
                        """,
                        (
                            request_id,
                            session_id,
                            author_style_id,
                            project_id,
                            original_story,
                            rewritten_story,
                            json.dumps(metadata),
                        )
                    )
                    conn.commit()
        except Exception as e:
            print(
                f"Warning: Failed to insert deconstructor_response: {str(e)}")

    def _insert_project_content(self, project_id, last_edited_by, chapters, metadata):
        try:
            with self.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO project_content (
                            id, project_id, last_edited_by, content, metadata, last_edited_at, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), NOW())
                        ON CONFLICT (project_id) DO UPDATE SET
                            last_edited_by = EXCLUDED.last_edited_by,
                            content = EXCLUDED.content,
                            metadata = EXCLUDED.metadata,
                            last_edited_at = NOW(),
                            updated_at = NOW()
                        """,
                        (
                            str(ULID()),
                            project_id,
                            last_edited_by,
                            json.dumps(chapters),
                            json.dumps(metadata),
                        )
                    )
                    conn.commit()
        except Exception as e:
            print(f"Warning: Failed to insert project_content: {str(e)}")
