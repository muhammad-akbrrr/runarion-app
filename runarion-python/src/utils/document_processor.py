"""
Document processor utility for handling file uploads and content extraction.
Supports PDF, TXT, and DOCX files with intelligent chunking for large documents.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from docx import Document

from .get_model_max_token import (
    chunk_text_by_tokens,
    count_tokens,
    get_safe_max_tokens,
    split_into_sentences,
)

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Handles document ingestion, extraction, and chunking for the novel pipeline.
    """

    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.doc'}
    DEFAULT_CHUNK_SIZE = 4000  # Conservative token limit for chunking
    OVERLAP_SIZE = 200  # Overlap between chunks to maintain context

    # Enhanced chunking configuration
    PARAGRAPH_PRIORITY = True  # Prefer paragraph boundaries
    MAX_PARAGRAPH_TOKENS = 8000  # Maximum tokens per paragraph before splitting
    SEMANTIC_OVERLAP = True  # Create overlaps at sentence boundaries

    def __init__(self, upload_path: str = "/app/uploads"):
        self.upload_path = Path(upload_path)
        self.upload_path.mkdir(exist_ok=True)

    def extract_text_from_file(self, file_path: str) -> str:
        """
        Extract text content from various file formats.

        Args:
            file_path: Path to the document file

        Returns:
            Extracted text content

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
            Exception: If extraction fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = file_path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {extension}")

        try:
            if extension == '.pdf':
                return self._extract_from_pdf(file_path)
            elif extension == '.txt':
                return self._extract_from_txt(file_path)
            elif extension in ['.docx', '.doc']:
                return self._extract_from_docx(file_path)
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {str(e)}")
            raise

    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file using PyMuPDF with paragraph preservation."""
        if self.PARAGRAPH_PRIORITY:
            return self._extract_paragraphs_from_pdf(file_path)
        else:
            # Original extraction method for backward compatibility
            text_content = []

            with fitz.open(str(file_path)) as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text()

                    if text.strip():
                        text_content.append(text)

            return "\n".join(text_content)

    def _extract_from_txt(self, file_path: Path) -> str:
        """Extract text from TXT file with encoding detection."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as file:
                return file.read()

    def _extract_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file."""
        doc = Document(str(file_path))
        text_content = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text)

        return "\n".join(text_content)

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove page numbers and common PDF artifacts
        text = re.sub(r'\b\d+\b(?=\s*$)', '', text, flags=re.MULTILINE)

        # Remove excessive line breaks
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # Remove zero-width characters
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def chunk_text(self, text: str, provider: str = "openai", model: str = "gpt-4o",
                   max_chunk_size: Optional[int] = None) -> List[Dict[str, any]]:
        """
        Split text into chunks suitable for AI processing using proper tokenizers.

        Args:
            text: Text to chunk
            provider: AI provider for token counting
            model: AI model for token limit
            max_chunk_size: Override default chunk size

        Returns:
            List of chunk dictionaries with metadata
        """
        if not text.strip():
            return []

        # Get model-specific token limit with safety margin
        try:
            safe_max_tokens = get_safe_max_tokens(
                provider, model, safety_margin=0.2)
            # Use conservative chunk size (25% of safe limit)
            chunk_size = max_chunk_size or min(
                self.DEFAULT_CHUNK_SIZE, safe_max_tokens // 4)
        except Exception as e:
            logger.warning(
                f"Could not get token limit for {provider}/{model}: {e}")
            chunk_size = max_chunk_size or self.DEFAULT_CHUNK_SIZE

        # Use enhanced semantic boundary chunking
        if self.PARAGRAPH_PRIORITY:
            try:
                return self._chunk_by_semantic_boundaries(text, chunk_size, provider, model)
            except Exception as e:
                logger.warning(
                    f"Semantic boundary chunking failed, falling back to tokenizer-based: {e}")

        # Use proper tokenizer-based chunking as fallback
        try:
            text_chunks = chunk_text_by_tokens(
                text, chunk_size, provider, model, overlap_tokens=50)

            chunks = []
            for i, chunk_text in enumerate(text_chunks, 1):
                # Get accurate token count for the chunk
                actual_token_count = self._safe_count_tokens(
                    chunk_text, provider, model)

                chunks.append({
                    'chunk_number': i,
                    'raw_text': chunk_text.strip(),
                    'token_count': actual_token_count,
                    'character_count': len(chunk_text)
                })

            logger.info(
                f"Split text into {len(chunks)} chunks using tokenizer, total tokens: {sum(c['token_count'] for c in chunks)}")
            return chunks

        except Exception as e:
            logger.warning(
                f"Tokenizer-based chunking failed, falling back to sentence-based: {e}")
            return self._sentence_based_chunking(text, chunk_size, provider, model)

    def _chunk_text_fallback(self, text: str, chunk_size: int, provider: str, model: str) -> List[Dict[str, any]]:
        """
        Fallback chunking method using sentence boundaries with improved token estimation.

        Args:
            text: Text to chunk
            chunk_size: Maximum tokens per chunk
            provider: AI provider
            model: AI model

        Returns:
            List of chunk dictionaries
        """
        return self._sentence_based_chunking(text, chunk_size, provider, model)

    def _extract_paragraphs_from_pdf(self, file_path: Path) -> str:
        """
        Extract text from PDF with enhanced paragraph detection using PyMuPDF structural analysis.

        Args:
            file_path: Path to PDF file

        Returns:
            Text with properly preserved paragraph boundaries
        """
        paragraphs = []

        with fitz.open(str(file_path)) as doc:
            for page in doc:
                blocks = page.get_text("blocks")
                for block in blocks:
                    # skip if image block
                    if block[6] != 0:
                        continue
                    # extract the text from the block
                    paragraphs.append(block[4])

        # Join paragraphs with double line breaks to maintain structure
        return "\n\n".join(paragraph.strip() for paragraph in paragraphs if paragraph.strip())

    def _detect_paragraphs_from_text(self, text: str) -> List[str]:
        """
        Detect paragraphs in plain text using heuristics.

        Args:
            text: Raw text content

        Returns:
            List of paragraph strings
        """
        # Split on double line breaks (most common paragraph separator)
        paragraphs = re.split(r'\n\s*\n', text)

        # Clean and filter paragraphs
        cleaned_paragraphs = []
        for para in paragraphs:
            # Clean whitespace and normalize line breaks within paragraph
            para = re.sub(r'\s+', ' ', para.strip())

            # Filter out very short "paragraphs" that are likely artifacts
            if len(para) > 20:  # Minimum paragraph length
                cleaned_paragraphs.append(para)

        return cleaned_paragraphs

    def _chunk_by_semantic_boundaries(self, text: str, chunk_size: int, provider: str, model: str) -> List[Dict[str, any]]:
        """
        Chunk text using hierarchical semantic boundaries: paragraphs > sentences > words.

        Args:
            text: Text to chunk
            chunk_size: Maximum tokens per chunk
            provider: AI provider
            model: AI model

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
            paragraph_tokens = self._safe_count_tokens(
                paragraph, provider, model)

            # Check if paragraph alone exceeds max chunk size
            if paragraph_tokens > self.MAX_PARAGRAPH_TOKENS:
                # Save current chunk if it has content
                if current_chunk_content:
                    chunk_text = self._join_chunk_content(
                        current_chunk_content)
                    chunks.append(self._create_chunk_dict(
                        chunk_number, chunk_text, current_chunk_tokens))
                    chunk_number += 1
                    current_chunk_content = []
                    current_chunk_tokens = 0

                # Split oversized paragraph and add as separate chunks
                paragraph_chunks = self._split_oversized_paragraph(
                    paragraph, chunk_size, provider, model)
                for para_chunk in paragraph_chunks:
                    para_chunk_tokens = self._safe_count_tokens(
                        para_chunk, provider, model)
                    chunks.append(self._create_chunk_dict(
                        chunk_number, para_chunk, para_chunk_tokens))
                    chunk_number += 1

            # Check if adding this paragraph would exceed chunk size
            elif current_chunk_tokens + paragraph_tokens > chunk_size and current_chunk_content:
                # Save current chunk
                chunk_text = self._join_chunk_content(current_chunk_content)
                chunks.append(self._create_chunk_dict(
                    chunk_number, chunk_text, current_chunk_tokens))
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
            chunk_text = self._join_chunk_content(current_chunk_content)
            final_tokens = self._safe_count_tokens(
                chunk_text, provider, model) if chunk_text else 0
            chunks.append(self._create_chunk_dict(
                chunk_number, chunk_text, final_tokens))

        # Add semantic overlaps between chunks
        if self.SEMANTIC_OVERLAP and len(chunks) > 1:
            chunks = self._add_semantic_overlaps(chunks, provider, model)

        logger.info(
            f"Split text into {len(chunks)} chunks using semantic boundaries, total tokens: {sum(c['token_count'] for c in chunks)}")
        return chunks

    def _split_oversized_paragraph(self, paragraph: str, chunk_size: int, provider: str, model: str) -> List[str]:
        """
        Split a paragraph that exceeds token limits at sentence boundaries.

        Args:
            paragraph: Paragraph text to split
            chunk_size: Maximum tokens per chunk
            provider: AI provider
            model: AI model

        Returns:
            List of paragraph chunks
        """
        # Use the unified sentence-based chunking helper
        return [chunk['raw_text'] for chunk in self._sentence_based_chunking(paragraph, chunk_size, provider, model, raw_only=True)]

    def _sentence_based_chunking(self, text: str, chunk_size: int, provider: str, model: str, raw_only: bool = False) -> List[Dict[str, any]]:
        """
        Helper for sentence-based chunking, used by fallback and paragraph splitting.
        If raw_only is True, returns only the raw text chunks (for paragraph splitting).
        """
        sentences = split_into_sentences(text)
        chunks = []
        current_chunk = ""
        chunk_number = 1
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            test_tokens = self._safe_count_tokens(test_chunk, provider, model)
            if test_tokens > chunk_size and current_chunk:
                current_tokens = self._safe_count_tokens(
                    current_chunk, provider, model)
                if raw_only:
                    chunks.append({'raw_text': current_chunk.strip()})
                else:
                    chunks.append({
                        'chunk_number': chunk_number,
                        'raw_text': current_chunk.strip(),
                        'token_count': current_tokens,
                        'character_count': len(current_chunk)
                    })
                current_chunk = sentence
                chunk_number += 1
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        if current_chunk.strip():
            final_tokens = self._safe_count_tokens(
                current_chunk, provider, model)
            if raw_only:
                chunks.append({'raw_text': current_chunk.strip()})
            else:
                chunks.append({
                    'chunk_number': chunk_number,
                    'raw_text': current_chunk.strip(),
                    'token_count': final_tokens,
                    'character_count': len(current_chunk)
                })
        if raw_only:
            return chunks
        logger.info(
            f"Split text into {len(chunks)} chunks using sentence-based chunking, total tokens: {sum(c.get('token_count', 0) for c in chunks)}")
        return chunks

    def _join_chunk_content(self, content_list: List[str]) -> str:
        """
        Join chunk content maintaining paragraph structure.

        Args:
            content_list: List of paragraphs or content pieces

        Returns:
            Joined text with proper spacing
        """
        return "\n\n".join(content.strip() for content in content_list if content.strip())

    def _create_chunk_dict(self, chunk_number: int, text: str, token_count: int) -> Dict[str, any]:
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
            'chunk_number': chunk_number,
            'raw_text': text.strip(),
            'token_count': token_count,
            'character_count': len(text)
        }

    def _add_semantic_overlaps(self, chunks: List[Dict[str, any]], provider: str, model: str) -> List[Dict[str, any]]:
        """
        Add semantic-aware overlaps between chunks.

        Args:
            chunks: List of chunk dictionaries
            provider: AI provider
            model: AI model

        Returns:
            Chunks with semantic overlaps added
        """
        if len(chunks) <= 1:
            return chunks

        enhanced_chunks = [chunks[0]]  # First chunk unchanged

        for i in range(1, len(chunks)):
            current_chunk = chunks[i]
            previous_chunk = chunks[i-1]

            # Create semantic overlap from previous chunk
            overlap_text = self._create_semantic_overlap(
                previous_chunk['raw_text'])

            if overlap_text:
                # Prepend overlap to current chunk
                enhanced_text = overlap_text + \
                    "\n\n" + current_chunk['raw_text']

                # Recalculate token count
                try:
                    new_token_count = count_tokens(
                        enhanced_text, provider, model)
                except Exception:
                    new_token_count = current_chunk['token_count'] + \
                        len(overlap_text) // 4

                enhanced_chunk = {
                    'chunk_number': current_chunk['chunk_number'],
                    'raw_text': enhanced_text,
                    'token_count': new_token_count,
                    'character_count': len(enhanced_text)
                }
                enhanced_chunks.append(enhanced_chunk)
            else:
                enhanced_chunks.append(current_chunk)

        return enhanced_chunks

    def _create_semantic_overlap(self, text: str, max_sentences: int = 2) -> str:
        """
        Create overlap text that ends at sentence boundaries.

        Args:
            text: Source text
            max_sentences: Maximum sentences to include in overlap

        Returns:
            Overlap text ending at sentence boundary
        """
        # Split into sentences
        sentences = split_into_sentences(text)

        if len(sentences) <= max_sentences:
            return ""  # Not enough content for meaningful overlap

        # Take last N sentences as overlap
        overlap_sentences = sentences[-max_sentences:]
        overlap_text = " ".join(overlap_sentences).strip()

        # Ensure reasonable overlap length (not too long or short)
        if len(overlap_text) < 50 or len(overlap_text) > 400:
            return ""  # Skip if overlap is too short or too long

        return overlap_text

    def _safe_count_tokens(self, text: str, provider: str, model: str) -> int:
        """
        Safely count tokens, falling back to character-based estimation if needed.
        """
        try:
            return count_tokens(text, provider, model)
        except Exception:
            return len(text) // 4

    def process_document(self, file_path: str, provider: str = "openai",
                         model: str = "gpt-4o") -> Dict[str, any]:
        """
        Complete document processing pipeline.

        Args:
            file_path: Path to document file
            provider: AI provider for processing
            model: AI model for processing

        Returns:
            Processing results with metadata
        """
        try:
            # Extract text
            raw_text = self.extract_text_from_file(file_path)

            # Clean text
            cleaned_text = self.clean_text(raw_text)

            # Create chunks
            chunks = self.chunk_text(cleaned_text, provider, model)

            # Calculate metadata
            metadata = {
                'file_path': file_path,
                'file_size': Path(file_path).stat().st_size,
                'original_length': len(raw_text),
                'cleaned_length': len(cleaned_text),
                'chunk_count': len(chunks),
                'total_tokens': sum(c['token_count'] for c in chunks),
                'processing_model': f"{provider}/{model}"
            }

            return {
                'success': True,
                'raw_text': raw_text,
                'cleaned_text': cleaned_text,
                'chunks': chunks,
                'metadata': metadata
            }

        except Exception as e:
            logger.error(
                f"Document processing failed for {file_path}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }

    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate file before processing.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (is_valid, error_message)
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return False, f"File not found: {file_path}"

        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return False, f"Unsupported file format: {file_path.suffix}"

        # Check file size (100MB limit)
        if file_path.stat().st_size > 100 * 1024 * 1024:
            return False, "File too large (max 100MB)"

        return True, ""
