import json
import os
import time
from math import ceil
from typing import NamedTuple, Type

from api.generation import PROVIDER_MAP
from models.request import CallerInfo, GenerationConfig, GenerationRequest, PromptConfig
from models.response import GenerationResponse
from providers.base_provider import BaseProvider
from services.quota_manager import QuotaManager
from ulid import ULID
from utils.get_model_max_token import get_model_max_token

from .paragraph_extractor import ParagraphExtractor
from .prompt_templates import (
    COMBINED_AUTHOR_STYLE,
    PARTIAL_AUTHOR_STYLE,
    STRUCTURED_AUTHOR_STYLE,
)
from .token_counter import TokenCounter


class Passage(NamedTuple):
    source: str
    num: int
    text: str


class Style(NamedTuple):
    text: str
    token: int
    processing_time_ms: int
    passages: dict[str, list[int]]


class AuthorStyleConfiguration:
    def __init__(
        self,
        provider: str,
        model_name: str,
        paragraph_extractors: list[ParagraphExtractor],
        caller: CallerInfo,
        generation_config: GenerationConfig,
        quota_manager: QuotaManager,
        paragraph_overlap: bool = False,
        store_intermediate: bool = False,
    ):
        self.provider = provider
        self.model_name = model_name
        self.paragraph_extractors = paragraph_extractors
        self.caller = caller
        self.generation_config = generation_config
        self.quota_manager = quota_manager
        self.paragraph_overlap = paragraph_overlap
        self.store_intermediate = store_intermediate

        provider_class = PROVIDER_MAP.get(provider)
        if provider_class is None:
            raise ValueError(
                f"Unsupported provider: {provider}. Supported providers are: {list(PROVIDER_MAP.keys())}"
            )
        self.provider_class: Type[BaseProvider] = provider_class

        self.token_counter = TokenCounter(provider, model_name)
        self.model_max_token = get_model_max_token(provider, model_name) - 100
        self.partial_max_token = self.model_max_token - self.token_counter.count_tokens(
            PARTIAL_AUTHOR_STYLE
        )
        self.combined_max_token = (
            self.model_max_token
            - self.token_counter.count_tokens(COMBINED_AUTHOR_STYLE)
        )

        self.id = str(ULID())
        self.connection_pool = self.quota_manager.connection_pool
        self.sources = [
            os.path.basename(extractor.file_path) for extractor in paragraph_extractors
        ]

    def construct_passages(self) -> list[Passage]:
        all_paragraphs: dict[str, list[str]] = {}
        for i, source in enumerate(self.sources):
            extractor = self.paragraph_extractors[i]
            paragraphs = extractor.run()
            all_paragraphs[source] = paragraphs
            extractor.clear()

        token_counts: dict[str, list[int]] = {}
        for source, paragraphs in all_paragraphs.items():
            token_counts[source] = [
                self.token_counter.count_tokens(p) for p in paragraphs
            ]

        passages: list[Passage] = []
        for source in self.sources:
            passage: list[str] = []
            passage_num = 1
            token_count = 0
            index = 0
            while index < len(all_paragraphs[source]):
                paragraph = all_paragraphs[source][index]
                paragraph_token_count = token_counts[source][index]
                index += 1

                if (token_count + paragraph_token_count) < self.partial_max_token:
                    passage.append(paragraph)
                    token_count += paragraph_token_count
                    continue

                if passage:
                    passage_text = "".join(passage)
                    passages.append(Passage(source, passage_num, passage_text))

                if self.paragraph_overlap:
                    index -= 1
                    paragraph = all_paragraphs[source][index]
                    paragraph_token_count = token_counts[source][index]

                passage = [paragraph]
                passage_num += 1
                token_count = paragraph_token_count

            if passage:
                passage_text = "".join(passage)
                passages.append(Passage(source, passage_num, passage_text))

        return passages

    def _call_llm(self, prompt: str) -> GenerationResponse:
        remaining_quota = self.quota_manager.fetch(self.caller)
        if remaining_quota <= 0:
            raise RuntimeError("Insufficient quota for workspace.")

        provider_instance = self.provider_class(
            GenerationRequest(
                prompt=prompt,
                provider=self.provider,
                model=self.model_name,
                caller=self.caller,
                prompt_config=PromptConfig(),
                generation_config=self.generation_config,
            )
        )

        response = provider_instance.generate()
        if not response.success:
            raise RuntimeError(f"LLM call failed: {response.error_message}")

        self.quota_manager.update(self.caller)

        return response

    def _store_intermediate_style(self, style: Style) -> None:
        if not self.store_intermediate:
            return
        try:
            with self.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO intermediate_styles (id, structured_style_id, style, processing_time_ms, passages)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            str(ULID()),
                            self.id,
                            style.text,
                            style.processing_time_ms,
                            json.dumps(style.passages),
                        ),
                    )
                    conn.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to store intermediate style: {str(e)}")

    def _store_structured_style(
        self, data: dict, started_at: str, total_time_ms: int
    ) -> None:
        try:
            with self.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO structured_styles (id, user_id, workspace_id, project_id, style, started_at, total_time_ms, sources)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            self.id,
                            self.caller.user_id,
                            self.caller.workspace_id,
                            self.caller.project_id,
                            json.dumps(data),
                            started_at,
                            total_time_ms,
                            ", ".join(self.sources),
                        ),
                    )
                    conn.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to store structured style: {str(e)}")

    def _merge_style_passage(self, styles: list[Style]) -> dict[str, list[int]]:
        merged_passages: dict[str, list[int]] = {}
        for style in styles:
            for source, nums in style.passages.items():
                if source not in merged_passages:
                    merged_passages[source] = []
                merged_passages[source].extend(nums)
        return merged_passages

    def _handle_partial_style(self, passage: Passage) -> Style:
        prompt = PARTIAL_AUTHOR_STYLE.format(text=passage.text)
        response = self._call_llm(prompt)
        title = f"PASSAGE {passage.num} from FILE {passage.source}\n\n"
        style = Style(
            text=title + response.text,
            token=response.metadata.output_tokens,
            processing_time_ms=response.metadata.processing_time_ms,
            passages={passage.source: [passage.num]},
        )
        self._store_intermediate_style(style)
        return style

    def _handle_combined_style(
        self, styles: list[Style], recursion_depth: int = 0
    ) -> Style:
        if recursion_depth > 5:
            raise RuntimeError("Recursion depth exceeded while combining styles")

        total_token = sum(s.token for s in styles)
        if total_token < self.combined_max_token:
            prompt = COMBINED_AUTHOR_STYLE.format(
                text="\n\n".join([s.text for s in styles])
            )
            response = self._call_llm(prompt)
            title = "Analyzed Author Style from Multiple (but possibly not all) PASSAGEs and FILEs\n\n"
            style = Style(
                text=title + response.text,
                token=response.metadata.output_tokens,
                passages=self._merge_style_passage(styles),
                processing_time_ms=response.metadata.processing_time_ms,
            )
            self._store_intermediate_style(style)
            return style

        n_splits = ceil(total_token / self.combined_max_token)
        style_base_count = len(styles) // n_splits
        style_remainder = len(styles) % n_splits
        reduced_styles: list[Style] = []
        for i in range(n_splits):
            start = i * style_base_count + min(i, style_remainder)
            end = start + style_base_count + (1 if i < style_remainder else 0)
            combined_style = self._handle_combined_style(
                styles[start:end], recursion_depth + 1
            )
            reduced_styles.append(combined_style)

        return self._handle_combined_style(reduced_styles, recursion_depth + 1)

    def run(self) -> dict:
        start_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        start_time = time.monotonic()

        passages = self.construct_passages()
        styles = [self._handle_partial_style(passage) for passage in passages]
        combined_style = self._handle_combined_style(styles)

        prompt = STRUCTURED_AUTHOR_STYLE.format(text=combined_style)
        response = self._call_llm(prompt)
        data = json.loads(response.text)

        total_time_ms = int((time.monotonic() - start_time) * 1000)
        self._store_structured_style(data, start_at, total_time_ms)

        return data
