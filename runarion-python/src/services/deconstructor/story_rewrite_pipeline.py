import time
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
    ):
        """
        Args:
            caller (CallerInfo): Caller information.
            connection_pool (SimpleConnectionPool): Database connection pool.
            provider (Optional[str]): The model provider.
            model (Optional[str]): The model name.
            generation_config (Optional[GenerationConfig]): Configuration for LLM generation.
        """
        self.caller = caller
        self.connection_pool = connection_pool
        self.provider = provider or "gemini"
        self.model = model or "gemini-2.0-flash"
        self.generation_config = generation_config or GenerationConfig()  # type: ignore

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

        print(f"Starting story rewrite pipeline (Session: {session_id})")

        # Step 1: Extract the rough draft content
        print("Step 1: Extracting rough draft content...")
        rough_draft_extractor = ParagraphExtractor(
            file_path=request.rough_draft_file,
            start_page=1,
            end_page=None,  # Process all pages
            min_char_len=150,
            max_char_len=3000,
        )

        rough_draft_paragraphs = rough_draft_extractor.run()
        original_story = "".join(rough_draft_paragraphs)
        rough_draft_extractor.clear()

        # Step 2: Handle author style (new or existing)
        print("Step 2: Processing author style...")
        author_style, author_style_id = self._handle_author_style(
            request.author_style_request, session_id
        )

        # Step 3: Rewrite the story
        print("Step 3: Rewriting story...")
        rewritten_content = self._rewrite_story(
            rough_draft_paragraphs,
            author_style,
            request.writing_perspective,
            request.rewrite_config,
            request.store_intermediate,
            request.chunk_overlap,
        )

        # Step 4: Combine results
        rewritten_story = "".join(
            [chunk.rewritten_text for chunk in rewritten_content])

        # Calculate metadata
        total_time_ms = int((time.monotonic() - start_time) * 1000)
        total_chunks = len(rewritten_content)
        total_original_chars = len(original_story)
        total_rewritten_chars = len(rewritten_story)
        total_tokens = sum(chunk.token_count for chunk in rewritten_content)
        average_confidence = (
            sum(chunk.style_confidence for chunk in rewritten_content) / total_chunks
            if total_chunks > 0 else 0.0
        )

        print(f"Pipeline completed in {total_time_ms}ms")

        return StoryRewriteResponse(
            original_story=original_story,
            rewritten_story=rewritten_story,
            author_style=author_style,
            total_chunks=total_chunks,
            total_original_chars=total_original_chars,
            total_rewritten_chars=total_rewritten_chars,
            total_tokens=total_tokens,
            processing_time_ms=total_time_ms,
            average_style_confidence=average_confidence,
            session_id=session_id,
            author_style_id=author_style_id,
        )

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
