import warnings
from math import ceil
from typing import Optional

import pymupdf


class ParagraphExtractor:
    """
    Extracts paragraphs from a PDF file while adhering to constraints
    such as minimum and maximum character lengths and sentence endings.
    """

    def __init__(
        self,
        file_path: str,
        start_page: int = 1,
        end_page: Optional[int] = None,
        min_char_len: Optional[int] = None,
        max_char_len: Optional[int] = None,
        sentence_endings: Optional[list[str]] = None,
    ):
        """
        Args:
            file_path (str): Path to the PDF file.
            start_page (int): Page number to start extraction from.
            end_page (Optional[int]): Page number to stop extraction at. None means till the last page.
            min_char_len (Optional[int]): Minimum character length for a paragraph, defaults to 150.
            max_char_len (Optional[int]): Maximum character length for a paragraph, defaults to 5000.
            sentence_endings (Optional[list[str]]): Sentence ending characters to identify paragraph endings and split paragraphs. Defaults to ".", "!", "?", and their variations within quotes.
        """
        self.file_path = file_path
        self.start_page = start_page
        self.end_page = end_page
        self.min_char_len = min_char_len or 150
        self.max_char_len = max_char_len or 5000

        default_endings = [".", "!", "?"]
        default_endings = (
            default_endings
            + [e + "'" for e in default_endings]
            + [e + '"' for e in default_endings]
        )
        self.sentence_endings = sentence_endings or default_endings

        self.paragraphs: list[str] = []
        self.temp_paragraph = ""  # temporary buffer for short paragraphs

    def read_file(self) -> pymupdf.Document:
        """
        Opens the PDF file using pymupdf.

        Returns:
            pymupdf.Document: The opened PDF document.
        """
        return pymupdf.open(self.file_path)

    def split_paragraph(self, text: str, max_len: Optional[int] = None) -> list[str]:
        """
        Splits a long paragraph based on the maximum length and sentence endings.

        Args:
            text (str): The paragraph text to split.
            max_len (Optional[int]): Maximum length of each split. Defaults to `self.max_char_len`.

        Returns:
            list[str]: List of split paragraphs.
        """
        if max_len is None:
            max_len = self.max_char_len

        n_splits = ceil(len(text) / max_len)
        if n_splits == 1:
            return [text]

        splits: list[str] = []
        start = 0
        len_split = round(len(text) / n_splits)  # approximate length of each split
        for _ in range(n_splits):
            # find the next sentence ending after the start position
            ref_ends = [
                text.find(e + " ", start + len_split) for e in self.sentence_endings
            ]
            ref_end = min([e for e in ref_ends if e != -1], default=-1)

            # if not found, take the rest of the text
            if ref_end == -1:
                splits.append(text[start:])
                break

            # if found, split and update the start position
            ending = self.sentence_endings[ref_ends.index(ref_end)]
            splits.append(text[start : ref_end + len(ending)])
            start = ref_end + len(ending) + 1

        if any(len(split) > max_len for split in splits):
            warnings.warn(
                "One or multiple paragraph splits are longer than the maximum length due to long sentences",
                UserWarning,
            )

        return splits

    def _handle_paragraph(self, text: str):
        """
        Processes a block of text and appends it to `self.paragraphs`,
        handling cases where the text is too long, too short, or not ended properly.

        Args:
            text (str): The text block to process.
        """
        # if the paragraphs is empty, just add the texts
        if len(self.paragraphs) == 0:
            self.paragraphs.extend(self.split_paragraph(text))
            return

        # if the last paragraph does not end with a sentence ending, append to it
        if not any(
            self.paragraphs[-1].strip().endswith(e) for e in self.sentence_endings
        ):
            last_paragraph = self.paragraphs.pop()
            self.paragraphs.extend(self.split_paragraph(last_paragraph + text))
            return

        # if the text is too short, put it to the temporary paragraph buffer
        if len(text) < self.min_char_len:
            self.temp_paragraph += text
            return

        # if the temporary paragraph buffer is long enough, add it to the paragraphs, otherwise append to the last paragraph
        if len(self.temp_paragraph) >= self.min_char_len:
            self.paragraphs.extend(self.split_paragraph(self.temp_paragraph))
        else:
            self.paragraphs[-1] += self.temp_paragraph
            if len(self.paragraphs[-1]) > self.max_char_len:
                warnings.warn(
                    "One or multiple paragraphs are unavoidably longer than the maximum length",
                    UserWarning,
                )
        self.temp_paragraph = ""

        # just add the texts to the paragraphs
        self.paragraphs.extend(self.split_paragraph(text))

    def run(self) -> list[str]:
        """
        Runs the paragraph extraction process.

        Returns:
            list[str]: List of extracted paragraphs.
        """
        doc = self.read_file()

        warnings.simplefilter("once", UserWarning)
        for page in doc[self.start_page - 1 : self.end_page]:
            blocks = page.get_text("blocks")  # type: ignore
            for block in blocks:
                # skip non-text blocks
                if block[6] != 0:
                    continue
                # process the text block
                self._handle_paragraph(block[4])
        warnings.simplefilter("default", UserWarning)

        return self.paragraphs

    def clear(self):
        """
        Clears the extracted paragraphs and temporary paragraph buffer.
        """
        self.paragraphs.clear()
        self.temp_paragraph = ""
