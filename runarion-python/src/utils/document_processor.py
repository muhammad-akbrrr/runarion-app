"""
Document processor utility for handling file uploads and content extraction.
Supports PDF, TXT, and DOCX files with intelligent chunking for large documents.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import fitz  # PyMuPDF
from docx import Document
from .get_model_max_token import count_tokens, chunk_text_by_tokens, get_safe_max_tokens

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Handles document ingestion, extraction, and chunking for the novel pipeline.
    """

    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.doc'}
    DEFAULT_WORD_LIMIT = 1500  # Primary word-based chunking limit
    DEFAULT_CHUNK_SIZE = 4000  # Token-based safety limit for validation
    OVERLAP_SIZE = 200  # Token overlap between chunks to maintain context
    WORD_OVERLAP_SIZE = 50  # Word overlap between chunks

    # Enhanced chunking configuration
    PARAGRAPH_PRIORITY = True  # Prefer paragraph boundaries
    MAX_PARAGRAPH_WORDS = 2000  # Maximum words per paragraph before splitting
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
                   word_limit: Optional[int] = None) -> List[Dict[str, any]]:
        """
        Split text into chunks using unified semantic boundary approach with word-based sizing and token validation.

        Args:
            text: Text to chunk
            provider: AI provider for token validation
            model: AI model for token limit validation
            word_limit: Target words per chunk (defaults to DEFAULT_WORD_LIMIT)

        Returns:
            List of chunk dictionaries with both word and token metadata
        """
        if not text.strip():
            return []

        # Get token safety limit for validation
        try:
            safe_max_tokens = get_safe_max_tokens(provider, model, safety_margin=0.2)
            token_safety_limit = min(self.DEFAULT_CHUNK_SIZE, safe_max_tokens // 4)
        except Exception as e:
            logger.warning(f"Could not get token limit for {provider}/{model}: {e}")
            token_safety_limit = self.DEFAULT_CHUNK_SIZE

        target_word_limit = word_limit or self.DEFAULT_WORD_LIMIT

        # Unified semantic boundary chunking with word/token validation
        try:
            return self._chunk_by_semantic_boundaries_unified(
                text, target_word_limit, token_safety_limit, provider, model)
        except Exception as e:
            logger.warning(f"Unified chunking failed, falling back to sentence-based: {e}")
            # Final fallback to sentence-based chunking
            return self._sentence_based_chunking(text, token_safety_limit, provider, model)

    def _chunk_text_fallback(self, text: str, token_limit: int, provider: str, model: str) -> List[Dict[str, any]]:
        """
        Fallback chunking method using sentence boundaries with improved token estimation.

        Args:
            text: Text to chunk
            token_limit: Maximum tokens per chunk
            provider: AI provider
            model: AI model

        Returns:
            List of chunk dictionaries
        """
        return self._sentence_based_chunking(text, token_limit, provider, model)

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
            for page_num in range(len(doc)):
                page = doc[page_num]

                # Get structured text data with blocks and lines
                text_dict = page.get_text("dict")

                page_paragraphs = self._extract_paragraphs_from_page_dict(
                    text_dict)
                paragraphs.extend(page_paragraphs)

        # Join paragraphs with double line breaks to maintain structure
        return "\n\n".join(paragraph.strip() for paragraph in paragraphs if paragraph.strip())

    def _extract_paragraphs_from_page_dict(self, page_dict: dict) -> List[str]:
        """
        Extract paragraphs from PyMuPDF page dictionary structure.

        Args:
            page_dict: PyMuPDF page dictionary from get_text("dict")

        Returns:
            List of paragraph strings
        """
        paragraphs = []
        current_paragraph = []
        last_y = None

        for block in page_dict.get("blocks", []):
            if "lines" not in block:  # Skip image blocks
                continue

            for line in block["lines"]:
                line_text = ""

                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if text.strip():
                        line_text += text

                if line_text.strip():
                    # Check for significant vertical gap (new paragraph indicator)
                    current_y = line["bbox"][1]  # Top Y coordinate

                    if last_y is not None:
                        y_gap = abs(current_y - last_y)
                        avg_line_height = 12  # Approximate line height

                        # If gap is larger than 1.5x normal line spacing, it's likely a new paragraph
                        if y_gap > avg_line_height * 1.5 and current_paragraph:
                            paragraphs.append(" ".join(current_paragraph))
                            current_paragraph = []

                    current_paragraph.append(line_text.strip())
                    last_y = current_y

            # End of block typically indicates paragraph boundary
            if current_paragraph:
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []

        # Add any remaining content
        if current_paragraph:
            paragraphs.append(" ".join(current_paragraph))

        return paragraphs

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

    def _chunk_by_semantic_boundaries(self, text: str, token_limit: int, provider: str, model: str) -> List[Dict[str, any]]:
        """
        Chunk text using hierarchical semantic boundaries: paragraphs > sentences > words.

        Args:
            text: Text to chunk
            token_limit: Maximum tokens per chunk
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

            # Check if paragraph alone exceeds max chunk size (convert word limit to approximate token limit)
            if paragraph_tokens > (self.MAX_PARAGRAPH_WORDS * 1.3):
                # Save current chunk if it has content
                if current_chunk_content:
                    chunk_text = self._join_chunk_content(
                        current_chunk_content)
                    word_count = self._count_words(chunk_text)
                    chunks.append(self._create_chunk_unified(
                        chunk_number, chunk_text, word_count, current_chunk_tokens))
                    chunk_number += 1
                    current_chunk_content = []
                    current_chunk_tokens = 0

                # Split oversized paragraph and add as separate chunks
                paragraph_chunks = self._split_oversized_paragraph(
                    paragraph, token_limit, provider, model)
                for para_chunk in paragraph_chunks:
                    para_chunk_tokens = self._safe_count_tokens(
                        para_chunk, provider, model)
                    word_count = self._count_words(para_chunk)
                    chunks.append(self._create_chunk_unified(
                        chunk_number, para_chunk, word_count, para_chunk_tokens))
                    chunk_number += 1

            # Check if adding this paragraph would exceed chunk size
            elif current_chunk_tokens + paragraph_tokens > token_limit and current_chunk_content:
                # Save current chunk
                chunk_text = self._join_chunk_content(current_chunk_content)
                word_count = self._count_words(chunk_text)
                chunks.append(self._create_chunk_unified(
                    chunk_number, chunk_text, word_count, current_chunk_tokens))
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
            word_count = self._count_words(chunk_text)
            chunks.append(self._create_chunk_unified(
                chunk_number, chunk_text, word_count, final_tokens))

        # Add semantic overlaps between chunks
        if self.SEMANTIC_OVERLAP and len(chunks) > 1:
            chunks = self._add_overlaps_unified(chunks, provider, model)

        logger.info(
            f"Split text into {len(chunks)} chunks using semantic boundaries, total tokens: {sum(c['token_count'] for c in chunks)}")
        return chunks

    def _split_oversized_paragraph(self, paragraph: str, token_limit: int, provider: str, model: str) -> List[str]:
        """
        Split a paragraph that exceeds token limits at sentence boundaries.

        Args:
            paragraph: Paragraph text to split
            token_limit: Maximum tokens per chunk
            provider: AI provider
            model: AI model

        Returns:
            List of paragraph chunks
        """
        # Use the unified sentence-based chunking helper
        return [chunk['raw_text'] for chunk in self._sentence_based_chunking(paragraph, token_limit, provider, model, raw_only=True)]

    def _sentence_based_chunking(self, text: str, token_limit: int, provider: str, model: str, raw_only: bool = False) -> List[Dict[str, any]]:
        """
        Helper for sentence-based chunking, used by fallback and paragraph splitting.
        If raw_only is True, returns only the raw text chunks (for paragraph splitting).
        """
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        current_chunk_tokens = 0
        chunk_number = 1
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            test_tokens = self._safe_count_tokens(test_chunk, provider, model)
            if test_tokens > token_limit and current_chunk:
                # Use cached token count from previous iteration
                if raw_only:
                    chunks.append({'raw_text': current_chunk.strip()})
                else:
                    word_count = self._count_words(current_chunk)
                    chunks.append({
                        'chunk_number': chunk_number,
                        'raw_text': current_chunk.strip(),
                        'word_count': word_count,
                        'token_count': current_chunk_tokens,
                        'character_count': len(current_chunk),
                        'safety_validated': True
                    })
                current_chunk = sentence
                current_chunk_tokens = self._safe_count_tokens(sentence, provider, model)
                chunk_number += 1
            else:
                current_chunk = test_chunk
                current_chunk_tokens = test_tokens
        if current_chunk.strip():
            # Use cached token count
            if raw_only:
                chunks.append({'raw_text': current_chunk.strip()})
            else:
                word_count = self._count_words(current_chunk)
                chunks.append({
                    'chunk_number': chunk_number,
                    'raw_text': current_chunk.strip(),
                    'word_count': word_count,
                    'token_count': current_chunk_tokens,
                    'character_count': len(current_chunk),
                    'safety_validated': True
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



    def _safe_count_tokens(self, text: str, provider: str, model: str) -> int:
        """
        Safely count tokens, falling back to character-based estimation if needed.
        """
        try:
            return count_tokens(text, provider, model)
        except Exception:
            return len(text) // 4

    def _count_words(self, text: str) -> int:
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

    def _chunk_by_semantic_boundaries_unified(self, text: str, word_limit: int, 
                                            token_safety_limit: int, provider: str, model: str) -> List[Dict[str, any]]:
        """
        Unified semantic boundary chunking with word targeting and token validation.
        
        Args:
            text: Text to chunk
            word_limit: Target words per chunk
            token_safety_limit: Maximum tokens per chunk for safety
            provider: AI provider for token counting
            model: AI model for token counting
            
        Returns:
            List of chunk dictionaries with both word and token counts
        """
        # Detect paragraphs for semantic boundaries
        paragraphs = self._detect_paragraphs_from_text(text)
        
        chunks = []
        current_chunk_content = []
        current_chunk_words = 0
        chunk_number = 1
        
        for paragraph in paragraphs:
            paragraph_words = self._count_words(paragraph)
            
            # Check if paragraph exceeds reasonable limits
            if paragraph_words > self.MAX_PARAGRAPH_WORDS:
                # Save current chunk if it has content
                if current_chunk_content:
                    chunk_text = self._join_chunk_content(current_chunk_content)
                    validated_chunks = self._create_and_validate_chunk(
                        chunk_text, chunk_number, word_limit, token_safety_limit, provider, model)
                    chunks.extend(validated_chunks)
                    chunk_number += len(validated_chunks)
                    current_chunk_content = []
                    current_chunk_words = 0
                
                # Split oversized paragraph
                paragraph_chunks = self._split_oversized_content(
                    paragraph, word_limit, token_safety_limit, provider, model)
                for para_chunk in paragraph_chunks:
                    validated_chunks = self._create_and_validate_chunk(
                        para_chunk, chunk_number, word_limit, token_safety_limit, provider, model)
                    chunks.extend(validated_chunks)
                    chunk_number += len(validated_chunks)
                    
            # Check if adding paragraph would exceed word limit
            elif current_chunk_words + paragraph_words > word_limit and current_chunk_content:
                # Finalize current chunk
                chunk_text = self._join_chunk_content(current_chunk_content)
                validated_chunks = self._create_and_validate_chunk(
                    chunk_text, chunk_number, word_limit, token_safety_limit, provider, model)
                chunks.extend(validated_chunks)
                chunk_number += len(validated_chunks)
                
                # Start new chunk with current paragraph
                current_chunk_content = [paragraph]
                current_chunk_words = paragraph_words
            else:
                # Add paragraph to current chunk
                current_chunk_content.append(paragraph)
                current_chunk_words += paragraph_words
        
        # Handle final chunk
        if current_chunk_content:
            chunk_text = self._join_chunk_content(current_chunk_content)
            validated_chunks = self._create_and_validate_chunk(
                chunk_text, chunk_number, word_limit, token_safety_limit, provider, model)
            chunks.extend(validated_chunks)
        
        # Add semantic overlaps between chunks
        if self.SEMANTIC_OVERLAP and len(chunks) > 1:
            chunks = self._add_overlaps_unified(chunks, provider, model)
        
        logger.info(
            f"Split text into {len(chunks)} chunks using unified chunking (target: {word_limit} words), "
            f"total words: {sum(c.get('word_count', 0) for c in chunks)}, "
            f"total tokens: {sum(c.get('token_count', 0) for c in chunks)}")
        return chunks

    def _create_and_validate_chunk(self, chunk_text: str, chunk_number: int, 
                                  word_limit: int, token_safety_limit: int, provider: str, model: str) -> List[Dict[str, any]]:
        """
        Create chunk with both word and token validation, splitting if necessary.
        
        Args:
            chunk_text: Text to create chunk from
            chunk_number: Starting chunk number
            word_limit: Target words per chunk
            token_safety_limit: Maximum tokens allowed
            provider: AI provider for token counting
            model: AI model for token counting
            
        Returns:
            List of validated chunk dictionaries
        """
        word_count = self._count_words(chunk_text)
        token_count = self._safe_count_tokens(chunk_text, provider, model)
        
        # If within both limits, return single chunk
        if token_count <= token_safety_limit:
            return [self._create_chunk_unified(chunk_number, chunk_text, word_count, token_count)]
        
        # If exceeds token limit, split by sentences
        logger.warning(f"Chunk {chunk_number} ({word_count} words, {token_count} tokens) exceeds token limit, splitting")
        return self._split_by_sentences_unified(chunk_text, chunk_number, token_safety_limit, provider, model)

    def _split_oversized_content(self, content: str, word_limit: int, 
                               token_safety_limit: int, provider: str, model: str) -> List[str]:
        """
        Split oversized content at sentence boundaries respecting both word and token limits.
        
        Args:
            content: Content to split
            word_limit: Target words per chunk
            token_safety_limit: Maximum tokens per chunk
            provider: AI provider for token counting
            model: AI model for token counting
            
        Returns:
            List of content chunks
        """
        sentences = re.split(r'(?<=[.!?])\s+', content)
        chunks = []
        current_chunk = ""
        current_words = 0
        current_tokens = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            test_words = self._count_words(test_chunk)
            test_tokens = self._safe_count_tokens(test_chunk, provider, model)
            
            if (test_words > word_limit or test_tokens > token_safety_limit) and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
                current_words = self._count_words(sentence)
                current_tokens = self._safe_count_tokens(sentence, provider, model)
            else:
                current_chunk = test_chunk
                current_words = test_words
                current_tokens = test_tokens
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks

    def _split_by_sentences_unified(self, chunk_text: str, starting_chunk_number: int, 
                                  token_safety_limit: int, provider: str, model: str) -> List[Dict[str, any]]:
        """
        Split chunk by sentences to respect token limits.
        
        Args:
            chunk_text: Text to split
            starting_chunk_number: Starting chunk number
            token_safety_limit: Maximum tokens per chunk
            provider: AI provider for token counting
            model: AI model for token counting
            
        Returns:
            List of chunk dictionaries
        """
        sentences = re.split(r'(?<=[.!?])\s+', chunk_text)
        chunks = []
        current_chunk = ""
        current_chunk_tokens = 0
        chunk_number = starting_chunk_number
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            test_tokens = self._safe_count_tokens(test_chunk, provider, model)
            
            if test_tokens > token_safety_limit and current_chunk:
                # Finalize current chunk using cached token count
                word_count = self._count_words(current_chunk)
                chunks.append(self._create_chunk_unified(chunk_number, current_chunk.strip(), word_count, current_chunk_tokens))
                current_chunk = sentence
                current_chunk_tokens = self._safe_count_tokens(sentence, provider, model)
                chunk_number += 1
            else:
                current_chunk = test_chunk
                current_chunk_tokens = test_tokens
        
        # Handle final chunk using cached token count
        if current_chunk.strip():
            word_count = self._count_words(current_chunk)
            chunks.append(self._create_chunk_unified(chunk_number, current_chunk.strip(), word_count, current_chunk_tokens))
        
        return chunks

    def _create_chunk_unified(self, chunk_number: int, text: str, word_count: int, token_count: int) -> Dict[str, any]:
        """
        Create unified chunk dictionary with both word and token metadata.
        
        Args:
            chunk_number: Sequential chunk number
            text: Chunk text content
            word_count: Actual word count
            token_count: Actual token count
            
        Returns:
            Standardized chunk dictionary
        """
        return {
            'chunk_number': chunk_number,
            'raw_text': text.strip(),
            'word_count': word_count,
            'token_count': token_count,
            'character_count': len(text),
            'safety_validated': True
        }

    def _add_overlaps_unified(self, chunks: List[Dict[str, any]], provider: str, model: str) -> List[Dict[str, any]]:
        """
        Add unified word-based semantic overlaps between chunks.
        
        Args:
            chunks: List of chunk dictionaries
            provider: AI provider for token counting
            model: AI model for token counting
            
        Returns:
            Chunks with overlaps added
        """
        if len(chunks) <= 1:
            return chunks
        
        enhanced_chunks = [chunks[0]]  # First chunk unchanged
        
        for i in range(1, len(chunks)):
            current_chunk = chunks[i]
            previous_chunk = chunks[i-1]
            
            # Create overlap from previous chunk
            overlap_text = self._create_overlap_unified(previous_chunk['raw_text'])
            
            if overlap_text:
                # Prepend overlap to current chunk
                enhanced_text = overlap_text + "\n\n" + current_chunk['raw_text']
                
                # Recalculate counts
                new_word_count = self._count_words(enhanced_text)
                new_token_count = self._safe_count_tokens(enhanced_text, provider, model)
                
                enhanced_chunk = self._create_chunk_unified(
                    current_chunk['chunk_number'], enhanced_text, new_word_count, new_token_count)
                enhanced_chunks.append(enhanced_chunk)
            else:
                enhanced_chunks.append(current_chunk)
        
        return enhanced_chunks

    def _create_overlap_unified(self, text: str, max_words: int = None) -> str:
        """
        Create semantic overlap text based on word count at sentence boundaries.
        
        Args:
            text: Source text
            max_words: Maximum words in overlap (defaults to WORD_OVERLAP_SIZE)
            
        Returns:
            Overlap text ending at sentence boundary
        """
        max_words = max_words or self.WORD_OVERLAP_SIZE
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        if len(sentences) <= 1:
            return ""  # Not enough content for overlap
        
        # Build overlap from last sentences within word limit
        overlap_sentences = []
        overlap_words = 0
        
        for sentence in reversed(sentences[-3:]):  # Check last 3 sentences
            sentence_words = self._count_words(sentence)
            if overlap_words + sentence_words <= max_words:
                overlap_sentences.insert(0, sentence)
                overlap_words += sentence_words
            else:
                break
        
        if not overlap_sentences or overlap_words < 10:  # Minimum meaningful overlap
            return ""
        
        overlap_text = " ".join(overlap_sentences).strip()
        
        # Ensure reasonable overlap length
        if len(overlap_text) < 30 or len(overlap_text) > 300:
            return ""
        
        return overlap_text


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
