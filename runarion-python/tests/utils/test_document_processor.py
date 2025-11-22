import os
import sys

# Add src to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import pytest
from src.utils.document_processor import Chunk, DocumentProcessor


class TestDocumentProcessor:
    """Test suite for DocumentProcessor class."""

    SAMPLE_DIR = "tests/sample/input"

    @pytest.fixture
    def check_exceed_limits(self):
        """Fixture to provide check_exceed_limits helper function."""

        def _check_exceed_limits(chunks: list[Chunk], processor: DocumentProcessor):
            token_limit = processor.chunk_token_limit
            word_limit = processor.chunk_word_limit
            for i, chunk in enumerate(chunks):
                if token_limit is not None and chunk["token_count"] > token_limit:
                    pytest.fail(
                        f"Chunk {i} exceeds token limit: {chunk['token_count']} > {token_limit}"
                    )
                if word_limit is not None and chunk["word_count"] > word_limit:
                    pytest.fail(
                        f"Chunk {i} exceeds word limit: {chunk['word_count']} > {word_limit}"
                    )

        return _check_exceed_limits

    def test_split_into_sentences(self):
        """Test sentence splitting functionality."""
        text = 'He said "Hello there!"    Then I answered \'How are you?\'    Then he replied "I\'m doing great." We just do a nice conversations!     I like him.'
        sentences = DocumentProcessor.split_into_sentences(text)
        assert isinstance(sentences, list)
        assert len(sentences) > 0
        assert all(isinstance(s, str) for s in sentences)

    def test_processor_gemini_default_settings_no_error(self, check_exceed_limits):
        """Test DocumentProcessor with Gemini model and default settings."""
        processor = DocumentProcessor(
            "gemini",
            "gemini-2.5-flash",
            model_token_safety_margin=0.5,
            chunk_token_limit=None,
            chunk_word_limit=None,
            sentence_overlap=0,
        )
        assert processor.chunk_token_limit > 0

        text = processor.document_reader.extract(
            f"{self.SAMPLE_DIR}/short_sample_1.pdf"
        )
        chunks = processor.chunk_text(text)

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        check_exceed_limits(chunks, processor)

    def test_processor_roberta_with_limits_and_overlap(self, check_exceed_limits):
        """Test DocumentProcessor with roberta-base model, custom limits and overlap."""
        processor = DocumentProcessor(
            "other",
            "roberta-base",
            model_token_safety_margin=0.5,
            chunk_token_limit=1000,
            chunk_word_limit=1000,
            sentence_overlap=2,
        )
        assert processor.chunk_token_limit < 1000
        assert processor.chunk_token_limit == processor.conservative_limit

        text = processor.document_reader.extract(
            f"{self.SAMPLE_DIR}/short_sample_1.pdf"
        )
        chunks = processor.chunk_text(text)

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        check_exceed_limits(chunks, processor)

    def test_processor_gemini_small_token_limit_with_overlap(self, check_exceed_limits):
        """Test DocumentProcessor with small token limit and sentence overlap."""
        processor = DocumentProcessor(
            "gemini",
            "gemini-2.5-flash",
            model_token_safety_margin=0.5,
            chunk_token_limit=100,
            chunk_word_limit=None,
            sentence_overlap=1,
        )
        assert processor.chunk_token_limit == 100

        text = processor.document_reader.extract(
            f"{self.SAMPLE_DIR}/short_sample_0.docx"
        )
        chunks = processor.chunk_text(text)

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        check_exceed_limits(chunks, processor)

    def test_processor_gemini_word_limit_with_overlap(self, check_exceed_limits):
        """Test DocumentProcessor with word limit and sentence overlap."""
        processor = DocumentProcessor(
            "gemini",
            "gemini-2.5-flash",
            model_token_safety_margin=0.5,
            chunk_token_limit=None,
            chunk_word_limit=500,
            sentence_overlap=2,
        )
        assert processor.chunk_token_limit > 0

        text = processor.document_reader.extract(
            f"{self.SAMPLE_DIR}/short_sample_0.docx"
        )
        chunks = processor.chunk_text(text)

        assert isinstance(chunks, list)
        assert len(chunks) > 0
        check_exceed_limits(chunks, processor)

    def test_chunk_structure(self):
        """Test that chunks have the expected structure."""
        processor = DocumentProcessor(
            "gemini",
            "gemini-2.5-flash",
            model_token_safety_margin=0.5,
            chunk_token_limit=None,
            chunk_word_limit=None,
            sentence_overlap=0,
        )

        text = processor.document_reader.extract(
            f"{self.SAMPLE_DIR}/short_sample_1.pdf"
        )
        chunks = processor.chunk_text(text)

        # Verify chunk structure
        for chunk in chunks:
            assert "chunk_number" in chunk
            assert "raw_text" in chunk
            assert "token_count" in chunk
            assert "word_count" in chunk
            assert "character_count" in chunk
            assert isinstance(chunk["chunk_number"], int)
            assert isinstance(chunk["raw_text"], str)
            assert isinstance(chunk["token_count"], int)
            assert isinstance(chunk["word_count"], int)
            assert isinstance(chunk["character_count"], int)
            assert chunk["token_count"] > 0
            assert chunk["word_count"] > 0
            assert chunk["character_count"] > 0
