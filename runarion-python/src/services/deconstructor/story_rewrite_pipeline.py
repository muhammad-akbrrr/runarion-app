import time
import json
from typing import Optional, Union
import logging
import re

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
from services.deconstructor.author_style_configuration.author_style_configuration import AuthorStyleConfiguration, Passage
from services.deconstructor.story_rewrite_configuration.story_rewrite_configuration import ContentRewritePipeline, ContentChunk
from services.deconstructor.utils.paragraph_extractor import ParagraphExtractor
from ulid import ULID
from services.deconstructor.utils.token_counter import TokenCounter
from utils.get_model_max_token import get_model_max_token
from services.usecase_handler.story_rewrite_handler import StoryStructureHandler
from services.generation_engine import GenerationEngine


def clean_unicode_characters(text: str) -> str:
    """
    Clean Unicode characters from text, converting smart quotes and other Unicode characters to ASCII equivalents.

    Args:
        text (str): The text to clean

    Returns:
        str: The cleaned text with ASCII characters
    """
    # Common Unicode to ASCII mappings
    unicode_mappings = {
        '\u2018': "'",  # Left single quotation mark
        '\u2019': "'",  # Right single quotation mark
        '\u201C': '"',  # Left double quotation mark
        '\u201D': '"',  # Right double quotation mark
        '\u2013': '-',  # En dash
        '\u2014': '--',  # Em dash
        '\u2026': '...',  # Horizontal ellipsis
        '\u00A0': ' ',  # Non-breaking space
        '\u00B0': '°',  # Degree sign
        '\u00AE': '(R)',  # Registered trademark
        '\u2122': '(TM)',  # Trademark
        '\u00A9': '(C)',  # Copyright
    }

    # Apply all mappings
    for unicode_char, ascii_char in unicode_mappings.items():
        text = text.replace(unicode_char, ascii_char)

    return text


class StoryRewritePipeline:
    """
    Main pipeline for story rewriting following the user workflow:
    1. Process user's rough draft PDF
    2. Handle author style selection (new or existing)
    3. Analyze draft structure (chapter breakdown)
    4. Rewrite the story by chapter using structured author style
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
        # Ensure max_output_tokens is at least 2000
        if not hasattr(self.generation_config, 'max_output_tokens') or self.generation_config.max_output_tokens < 2000:
            self.generation_config.max_output_tokens = 2000
        self.request_id = request_id

    def _set_processing_status(self):
        """
        Set the deconstructor_logs status to 'processing' when the pipeline starts.
        """
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE deconstructor_logs 
                    SET status = 'processing',
                        updated_at = NOW()
                    WHERE id = %s AND status = 'pending'
                    """,
                    (self.request_id,)
                )
            conn.commit()
        except Exception as e:
            logger = logging.getLogger("story_rewrite_pipeline")
            logger.error(f"[Pipeline] Failed to set processing status: {e}")
        finally:
            self.connection_pool.putconn(conn)

    def process_request(self, request: StoryRewriteRequest) -> StoryRewriteResponse:
        """
        Process a complete story rewrite request using the revamped three-stage pipeline.
        """
        logger = logging.getLogger("story_rewrite_pipeline")
        start_time = time.monotonic()
        session_id = str(ULID())
        logger.info(
            f"[Pipeline] Starting story rewrite pipeline (Session: {session_id})")

        # Set status to processing
        self._set_processing_status()

        try:
            # --- Stage 1: Chunk the draft ---
            logger.info("[Pipeline] Stage 1: Chunking the draft PDF...")
            rough_draft_extractor = ParagraphExtractor(
                file_path=request.rough_draft_file,
                start_page=1,
                end_page=None,
                min_char_len=20,
                max_char_len=3000,
            )
            # Debug: print PDF info
            try:
                import pymupdf
                doc = pymupdf.open(request.rough_draft_file)
                logger.info(f"[Pipeline] PDF has {doc.page_count} pages.")
                for i, page in enumerate(doc):
                    blocks = page.get_text("blocks")
                    logger.info(
                        f"[Pipeline] Page {i+1} has {len(blocks)} blocks.")
            except Exception as e:
                logger.warning(f"[Pipeline] Could not inspect PDF: {e}")
            draft_paragraphs = rough_draft_extractor.run().copy()
            logger.info(
                f"[Pipeline] Extracted {len(draft_paragraphs)} paragraphs from draft: {draft_paragraphs}")
            for idx, para in enumerate(draft_paragraphs):
                logger.info(
                    f"[Pipeline] Paragraph {idx+1} length: {len(para)} | Content: {para[:100]}...")
            rough_draft_extractor.clear()

            # Use chunking logic similar to AuthorStyleConfiguration.construct_passages
            RESERVED_TOKENS_FOR_SAFETY = 200
            token_counter = TokenCounter(self.provider, self.model)
            model_max_token = get_model_max_token(
                self.provider, self.model) - RESERVED_TOKENS_FOR_SAFETY
            estimated_prompt_tokens = 1000
            max_content_tokens = model_max_token - estimated_prompt_tokens
            logger.info(
                f"[Pipeline] model_max_token: {model_max_token}, estimated_prompt_tokens: {estimated_prompt_tokens}, max_content_tokens: {max_content_tokens}")

            passages = []
            chunk = []
            token_count = 0
            passage_num = 1
            logger.info(
                f"[Pipeline] Starting chunking loop with {len(draft_paragraphs)} paragraphs.")
            for i, paragraph in enumerate(draft_paragraphs):
                paragraph_token_count = token_counter.count_tokens(paragraph)
                logger.info(
                    f"[Pipeline] Paragraph {i+1} token count: {paragraph_token_count}")
                logger.info(
                    f"[Pipeline] Current chunk token count: {token_count}, chunk size: {len(chunk)}")
                if (token_count + paragraph_token_count) < max_content_tokens:
                    chunk.append(paragraph)
                    token_count += paragraph_token_count
                    logger.info(
                        f"[Pipeline] Added paragraph {i+1} to chunk. New chunk size: {len(chunk)}. New token count: {token_count}")
                else:
                    logger.info(
                        f"[Pipeline] Chunk full or paragraph too large. Finalizing chunk with {len(chunk)} paragraphs and {token_count} tokens.")
                    if chunk:
                        logger.info(
                            f"[Pipeline] Appending final passage with {len(chunk)} paragraphs.")
                        logger.info(f"[Pipeline] Chunk content: {chunk}")
                        try:
                            passages.append(Passage("rough_draft.pdf",
                                            passage_num, "".join(chunk)))
                        except Exception as e:
                            logger.error(
                                f"[Pipeline] Failed to create final passage: {e}")
                    else:
                        logger.warning(
                            f"[Pipeline] Chunk was empty when trying to finalize.")
                    chunk = [paragraph]
                    token_count = paragraph_token_count
                    passage_num += 1
            if chunk:
                logger.info(
                    f"[Pipeline] Final chunk length (after loop): {len(chunk)}")
                logger.info(
                    f"[Pipeline] Appending final passage with {len(chunk)} paragraphs (after loop).")
                logger.info(f"[Pipeline] Chunk content (after loop): {chunk}")
                try:
                    passages.append(Passage("rough_draft.pdf",
                                    passage_num, "".join(chunk)))
                except Exception as e:
                    logger.error(
                        f"[Pipeline] Failed to create final passage (after loop): {e}")
            else:
                logger.info(
                    f"[Pipeline] No remaining chunk to append after loop.")
            logger.info(
                f"[Pipeline] After chunking: passages={len(passages)}, chunk={len(chunk)}, draft_paragraphs={len(draft_paragraphs)}")
            if len(passages) == 0:
                logger.warning(
                    f"[Pipeline] No passages were created. Possible reasons: draft_paragraphs was empty (len={len(draft_paragraphs)}), or chunking logic did not add any passages. chunk at end: {chunk}")
            logger.info(f"[Pipeline] Chunked into {len(passages)} passages.")

            # Save each chunk in intermediate_deconstructor (original, not rewritten yet)
            for idx, passage in enumerate(passages):
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT INTO intermediate_deconstructor (
                                request_id, project_id, session_id, original_story, rewritten_story, 
                                applied_style, applied_perspective, duration_ms, token_count, style_intensity, 
                                original_content, chunk_num, created_at, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                            """,
                            (
                                self.request_id,
                                self.caller.project_id,
                                session_id,
                                passage.text,
                                None,
                                None,
                                json.dumps(
                                    request.writing_perspective.dict()),
                                None,
                                token_counter.count_tokens(passage.text),
                                None,
                                passage.text,
                                idx + 1,
                            )
                        )
                    conn.commit()
                except Exception as e:
                    logger.error(
                        f"[Pipeline] Failed to save intermediate chunk {idx+1}: {e}")
                finally:
                    self.connection_pool.putconn(conn)

            # --- Stage 2: Analyze draft structure (chapter breakdown) ---
            logger.info(
                "[Pipeline] Stage 2: Analyzing draft structure (chapter breakdown)...")
            structure_input_text = "\n".join([p.text for p in passages])
            if not structure_input_text.strip():
                logger.warning(
                    "[Pipeline] No content for chapter breakdown. Skipping LLM call and using default chapter.")
                chapter_breakdown = [
                    {
                        "chapter_name": "Chapter 1",
                        "summary": "Full story as one chapter.",
                        "plot_points": [],
                        "start_idx": 0,
                        "end_idx": len(passages) - 1,
                    }
                ]
            else:
                structure_handler = StoryStructureHandler()
                structure_request = {
                    "mode": "structure",
                    "provider": self.provider,
                    "model": self.model,
                    "text": structure_input_text,
                    "generation_config": self.generation_config,
                    "caller": self.caller,
                }
                structure_gen_request = structure_handler.build_request(
                    structure_request)
                structure_engine = GenerationEngine(structure_gen_request)
                try:
                    structure_response = structure_engine.generate()
                    import re
                    structure_response_text = clean_unicode_characters(
                        structure_response.text.strip())
                    logger.info(
                        f"[Pipeline] LLM structure response: {structure_response_text!r}")

                    # Remove markdown code fencing if present
                    if structure_response_text.startswith("```"):
                        structure_response_text = re.sub(
                            r"^```[a-zA-Z]*\\n?", "", structure_response_text)
                        structure_response_text = re.sub(
                            r"```$", "", structure_response_text).strip()

                    try:
                        chapter_breakdown = json.loads(structure_response_text)
                        logger.info(
                            f"[Pipeline] Successfully parsed chapter breakdown as JSON.")
                    except Exception as e1:
                        logger.error(
                            f"[Pipeline] JSON parsing failed: {e1}. Attempting to extract JSON array from response.")
                        # Try to extract JSON array from within the response
                        start_index = structure_response_text.find("[")
                        end_index = structure_response_text.rfind("]")
                        if start_index != -1 and end_index != -1 and start_index < end_index:
                            clean_text = structure_response_text[start_index:end_index+1]
                            try:
                                import demjson3
                                chapter_breakdown = demjson3.decode(clean_text)
                                logger.info(
                                    f"[Pipeline] Successfully parsed chapter breakdown using demjson3.")
                            except Exception as e2:
                                logger.error(
                                    f"[Pipeline] demjson3 parsing also failed: {e2}. Raw response: {structure_response_text!r}")
                                raise
                        else:
                            logger.error(
                                f"[Pipeline] No valid JSON array found in LLM response. Raw response: {structure_response_text!r}")
                            raise
                except Exception as e:
                    logger.error(
                        f"[Pipeline] ERROR: Failed to analyze chapter structure or parse JSON: {e}")
                    # Fallback: single chapter for all content
                    chapter_breakdown = [
                        {
                            "chapter_name": "Chapter 1",
                            "summary": "Full story as one chapter.",
                            "plot_points": [],
                            "start_idx": 0,
                            "end_idx": len(passages) - 1,
                        }
                    ]

            # Validate chapter indices do not exceed paragraph count
            num_paragraphs = len(draft_paragraphs)
            validated_chapter_breakdown = []
            for chapter in chapter_breakdown:
                orig_start = chapter.get("start_idx", 0)
                orig_end = chapter.get("end_idx", 0)
                start_idx = max(0, min(orig_start, num_paragraphs - 1))
                end_idx = max(0, min(orig_end, num_paragraphs - 1))
                if start_idx > end_idx:
                    logger.warning(
                        f"[Pipeline] Chapter '{chapter.get('chapter_name', '?')}' has start_idx > end_idx after validation: start_idx={start_idx}, end_idx={end_idx}. Skipping.")
                    continue
                if orig_start != start_idx or orig_end != end_idx:
                    logger.warning(
                        f"[Pipeline] Corrected chapter indices for '{chapter.get('chapter_name', '?')}': start_idx {orig_start}->{start_idx}, end_idx {orig_end}->{end_idx}")
                chapter["start_idx"] = start_idx
                chapter["end_idx"] = end_idx
                validated_chapter_breakdown.append(chapter)
            chapter_breakdown = validated_chapter_breakdown

            # --- Stage 3: Rewrite by chapter using structured author style ---
            logger.info(
                "[Pipeline] Stage 3: Rewriting by chapter using structured author style...")
            if hasattr(request.author_style_request, 'author_style_id'):
                # Existing style: fetch from DB
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT style FROM structured_author_styles WHERE id = %s",
                            (request.author_style_request.author_style_id,)
                        )
                        result = cursor.fetchone()
                        if not result:
                            raise ValueError(
                                f"Author style with ID {request.author_style_request.author_style_id} not found")
                        author_style_json = result[0]
                except Exception as e:
                    logger.error(
                        f"[Pipeline] Failed to fetch existing author style: {e}")
                    raise
            else:
                # New style: assume it was just created and available as a dict
                author_style_json = request.author_style_request.dict() if hasattr(
                    request.author_style_request, 'dict') else {}

            # Ensure author_style_json is always a dict for downstream use
            import json as _json

            def ensure_dict(val):
                if isinstance(val, dict):
                    return val
                try:
                    return _json.loads(val)
                except Exception:
                    logger.error(
                        f"[Pipeline] Could not parse author_style_json as JSON: {val}")
                    raise
            author_style_json = ensure_dict(author_style_json)

            # Convert author_style_json to AuthorStyle object if needed
            from models.deconstructor.author_style import AuthorStyle
            logger.info(
                f"[Pipeline] author_style_json raw value: {repr(author_style_json)} (type: {type(author_style_json)})")
            try:
                logger.info(
                    f"[Pipeline] Parsing author_style_json as dict: keys={list(author_style_json.keys())}")
                author_style_obj = AuthorStyle(**author_style_json)
                logger.info(
                    f"[Pipeline] Successfully parsed author_style_obj: {author_style_obj}")
            except Exception as e:
                logger.error(
                    f"[Pipeline] Failed to parse author style JSON: {e}. author_style_json value: {repr(author_style_json)} (type: {type(author_style_json)})")
                raise

            rewritten_chapters = []
            rewritten_story = ""
            num_paragraphs = len(draft_paragraphs)
            for chapter_idx, chapter in enumerate(chapter_breakdown):
                start_idx = chapter.get("start_idx", 0)
                end_idx = chapter.get("end_idx", 0)
                # Bounds checking
                if not (0 <= start_idx <= end_idx < num_paragraphs):
                    logger.warning(
                        f"[Pipeline] Chapter '{chapter.get('chapter_name', '?')}' has invalid indices: start_idx={start_idx}, end_idx={end_idx}, num_paragraphs={num_paragraphs}. Skipping.")
                    continue
                chapter_paragraphs = draft_paragraphs[start_idx:end_idx+1]

                class MemoryParagraphExtractor:
                    def __init__(self, paragraphs):
                        self.paragraphs = paragraphs
                        self.file_path = "memory_chapter"

                    def run(self):
                        return self.paragraphs.copy()

                    def clear(self):
                        pass
                memory_extractor = MemoryParagraphExtractor(chapter_paragraphs)
                from services.deconstructor.story_rewrite_configuration.story_rewrite_configuration import ContentRewritePipeline
                try:
                    rewrite_pipeline = ContentRewritePipeline(
                        paragraph_extractors=[memory_extractor],
                        author_style=author_style_obj,
                        writing_perspective=request.writing_perspective,
                        caller=self.caller,
                        connection_pool=self.connection_pool,
                        provider=self.provider,
                        model=self.model,
                        generation_config=self.generation_config,
                        rewrite_config=request.rewrite_config,
                        chunk_overlap=False,
                        store_intermediate=True,
                        request_id=self.request_id,
                    )
                    chapter_rewrites = rewrite_pipeline.run()
                    chapter_text = "".join(
                        [c.rewritten_text for c in chapter_rewrites])
                    # Clean Unicode characters from the generated text
                    chapter_text = clean_unicode_characters(chapter_text)
                except Exception as e:
                    logger.error(
                        f"[Pipeline] Failed to rewrite chapter '{chapter.get('chapter_name', '?')}': {e}")
                    chapter_text = "[ERROR: Failed to rewrite chapter]"
                rewritten_chapters.append({
                    "order": chapter_idx,  # Auto-increment from 0
                    "chapter_name": chapter.get("chapter_name", "Chapter"),
                    "content": chapter_text,
                    "summary": chapter.get("summary", ""),
                    "plot_points": chapter.get("plot_points", []),
                })
                rewritten_story += chapter_text + "\n"

            total_time_ms = int((time.monotonic() - start_time) * 1000)
            logger.info(f"[Pipeline] Completed in {total_time_ms} ms.")

            # Prepare metadata for storage
            metadata = {
                "original_story": "".join([p.text for p in passages]),
                "rewritten_story": rewritten_story,
                "author_style": author_style_json,
                "total_chunks": len(passages),
                "total_original_chars": sum(len(p.text) for p in passages),
                "total_rewritten_chars": len(rewritten_story),
                "total_tokens": sum(token_counter.count_tokens(p.text) for p in passages),
                "chapters": rewritten_chapters,
            }

            # Update deconstructor_logs with completion status
            logger.info(
                f"[Pipeline] Updating deconstructor_logs with completion status")
            self._update_deconstructor_log(
                session_id, total_time_ms, True, None, metadata)

            # Insert deconstructor_response record
            author_style_id = getattr(
                request.author_style_request, 'author_style_id', None)
            logger.info(
                f"[Pipeline] Inserting deconstructor_response record with request_id: {self.request_id}")
            self._insert_deconstructor_response(
                request_id=self.request_id,
                session_id=session_id,
                author_style_id=author_style_id,
                project_id=self.caller.project_id,
                original_story="".join([p.text for p in passages]),
                rewritten_story=rewritten_story,
                metadata=metadata
            )

            # Update project_content with the rewritten chapters
            project_metadata = {
                "total_words": len(rewritten_story.split()),
                "total_chapters": len(rewritten_chapters),
                "average_words_per_chapter": len(rewritten_story.split()) / max(len(rewritten_chapters), 1),
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "last_modified": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "deconstructor_session_id": session_id,
                "author_style_id": author_style_id,
            }

            # Convert user_id to integer for database storage
            try:
                last_edited_by = int(
                    self.caller.user_id) if self.caller.user_id and self.caller.user_id != 'default_user' else None
            except (ValueError, TypeError):
                logger.warning(
                    f"[Pipeline] Invalid user_id format: {self.caller.user_id}, setting to None")
                last_edited_by = None

            logger.info(
                f"[Pipeline] Updating project_content with {len(rewritten_chapters)} chapters")
            self._insert_project_content(
                project_id=self.caller.project_id,
                last_edited_by=last_edited_by,
                chapters=rewritten_chapters,
                metadata=project_metadata
            )

            return {
                "original_story": "".join([p.text for p in passages]),
                "rewritten_story": rewritten_story,
                "author_style": author_style_json,
                "total_chunks": len(passages),
                "total_original_chars": sum(len(p.text) for p in passages),
                "total_rewritten_chars": len(rewritten_story),
                "total_tokens": sum(token_counter.count_tokens(p.text) for p in passages),
                "processing_time_ms": total_time_ms,
                "average_style_confidence": 0.0,  # TODO: calculate if needed
                "session_id": session_id,
                "author_style_id": author_style_id,
                "chapters": rewritten_chapters,
            }
        except Exception as e:
            logger.error(f"[Pipeline] Unhandled error: {e}")
            # Calculate time even if we don't have all variables
            elapsed_time = int((time.monotonic() - start_time) * 1000)

            # Safely get metadata with fallbacks
            metadata = {}
            try:
                if 'passages' in locals():
                    metadata["total_chunks"] = len(passages)
                    metadata["total_original_chars"] = sum(
                        len(p.text) for p in passages)
                    metadata["total_tokens"] = sum(
                        token_counter.count_tokens(p.text) for p in passages)
                if 'rewritten_story' in locals():
                    metadata["total_rewritten_chars"] = len(rewritten_story)
                if 'author_style_json' in locals():
                    metadata["author_style"] = author_style_json
                if 'rewritten_chapters' in locals():
                    metadata["chapters"] = rewritten_chapters
            except Exception as meta_error:
                logger.error(
                    f"[Pipeline] Failed to build metadata: {meta_error}")

            self._update_deconstructor_log(
                session_id, elapsed_time, False, str(e), metadata)
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

        conn = self.connection_pool.getconn()
        try:
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
        finally:
            self.connection_pool.putconn(conn)

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
        conn = self.connection_pool.getconn()
        try:
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
        finally:
            self.connection_pool.putconn(conn)

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
                "content": clean_unicode_characters(rewritten_content[0].rewritten_text),
            }]
        chapters = []
        for idx, chunk in enumerate(rewritten_content):
            chapters.append({
                "order": idx,  # Auto-increment from 0
                "chapter_name": f"Chapter {idx+1}",
                "content": clean_unicode_characters(chunk.rewritten_text),
            })
        return chapters

    def _insert_deconstructor_response(self, request_id, session_id, author_style_id, project_id, original_story, rewritten_story, metadata):
        logger = logging.getLogger("story_rewrite_pipeline")
        logger.info(
            f"[Pipeline] Attempting to insert deconstructor_response with request_id: {request_id}")
        conn = self.connection_pool.getconn()
        try:
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
            logger.info(
                f"[Pipeline] Successfully inserted deconstructor_response")
        except Exception as e:
            logger.error(
                f"[Pipeline] Failed to insert deconstructor_response: {str(e)}")
        finally:
            self.connection_pool.putconn(conn)

    def _insert_project_content(self, project_id, last_edited_by, chapters, metadata):
        logger = logging.getLogger("story_rewrite_pipeline")
        logger.info(
            f"[Pipeline] Attempting to insert/update project_content for project_id: {project_id}")
        conn = self.connection_pool.getconn()
        try:
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
                # Update onboarding status in projects table
                cursor.execute(
                    """
                    UPDATE projects
                    SET completed_onboarding = TRUE,
                        updated_at = NOW()
                    WHERE id = %s AND completed_onboarding = FALSE
                    """,
                    (project_id,)
                )
            conn.commit()
            logger.info(
                f"[Pipeline] Successfully inserted/updated project_content")
        except Exception as e:
            logger.error(
                f"[Pipeline] Failed to insert project_content: {str(e)}")
        finally:
            self.connection_pool.putconn(conn)

    def _update_deconstructor_log(self, session_id: str, total_time_ms: int, success: bool = True, error_message: str = None, metadata: dict = None):
        """
        Update the deconstructor_logs table with completion status and metadata.

        Args:
            session_id (str): Session ID for tracking.
            total_time_ms (int): Total processing time in milliseconds.
            success (bool): Whether the processing was successful.
            error_message (str): Error message if processing failed.
            metadata (dict): Additional metadata to store.
        """
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE deconstructor_logs 
                    SET completed_at = NOW(),
                        duration_ms = %s,
                        status = %s,
                        error_message = %s,
                        response_metadata = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        total_time_ms,
                        'completed' if success else 'failed',
                        error_message,
                        json.dumps(metadata) if metadata else None,
                        self.request_id,
                    )
                )
            conn.commit()
        except Exception as e:
            logger = logging.getLogger("story_rewrite_pipeline")
            logger.error(f"[Pipeline] Failed to update deconstructor_log: {e}")
        finally:
            self.connection_pool.putconn(conn)
