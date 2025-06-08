import warnings
from math import ceil

import pymupdf


class ParagraphExtractor:
    def __init__(
        self,
        file_path: str,
        start_page: int = 0,
        end_page: int | None = None,
        min_char_len: int = 150,
        max_char_len: int = 5000,
        sentence_endings: list[str] | None = None,
    ):
        self.file_path = file_path
        self.start_page = start_page
        self.end_page = end_page
        self.min_char_len = min_char_len
        self.max_char_len = max_char_len

        default_endings = [".", "!", "?"]
        default_endings = (
            default_endings
            + [e + "'" for e in default_endings]
            + [e + '"' for e in default_endings]
        )
        self.sentence_endings = sentence_endings or default_endings

        self.paragraphs: list[str] = []
        self.temp_paragraph = ""

    def read_file(self) -> pymupdf.Document:
        return pymupdf.open(self.file_path)

    def split_paragraph(self, text: str, max_len: int | None = None) -> list[str]:
        if max_len is None:
            max_len = self.max_char_len

        n_splits = ceil(len(text) / max_len)
        if n_splits == 1:
            return [text]

        splits: list[str] = []
        start = 0
        len_split = round(len(text) / n_splits)
        for _ in range(n_splits):
            ref_ends = [
                text.find(e + " ", start + len_split) for e in self.sentence_endings
            ]
            ref_end = min([e for e in ref_ends if e != -1], default=-1)
            if ref_end == -1:
                splits.append(text[start:])
                break
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
        if len(self.paragraphs) == 0:
            self.paragraphs.extend(self.split_paragraph(text))
            return

        if not any(
            self.paragraphs[-1].strip().endswith(e) for e in self.sentence_endings
        ):
            last_paragraph = self.paragraphs.pop()
            self.paragraphs.extend(self.split_paragraph(last_paragraph + text))
            return

        if len(text) < self.min_char_len:
            self.temp_paragraph += text
            return

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

        self.paragraphs.extend(self.split_paragraph(text))

    def run(self) -> list[str]:
        doc = self.read_file()
        warnings.simplefilter("once", UserWarning)
        for page in doc[self.start_page : self.end_page]:
            blocks = page.get_text("blocks")  # type: ignore
            for block in blocks:
                if block[6] != 0:
                    continue
                self._handle_paragraph(block[4])
        warnings.simplefilter("default", UserWarning)
        return self.paragraphs

    def clear(self):
        self.paragraphs.clear()
        self.temp_paragraph = ""
