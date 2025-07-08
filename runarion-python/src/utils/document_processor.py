"""
Document processor utility for handling file uploads and content extraction.
Supports PDF, TXT, and DOCX files with intelligent chunking for large documents.
"""

import os
import re
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import fitz  # PyMuPDF
from docx import Document
from .get_model_max_token import get_model_max_token, count_tokens, chunk_text_by_tokens, get_safe_max_tokens

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Handles document ingestion, extraction, and chunking for the novel pipeline.
    """
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.doc'}
    DEFAULT_CHUNK_SIZE = 4000  # Conservative token limit for chunking
    OVERLAP_SIZE = 200  # Overlap between chunks to maintain context
    
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
            else:
                raise ValueError(f"Unsupported file format: {extension}")
        
        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {str(e)}")
            raise
    
    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file using PyMuPDF."""
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
            safe_max_tokens = get_safe_max_tokens(provider, model, safety_margin=0.2)
            # Use conservative chunk size (25% of safe limit)
            chunk_size = max_chunk_size or min(self.DEFAULT_CHUNK_SIZE, safe_max_tokens // 4)
        except Exception as e:
            logger.warning(f"Could not get token limit for {provider}/{model}: {e}")
            chunk_size = max_chunk_size or self.DEFAULT_CHUNK_SIZE
        
        # Use proper tokenizer-based chunking
        try:
            text_chunks = chunk_text_by_tokens(text, chunk_size, provider, model, overlap_tokens=50)
            
            chunks = []
            for i, chunk_text in enumerate(text_chunks, 1):
                # Get accurate token count for the chunk
                actual_token_count = count_tokens(chunk_text, provider, model)
                
                chunks.append({
                    'chunk_number': i,
                    'raw_text': chunk_text.strip(),
                    'token_count': actual_token_count,
                    'character_count': len(chunk_text)
                })
            
            logger.info(f"Split text into {len(chunks)} chunks using proper tokenizer, total tokens: {sum(c['token_count'] for c in chunks)}")
            return chunks
            
        except Exception as e:
            logger.warning(f"Tokenizer-based chunking failed, falling back to sentence-based: {e}")
            return self._chunk_text_fallback(text, chunk_size, provider, model)
    
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
        # Split text into sentences for better chunking
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        chunk_number = 1
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Use proper token counting for sentence
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            try:
                test_tokens = count_tokens(test_chunk, provider, model)
            except Exception:
                # Fallback to character-based estimation if tokenizer fails
                test_tokens = len(test_chunk) // 4
            
            # Check if adding this sentence would exceed chunk size
            if test_tokens > chunk_size and current_chunk:
                # Get accurate token count for current chunk
                try:
                    current_tokens = count_tokens(current_chunk, provider, model)
                except Exception:
                    current_tokens = len(current_chunk) // 4
                
                # Save current chunk
                chunks.append({
                    'chunk_number': chunk_number,
                    'raw_text': current_chunk.strip(),
                    'token_count': current_tokens,
                    'character_count': len(current_chunk)
                })
                
                # Start new chunk with current sentence
                current_chunk = sentence
                chunk_number += 1
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        # Add final chunk if it has content
        if current_chunk.strip():
            try:
                final_tokens = count_tokens(current_chunk, provider, model)
            except Exception:
                final_tokens = len(current_chunk) // 4
                
            chunks.append({
                'chunk_number': chunk_number,
                'raw_text': current_chunk.strip(),
                'token_count': final_tokens,
                'character_count': len(current_chunk)
            })
        
        logger.info(f"Split text into {len(chunks)} chunks using fallback method, total tokens: {sum(c['token_count'] for c in chunks)}")
        return chunks
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """
        Get the last portion of text for overlap between chunks.
        
        Args:
            text: Source text
            overlap_size: Number of characters for overlap
            
        Returns:
            Overlap text
        """
        if len(text) <= overlap_size:
            return text
        
        # Try to find a sentence boundary within overlap range
        overlap_text = text[-overlap_size:]
        sentence_start = overlap_text.find('. ')
        
        if sentence_start > 0:
            return overlap_text[sentence_start + 2:]
        
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
            logger.error(f"Document processing failed for {file_path}: {str(e)}")
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