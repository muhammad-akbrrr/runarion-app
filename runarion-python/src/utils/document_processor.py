import logging
import re
from pathlib import Path
from typing import List, Literal, Optional, Tuple, TypedDict, overload

import tiktoken

from .document_reader import DocumentReader
from .get_model_max_token import (
    get_safe_model_max_tokens,
)
from .token_counter import (
    CHARS_PER_TOKEN_ESTIMATE,
    TokenCounter,
)

logger = logging.getLogger(__name__)


class Chunk(TypedDict):
    chunk_number: int
    raw_text: str
    token_count: int
    character_count: int


class ChunkWithStart(Chunk):
    start: int


class ProcessedDocumentMetadata(TypedDict):
    file_path: str
    file_size: int
    original_length: int
    cleaned_length: int
    chunk_count: int
    total_tokens: int
    processing_model: str


class ProcessedDocument(TypedDict):
    status: Literal["success"]
    raw_text: str
    cleaned_text: str
    chunks: List[Chunk]
    metadata: ProcessedDocumentMetadata


class FailedProcessedDocument(TypedDict):
    status: Literal["failed"]
    error: str
    file_path: str


class DocumentProcessor:
    """
    Handles document extraction and chunking for the novel pipeline.
    """

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o",
        safety_margin: float | int = 0.5,
        max_chunk_size: Optional[int] = None,
        paragraph_priority: bool = True,
        sentence_overlap: int = 0,
        token_overlap: int = 50,
    ):
        """
        Initialize the document processor with configuration options.

        Args:
            provider: LLM provider for token counting and limits
            model: LLM model for token counting and limits
            safety_margin: Portion of tokens to reserve, int means number of tokens, float means ratio of model max tokens
            max_chunk_size: Maximum token size for each chunk, if None or too big uses conservative limit based on model max tokens and safety margin
            paragraph_priority: Whether to prioritize paragraph boundaries in chunking
            sentence_overlap: Number of sentences to overlap between chunks, used when paragraph_priority is True
            token_overlap: Number of tokens to overlap between chunks, used when paragraph_priority is False
        """
        self.document_reader = DocumentReader(paragraph_priority)

        self._provider = provider
        self._model = model

        self.token_counter = TokenCounter(
            provider=provider,
            model=model,
        )

        try:
            conservative_limit = get_safe_model_max_tokens(
                provider, model, safety_margin=safety_margin
            )
        except Exception as e:
            logger.warning(
                f"Failed to get conservative max token limit for {provider}/{model}: {e}."
            )
            conservative_limit = None
        if max_chunk_size is None:
            if conservative_limit is None:
                self.max_chunk_size = 4000
            else:
                self.max_chunk_size = conservative_limit
        else:
            if conservative_limit is None:
                self.max_chunk_size = max_chunk_size
            else:
                self.max_chunk_size = min(max_chunk_size, conservative_limit)

        self.paragraph_priority = paragraph_priority
        self.sentence_overlap = sentence_overlap
        self.token_overlap = token_overlap

    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
    ) -> List[Chunk]:
        """
        Split text into chunks suitable for AI processing using proper tokenizers.

        Args:
            text: Text to chunk
            chunk_size: Override default max chunk size

        Returns:
            List of chunk dictionaries with metadata
        """
        if not text.strip():
            return []

        if chunk_size is None:
            chunk_size = self.max_chunk_size

        # Use enhanced semantic boundary chunking
        if self.paragraph_priority:
            try:
                return self._chunk_by_semantic_boundaries(text, chunk_size)
            except Exception as e:
                logger.warning(
                    f"Semantic boundary chunking failed, falling back to tokenizer-based: {e}"
                )

        # Use proper tokenizer-based chunking as fallback
        try:
            text_chunks = self._safe_chunk_by_tokens(text, chunk_size)

            chunks = []
            for i, text_chunk in enumerate(text_chunks, 1):
                # Get accurate token count for the chunk
                actual_token_count = self.token_counter.safe_count(text_chunk)

                chunks.append(
                    self._create_chunk_dict(i, text_chunk, actual_token_count)
                )

            logger.info(
                f"Split text into {len(chunks)} chunks using tokenizer, total tokens: {sum(c['token_count'] for c in chunks)}"
            )
            return chunks

        except Exception as e:
            logger.warning(
                f"Tokenizer-based chunking failed, falling back to sentence-based: {e}"
            )
            return self._sentence_based_chunking(text, chunk_size)

    def _chunk_by_semantic_boundaries(self, text: str, chunk_size: int) -> List[Chunk]:
        """
        Chunk text using hierarchical semantic boundaries: paragraphs > sentences > words.

        Args:
            text: Text to chunk
            chunk_size: Maximum tokens per chunk

        Returns:
            List of chunk dictionaries
        """
        # First, detect paragraphs
        paragraphs = self._detect_paragraphs_from_text(text)

        chunks = []
        current_chunk_content = []
        current_chunk_tokens = 0
        chunk_number = 1

        for paragraph in paragraphs:
            # Count tokens for this paragraph
            paragraph_tokens = self.token_counter.safe_count(paragraph)

            # Check if this paragraph alone exceeds max chunk size
            if paragraph_tokens > chunk_size:
                # Save current chunk if it has content
                if current_chunk_content:
                    text_chunk = self._join_chunk_content(current_chunk_content)
                    chunks.append(
                        self._create_chunk_dict(
                            chunk_number, text_chunk, current_chunk_tokens
                        )
                    )
                    chunk_number += 1
                    current_chunk_content = []
                    current_chunk_tokens = 0

                # Split oversized paragraph and add as separate chunks
                paragraph_chunks = self._split_oversized_paragraph(
                    paragraph, chunk_size
                )
                for para_chunk in paragraph_chunks:
                    para_chunk_tokens = self.token_counter.safe_count(para_chunk)
                    chunks.append(
                        self._create_chunk_dict(
                            chunk_number, para_chunk, para_chunk_tokens
                        )
                    )
                    chunk_number += 1

            # Check if adding this paragraph would exceed chunk size
            elif (
                current_chunk_tokens + paragraph_tokens > chunk_size
                and current_chunk_content
            ):
                # Save current chunk
                text_chunk = self._join_chunk_content(current_chunk_content)
                chunks.append(
                    self._create_chunk_dict(
                        chunk_number, text_chunk, current_chunk_tokens
                    )
                )
                chunk_number += 1

                # Start new chunk with current paragraph
                current_chunk_content = [paragraph]
                current_chunk_tokens = paragraph_tokens
            else:
                # Add paragraph to current chunk
                current_chunk_content.append(paragraph)
                current_chunk_tokens += paragraph_tokens

        # Add final chunk if it has content
        if current_chunk_content:
            text_chunk = self._join_chunk_content(current_chunk_content)
            final_tokens = (
                self.token_counter.safe_count(text_chunk) if text_chunk else 0
            )
            chunks.append(
                self._create_chunk_dict(chunk_number, text_chunk, final_tokens)
            )

        # Add semantic overlaps between chunks
        if self.sentence_overlap and len(chunks) > 1:
            chunks = self._add_semantic_overlaps(chunks)

        logger.info(
            f"Split text into {len(chunks)} chunks using semantic boundaries, total tokens: {sum(c['token_count'] for c in chunks)}"
        )
        return chunks

    def _detect_paragraphs_from_text(self, text: str) -> List[str]:
        """
        Detect paragraphs in plain text using heuristics.

        Args:
            text: Raw text content

        Returns:
            List of paragraph strings
        """
        # Split on double line breaks (most common paragraph separator)
        paragraphs = re.split(r"\n\s*\n", text)

        # Clean and filter paragraphs
        cleaned_paragraphs = []
        for para in paragraphs:
            # Clean whitespace and normalize line breaks within paragraph
            para = re.sub(r"\s+", " ", para.strip())

            # Filter out very short "paragraphs" that are likely artifacts
            if len(para) > 20:  # Minimum paragraph length
                cleaned_paragraphs.append(para)

        return cleaned_paragraphs

    def _split_oversized_paragraph(self, paragraph: str, chunk_size: int) -> List[str]:
        """
        Split a paragraph that exceeds token limits at sentence boundaries.

        Args:
            paragraph: Paragraph text to split
            chunk_size: Maximum tokens per chunk

        Returns:
            List of paragraph chunks
        """
        # Use the unified sentence-based chunking helper
        return [
            chunk
            for chunk in self._sentence_based_chunking(
                paragraph, chunk_size, raw_only=True
            )
        ]

    def _add_semantic_overlaps(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Add semantic-aware overlaps between chunks.

        Args:
            chunks: List of chunk dictionaries

        Returns:
            Chunks with semantic overlaps added
        """
        if len(chunks) <= 1:
            return chunks

        enhanced_chunks = [chunks[0]]  # First chunk unchanged

        for i in range(1, len(chunks)):
            current_chunk = chunks[i]
            previous_chunk = chunks[i - 1]

            # Create semantic overlap from previous chunk
            overlap_text = self._create_semantic_overlap(previous_chunk["raw_text"])

            if overlap_text:
                # Prepend overlap to current chunk
                enhanced_text = overlap_text + "\n\n" + current_chunk["raw_text"]

                # Recalculate token count
                new_token_count = self.token_counter.safe_count(enhanced_text)

                enhanced_chunks.append(
                    self._create_chunk_dict(
                        current_chunk["chunk_number"],
                        enhanced_text,
                        new_token_count,
                    )
                )
            else:
                enhanced_chunks.append(current_chunk)

        return enhanced_chunks

    def _create_semantic_overlap(self, text: str) -> str:
        """
        Create overlap text that ends at sentence boundaries.

        Args:
            text: Source text

        Returns:
            Overlap text ending at sentence boundary
        """
        # Split into sentences
        sentences = self.split_into_sentences(text)

        overlap = min(self.sentence_overlap, len(sentences))

        # Take last N sentences as overlap
        overlap_sentences = sentences[-overlap:]
        overlap_text = " ".join(overlap_sentences).strip()

        # Ensure reasonable overlap length (not too long or short)
        if len(overlap_text) < 50:
            return ""
        if len(overlap_text) > 500:
            overlap_text = ""
            for sentence in overlap_sentences:
                if len(overlap_text) + len(sentence) + 1 <= 500:
                    overlap_text += " " + sentence
                else:
                    break

        return overlap_text

    def _chunk_by_tokens(self, text: str, chunk_size: int) -> list[str]:
        """
        Split text into chunks based on token count rather than character count.

        Args:
            text: Text to chunk
            chunk_size: Maximum tokens per chunk

        Returns:
            List of text chunks
        """
        if isinstance(self.token_counter.tokenizer, tiktoken.Encoding):
            tokens = self.token_counter.tokenizer.encode(text)

            chunks = []
            start = 0

            while start < len(tokens):
                end = min(start + chunk_size, len(tokens))
                chunk_tokens = tokens[start:end]
                text_chunk = self.token_counter.tokenizer.decode(chunk_tokens)
                chunks.append(text_chunk)

                # Move start position, accounting for overlap
                start = end - self.token_overlap
                if start >= len(tokens):
                    break

            return chunks
        else:
            # For Gemini, we need to use iterative chunking since we can't encode/decode directly
            # Split text into sentences first for better chunking boundaries
            sentences = self.split_into_sentences(text)
            chunks = []
            current_chunk = ""

            for sentence in sentences:
                # Test if adding this sentence would exceed max tokens
                test_chunk = (
                    current_chunk + " " + sentence if current_chunk else sentence
                )

                test_tokens = self.token_counter.count(test_chunk)

                if test_tokens > chunk_size and current_chunk:
                    # Save current chunk and start new one
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Add sentence to current chunk
                    current_chunk = test_chunk

            # Add final chunk
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            # Add overlaps between chunks
            if self.token_overlap > 0 and len(chunks) > 1:
                chunks = self._add_token_overlaps(chunks)

            return chunks

    def _safe_chunk_by_tokens(self, text: str, chunk_size: int) -> list[str]:
        """
        Split text into chunks based on token count with fallback to character-based chunking.

        Args:
            text: Text to chunk
            chunk_size: Maximum tokens per chunk

        Returns:
            List of text chunks
        """
        try:
            return self._chunk_by_tokens(text, chunk_size)
        except Exception:
            whitespaces = [" ", "\n", "\t", "\r", "\f", "\v"]
            endings = [".", "!", "?"]
            boundaries = whitespaces + endings

            # Fallback to character-based chunking with token estimation
            max_chars = chunk_size * CHARS_PER_TOKEN_ESTIMATE
            overlap_chars = self.token_overlap * CHARS_PER_TOKEN_ESTIMATE

            chunks = []
            start = 0

            while start < len(text):
                end = min(start + max_chars, len(text))
                chunk = text[start:end]

                # Try to break at word or sentence boundaries
                if end < len(text) and text[end] not in boundaries:
                    last_boundary = max(chunk.rfind(b) for b in boundaries)
                    if last_boundary != -1 and last_boundary > len(chunk) // 2:
                        end = start + last_boundary + 1
                        chunk = text[start:end]

                chunks.append(chunk.strip())
                start = end - overlap_chars
                if start >= len(text):
                    break

            return chunks

    def _add_token_overlaps(self, chunks: list[str]) -> list[str]:
        """
        Add overlaps between chunks for better context continuity.

        Args:
            chunks: List of text chunks

        Returns:
            List of chunks with overlaps added
        """
        if len(chunks) <= 1:
            return chunks

        overlapped_chunks = [chunks[0]]  # First chunk unchanged

        for i in range(1, len(chunks)):
            current_chunk = chunks[i]
            previous_chunk = chunks[i - 1]

            # Get the last portion of previous chunk for overlap
            prev_sentences = self.split_into_sentences(previous_chunk)
            overlap_text = ""

            # Try to get approximately overlap_tokens worth of text from end of previous chunk
            for j in range(len(prev_sentences) - 1, -1, -1):
                test_overlap = " ".join(prev_sentences[j:])
                try:
                    if self.token_counter.count(test_overlap) <= self.token_overlap:
                        overlap_text = test_overlap
                        break
                except Exception:
                    # Fallback to character-based estimation
                    if (
                        len(test_overlap)
                        <= self.token_overlap * CHARS_PER_TOKEN_ESTIMATE
                    ):
                        overlap_text = test_overlap
                        break

            # Add overlap to current chunk
            if overlap_text:
                overlapped_chunk = overlap_text + " " + current_chunk
                overlapped_chunks.append(overlapped_chunk)
            else:
                overlapped_chunks.append(current_chunk)

        return overlapped_chunks

    @overload
    def _sentence_based_chunking(
        self,
        text: str,
        chunk_size: int,
        raw_only: Literal[True],
    ) -> List[str]: ...

    @overload
    def _sentence_based_chunking(
        self,
        text: str,
        chunk_size: int,
        raw_only: Literal[False] = False,
    ) -> List[Chunk]: ...

    def _sentence_based_chunking(
        self,
        text: str,
        chunk_size: int,
        raw_only: bool = False,
    ) -> List[str] | List[Chunk]:
        """
        Helper for sentence-based chunking, used by fallback and paragraph splitting.
        If raw_only is True, returns only the raw text chunks (for paragraph splitting).
        """
        sentences = self.split_into_sentences(text)
        chunks = []
        current_chunk = ""
        chunk_number = 1
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            test_tokens = self.token_counter.safe_count(test_chunk)
            if test_tokens > chunk_size and current_chunk:
                if raw_only:
                    chunks.append(current_chunk.strip())
                else:
                    current_tokens = self.token_counter.safe_count(current_chunk)
                    chunks.append(
                        {
                            "chunk_number": chunk_number,
                            "raw_text": current_chunk.strip(),
                            "token_count": current_tokens,
                            "character_count": len(current_chunk),
                        }
                    )
                current_chunk = sentence
                chunk_number += 1
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        if current_chunk.strip():
            if raw_only:
                chunks.append(current_chunk.strip())
            else:
                final_tokens = self.token_counter.safe_count(current_chunk)
                chunks.append(
                    {
                        "chunk_number": chunk_number,
                        "raw_text": current_chunk.strip(),
                        "token_count": final_tokens,
                        "character_count": len(current_chunk),
                    }
                )
        if raw_only:
            return chunks
        logger.info(
            f"Split text into {len(chunks)} chunks using sentence-based chunking, total tokens: {sum(c.get('token_count', 0) for c in chunks)}"
        )
        return chunks

    def _join_chunk_content(self, content_list: List[str]) -> str:
        """
        Join chunk content maintaining paragraph structure.

        Args:
            content_list: List of paragraphs or content pieces

        Returns:
            Joined text with proper spacing
        """
        return "\n\n".join(
            content.strip() for content in content_list if content.strip()
        )

    def _create_chunk_dict(
        self, chunk_number: int, text: str, token_count: int
    ) -> Chunk:
        """
        Create a standardized chunk dictionary.

        Args:
            chunk_number: Sequential chunk number
            text: Chunk text content
            token_count: Actual token count

        Returns:
            Chunk dictionary matching expected format
        """
        return {
            "chunk_number": chunk_number,
            "raw_text": text.strip(),
            "token_count": token_count,
            "character_count": len(text),
        }

    @staticmethod
    def split_into_sentences(text: str) -> list[str]:
        """
        Split text into sentences using improved regex pattern.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Use regex for better sentence splitting
        sentences = re.split(r"""(?<=[.!?]"\s)|(?<=[.!?]'\s)|(?<=[.!?]\s)""", text)
        return [s.strip() for s in sentences if s.strip()]

    def add_start_to_chunks(
        self, text: str, chunks: list[Chunk]
    ) -> List[ChunkWithStart]:
        """
        Add start index to each chunk based on its position in the original text.

        Args:
            text: Original text content
            chunks: List of chunk dictionaries without start index

        Returns:
            List of chunks with start index added
        """
        chunks_with_start: List[ChunkWithStart] = []
        for chunk in chunks:
            chunks_with_start.append(
                {
                    **chunk,
                    "start": text.find(chunk["raw_text"]),
                }
            )

        return chunks_with_start

    def process_document(
        self, file_path: str
    ) -> ProcessedDocument | FailedProcessedDocument:
        """
        Complete document processing pipeline.

        Args:
            file_path: Path to document file

        Returns:
            Processing results with metadata
        """
        try:
            # Extract text
            raw_text = self.document_reader.extract(file_path)

            # Clean text
            cleaned_text = self.document_reader.clean(raw_text)

            # Create chunks
            chunks = self.chunk_text(cleaned_text)

            # Calculate metadata
            metadata: ProcessedDocumentMetadata = {
                "file_path": file_path,
                "file_size": Path(file_path).stat().st_size,
                "original_length": len(raw_text),
                "cleaned_length": len(cleaned_text),
                "chunk_count": len(chunks),
                "total_tokens": sum(c["token_count"] for c in chunks),
                "processing_model": f"{self._provider}/{self._model}",
            }

            return {
                "status": "success",
                "raw_text": raw_text,
                "cleaned_text": cleaned_text,
                "chunks": chunks,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Document processing failed for {file_path}: {str(e)}")
            return {"status": "failed", "error": str(e), "file_path": file_path}

    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        return self.document_reader.validate_file(file_path)
