import logging
import re
from pathlib import Path
from typing import List, Literal, Optional, Tuple, TypedDict

from .document_reader import DocumentReader
from .get_model_max_token import (
    get_safe_model_max_tokens,
)
from .token_counter import (
    TokenCounter,
)

logger = logging.getLogger(__name__)


class Chunk(TypedDict):
    chunk_number: int
    raw_text: str
    token_count: int
    character_count: int
    word_count: int


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
        provider: str,
        model: str,
        model_token_safety_margin: float | int = 0.5,
        chunk_token_limit: Optional[int] = None,
        chunk_word_limit: Optional[int] = None,
        sentence_overlap: int = 0,
    ):
        """
        Initialize the document processor with configuration options.

        Args:
            provider: LLM provider for token counting and limits
            model: LLM model for token counting and limits
            model_token_safety_margin: Portion of tokens to reserve from model max tokens, int means number of tokens, float means ratio of model max tokens
            chunk_token_limit: Maximum token size for each chunk, if None or too big uses conservative limit based on model max tokens and safety margin
            chunk_word_limit: Maximum word count for each chunk, works together with chunk_token_limit, if None then no limit
            sentence_overlap: Number of sentences to overlap between chunks
        """
        self.document_reader = DocumentReader()

        self._provider = provider
        self._model = model

        self.token_counter = TokenCounter(
            provider=provider,
            model=model,
        )

        try:
            self.conservative_limit = get_safe_model_max_tokens(
                provider, model, safety_margin=model_token_safety_margin
            )
        except Exception as e:
            logger.warning(
                f"Failed to get conservative max token limit for {provider}/{model}: {e}."
            )
            self.conservative_limit = None
        self._chunk_token_limit = self.get_chunk_token_limit(chunk_token_limit)

        self.chunk_word_limit = chunk_word_limit if chunk_word_limit else 9999999999
        self.sentence_overlap = sentence_overlap

    def get_chunk_token_limit(self, chunk_token_limit: Optional[int]) -> int:
        """
        Get the effective chunk token limit based on user-defined and conservative limits.

        Args:
            chunk_token_limit: User-defined chunk token limit

        Returns:
            Effective chunk token limit to use for processing
        """
        if chunk_token_limit is None:
            if self.conservative_limit is None:
                return 4000
            else:
                return self.conservative_limit
        else:
            if self.conservative_limit is None:
                return chunk_token_limit
            else:
                return min(chunk_token_limit, self.conservative_limit)

    @property
    def chunk_token_limit(self) -> int:
        return self._chunk_token_limit

    @chunk_token_limit.setter
    def chunk_token_limit(self, value: Optional[int]):
        if value is not None and value <= 0:
            raise ValueError("Chunk token limit cannot be zero or negative.")
        self._chunk_token_limit = self.get_chunk_token_limit(value)

    def chunk_text(
        self,
        text: str,
    ) -> List[Chunk]:
        """
        Split text into chunks suitable for AI processing using proper tokenizers.

        Args:
            text: Text to chunk

        Returns:
            List of chunk dictionaries with metadata
        """
        if not text.strip():
            return []

        try:
            return self._paragraph_based_chunking(text)
        except Exception as e:
            logger.warning(
                f"Paragraph-vased chunking failed, falling back to sentence-based: {e}"
            )
            return self._sentence_based_chunking(text)

    def _paragraph_based_chunking(self, text: str) -> List[Chunk]:
        """
        Chunk text based on paragraphs, ensuring each chunk is within word and token limits.

        Args:
            text: Text to chunk

        Returns:
            List of chunk dictionaries
        """
        paragraphs = self._detect_paragraphs_from_text(text)
        chunks: List[Chunk] = []
        current_contents = []
        current_tokens = 0
        current_words = 0
        chunk_number = 1

        for paragraph in paragraphs:
            paragraph_words = self.count_words(paragraph)
            paragraph_tokens = self.token_counter.safe_count(paragraph)

            # Check if this paragraph alone exceeds limits
            if (
                paragraph_tokens > self.chunk_token_limit
                or paragraph_words > self.chunk_word_limit
            ):
                # Save current chunk if it has content
                if current_contents:
                    text_chunk = self._join_chunk_content(current_contents)
                    chunks.append(self._create_chunk_dict(chunk_number, text_chunk))
                    chunk_number += 1
                    current_contents = []
                    current_tokens = 0
                    current_words = 0

                # Split oversized paragraph into smaller chunks
                paragraph_chunks = self._sentence_based_chunking(
                    paragraph, initial_chunk_number=chunk_number
                )
                chunks.extend(paragraph_chunks)
                chunk_number += len(paragraph_chunks)

            # Check if adding this paragraph would exceed limits
            elif (
                ((current_tokens + paragraph_tokens) > self.chunk_token_limit)
                or ((current_words + paragraph_words) > self.chunk_word_limit)
            ) and current_contents:
                # Save current chunk
                text_chunk = self._join_chunk_content(current_contents)
                chunks.append(self._create_chunk_dict(chunk_number, text_chunk))
                chunk_number += 1

                # Start new chunk with current paragraph
                current_contents = [paragraph]
                current_tokens = paragraph_tokens
                current_words = paragraph_words

            # Otherwise, add paragraph to current chunk
            else:
                current_contents.append(paragraph)
                current_tokens += paragraph_tokens
                current_words += paragraph_words

        # Add final chunk if it has content
        if current_contents:
            text_chunk = self._join_chunk_content(current_contents)
            chunks.append(self._create_chunk_dict(chunk_number, text_chunk))

        # Add semantic overlaps if configured
        if self.sentence_overlap > 0 and len(chunks) > 1:
            chunks = self._add_semantic_overlaps(chunks)

        total_tokens = sum(c["token_count"] for c in chunks)
        total_words = sum(c["word_count"] for c in chunks)
        logger.info(
            f"Split text into {len(chunks)} chunks using paragraph-based chunking, total tokens: {total_tokens}, total words: {total_words}"
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
            overlap_text = self._create_semantic_overlap(
                previous_chunk["raw_text"],
                current_chunk["token_count"],
                current_chunk["word_count"],
            )

            if overlap_text:
                enhanced_chunks.append(
                    self._create_chunk_dict(
                        current_chunk["chunk_number"],
                        overlap_text + "\n\n" + current_chunk["raw_text"],
                    )
                )
            else:
                enhanced_chunks.append(current_chunk)

        return enhanced_chunks

    def _create_semantic_overlap(
        self, previous_text: str, chunk_token_count: int, chunk_word_count: int
    ) -> str:
        """
        Create overlap text that ends at sentence boundaries.

        Args:
            previous_text: Text from the previous chunk
            chunk_token_count: Token count of the current chunk
            chunk_word_count: Word count of the current chunk

        Returns:
            Overlap text at the end of the previous chunk
        """
        sentences = self.split_into_sentences(previous_text)

        overlap_count = min(self.sentence_overlap, len(sentences))
        overlap_text = ""
        total_tokens = chunk_token_count
        total_words = chunk_word_count
        for sentence in reversed(sentences[-overlap_count:]):
            sentence = sentence.strip()
            if not sentence:
                continue
            sentence_tokens = self.token_counter.safe_count(sentence)
            sentence_words = self.count_words(sentence)

            if (total_tokens + sentence_tokens) <= self.chunk_token_limit and (
                total_words + sentence_words
            ) <= self.chunk_word_limit:
                overlap_text = sentence + " " + overlap_text
                total_tokens += sentence_tokens
                total_words += sentence_words
            else:
                break

        overlap_text = overlap_text.strip()
        if len(overlap_text) < 50:
            return ""
        return overlap_text

    def _sentence_based_chunking(
        self,
        text: str,
        initial_chunk_number: int = 1,
    ) -> List[Chunk]:
        """
        Split text into chunks based on sentences, ensuring each chunk is within word and token limits.
        """
        sentences = self.split_into_sentences(text)
        chunks: List[Chunk] = []
        current_chunk = ""
        current_tokens = 0
        current_words = 0
        chunk_number = initial_chunk_number

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            sentence_tokens = self.token_counter.safe_count(sentence)
            sentence_words = self.count_words(sentence)
            if (
                (current_tokens + sentence_tokens) > self.chunk_word_limit
                or (current_words + sentence_words) > self.chunk_token_limit
            ) and current_chunk:
                chunks.append(
                    self._create_chunk_dict(
                        chunk_number,
                        current_chunk,
                    )
                )
                current_chunk = sentence
                current_tokens = sentence_tokens
                current_words = sentence_words
                chunk_number += 1
            else:
                current_chunk = (
                    current_chunk + " " + sentence if current_chunk else sentence
                )
                current_tokens += sentence_tokens
                current_words += sentence_words

        if current_chunk.strip():
            chunks.append(
                self._create_chunk_dict(
                    chunk_number,
                    current_chunk,
                )
            )

        total_tokens = sum(c.get("token_count", 0) for c in chunks)
        total_words = sum(c.get("word_count", 0) for c in chunks)
        logger.info(
            f"Split text into {len(chunks)} chunks using sentence-based chunking, total tokens: {total_tokens}, total words: {total_words}"
        )

        return chunks

    def _create_chunk_dict(
        self,
        chunk_number: int,
        text: str,
        token_count: Optional[int] = None,
        word_count: Optional[int] = None,
    ) -> Chunk:
        """
        Create a standardized chunk dictionary.

        Args:
            chunk_number: Sequential chunk number
            text: Chunk text content
            token_count: Token count of the text
            word_count: Word count of the text

        Returns:
            Chunk dictionary matching expected format
        """
        return {
            "chunk_number": chunk_number,
            "raw_text": text.strip(),
            "token_count": token_count or self.token_counter.safe_count(text),
            "word_count": word_count or self.count_words(text),
            "character_count": len(text),
        }

    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
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

    @staticmethod
    def count_words(text: str) -> int:
        """
        Count words in text using simple whitespace splitting.

        Args:
            text: Text to count words in

        Returns:
            Number of words in the text
        """
        if not text or not text.strip():
            return 0
        return len(text.strip().split())

    def add_start_to_chunks(
        self, text: str, chunks: List[Chunk]
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
