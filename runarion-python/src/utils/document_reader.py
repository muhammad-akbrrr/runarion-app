import logging
import re
from pathlib import Path
from typing import Tuple

import fitz  # PyMuPDF
from docx import Document

logger = logging.getLogger(__name__)


class DocumentReader:
    """
    Utility class for reading text from various document formats and cleaning the text.
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".docx", ".doc"}

    def extract(self, file_path: str) -> str:
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
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {extension}")

        try:
            if extension == ".pdf":
                return self._extract_from_pdf(path)
            elif extension == ".txt":
                return self._extract_from_txt(path)
            elif extension in [".docx", ".doc"]:
                return self._extract_from_docx(path)
            else:
                raise ValueError(f"Unsupported file format: {extension}")
        except Exception as e:
            logger.error(f"Failed to extract text from {path}: {str(e)}")
            raise

    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file using PyMuPDF and handle paragraph breaks."""
        endings = [".", "!", "?"]
        endings = endings + [e + "'" for e in endings] + [e + '"' for e in endings]

        paragraphs: list[str] = []
        temp_paragraph = ""
        with fitz.open(str(file_path)) as doc:
            for page in doc:
                # get text blocks from the page and skip image blocks
                blocks = page.get_text("blocks")  # type: ignore
                texts: list[str] = [
                    block[4].strip() for block in blocks if block[6] == 0
                ]

                # remove empty strings
                texts = [text for text in texts if text]
                if not texts:
                    continue

                # remove first and last block if it's a page number
                if texts[0].isdigit():
                    texts.pop(0)
                if texts[-1].isdigit():
                    texts.pop()

                for i, text in enumerate(texts):
                    # handle paragraph break at end of page
                    if i == len(texts) - 1 and not text.endswith(tuple(endings)):
                        temp_paragraph = text
                        continue
                    paragraphs.append(temp_paragraph + " " + text)
                    temp_paragraph = ""

        # clean line breaks inside paragraphs
        paragraphs = [
            p.replace("\n", " ").replace("\r", " ").strip() for p in paragraphs
        ]

        # Join paragraphs with double line breaks to maintain structure
        return "\n\n".join(paragraphs)

    def _extract_from_txt(self, file_path: Path) -> str:
        """Extract text from TXT file with encoding detection."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, "r", encoding="latin-1") as file:
                return file.read()

    def _extract_from_docx(self, file_path: Path) -> str:
        """Extract text from DOCX file."""
        doc = Document(str(file_path))

        paragraphs = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                paragraphs.append(paragraph.text)

        return "\n\n".join(paragraphs)

    def clean(self, text: str) -> str:
        """
        Clean and normalize extracted text.

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text
        """
        # Remove excessive horizontal whitespaces
        text = re.sub(r"[ \t]+", " ", text)

        # Remove excessive line breaks
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

        # Remove spaces before and after line breaks
        text = re.sub(r"\s*\n\n\s*", "\n\n", text)

        # Remove zero-width characters
        text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate file before processing.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (is_valid, error_message)
        """
        path = Path(file_path)

        if not path.exists():
            return False, f"File not found: {path}"

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return False, f"Unsupported file format: {path.suffix}"

        # Check file size (100MB limit)
        if path.stat().st_size > 100 * 1024 * 1024:
            return False, "File too large (max 100MB)"

        return True, ""
