import os
import sys

# Add src to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import pytest
from src.utils.document_reader import DocumentReader


class TestDocumentReader:
    """Test suite for DocumentReader class."""

    SAMPLE_DIR = "tests/sample/input"

    @pytest.fixture
    def reader(self):
        """Fixture to create a DocumentReader instance."""
        return DocumentReader()

    def test_extract_docx_no_error(self, reader):
        """Test extracting text from DOCX file."""
        result = reader.extract(f"{self.SAMPLE_DIR}/short_sample_0.docx")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_extract_pdf_no_error(self, reader):
        """Test extracting text from PDF file."""
        result = reader.extract(f"{self.SAMPLE_DIR}/short_sample_1.pdf")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_extract_txt_no_error(self, reader):
        """Test extracting text from TXT file."""
        result = reader.extract(f"{self.SAMPLE_DIR}/short_sample_3.txt")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_clean_excessive_whitespace(self, reader):
        """Test cleaning excessive whitespace."""
        input_text = "  Hello   World!   This is   a test.  "
        expected_output = "Hello World! This is a test."
        actual_output = reader.clean(input_text)
        assert actual_output == expected_output

    def test_clean_excessive_line_breaks(self, reader):
        """Test cleaning excessive line breaks."""
        input_text = "Line 1\n\n\n\nLine 2\n\nLine 3"
        expected_output = "Line 1\n\nLine 2\n\nLine 3"
        actual_output = reader.clean(input_text)
        assert actual_output == expected_output

    def test_clean_zero_width_characters(self, reader):
        """Test cleaning zero-width characters."""
        input_text = "Text with\u200bzero\u200cwidth\u200dchars\ufeff."
        expected_output = "Text withzerowidthchars."
        actual_output = reader.clean(input_text)
        assert actual_output == expected_output

    def test_clean_combination_of_issues(self, reader):
        """Test cleaning combination of all issues."""
        input_text = (
            "  First line.  \n\n\nSecond\u200bline.  \n\n\n\n\n\nEnd of text.   "
        )
        expected_output = "First line.\n\nSecondline.\n\nEnd of text."
        actual_output = reader.clean(input_text)
        assert actual_output == expected_output

    def test_clean_empty_string(self, reader):
        """Test cleaning empty string."""
        input_text = ""
        expected_output = ""
        actual_output = reader.clean(input_text)
        assert actual_output == expected_output

    def test_clean_whitespace_only_string(self, reader):
        """Test cleaning string with only whitespace."""
        input_text = "   \n \t  "
        expected_output = ""
        actual_output = reader.clean(input_text)
        assert actual_output == expected_output
