from contextlib import contextmanager

from flask import Flask

from src.models.request import (
    BaseGenerationRequest,
    CallerInfo,
    GenerationConfig,
    QuotaContext,
)
from src.providers.base_provider import BaseProvider


class _RecordingCursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params):
        self.executed.append((query, params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _RecordingConnection:
    def __init__(self):
        self.cursor_obj = _RecordingCursor()
        self.commits = 0

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1


class _RecordingQuotaManager:
    def __init__(self):
        self.connection = _RecordingConnection()
        self.reserve_calls = []
        self.finalize_calls = []

    def reserve_tokens(self, caller, estimated_tokens, quota_mode="strict", workflow_id=None):
        self.reserve_calls.append(
            {
                "caller": caller,
                "estimated_tokens": estimated_tokens,
                "quota_mode": quota_mode,
                "workflow_id": workflow_id,
            }
        )
        return {
            "workspace_usage_period_id": "period-1",
            "reserved_tokens": estimated_tokens,
        }

    def finalize_usage(self, reservation, actual_total_tokens):
        self.finalize_calls.append(
            {
                "reservation": reservation,
                "actual_total_tokens": actual_total_tokens,
            }
        )

    @contextmanager
    def get_connection(self):
        yield self.connection


class _TestProvider(BaseProvider):
    def __init__(self, request):
        self._quota_manager = _RecordingQuotaManager()
        super().__init__(request)

    def _get_quota_manager(self):
        return self._quota_manager

    def _resolve_api_key(self):
        return "test-key", "default"

    def _resolve_model(self):
        return self.request.model or "gpt-4o-mini"

    def generate(self, skip_quota: bool = False):
        raise NotImplementedError

    def generate_stream(self):
        raise NotImplementedError


def _build_request(provider="openai", thinking_budget=None, quota_mode="strict"):
    return BaseGenerationRequest(
        usecase="test_usecase",
        feature="test_feature",
        provider=provider,
        model="gpt-4o-mini" if provider == "openai" else "gemini-2.5-flash",
        prompt="Hello world",
        instruction="Test instruction",
        generation_config=GenerationConfig(
            max_output_tokens=100,
            thinking_budget=thinking_budget,
        ),
        caller=CallerInfo(
            user_id="1",
            workspace_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            project_id="01ARZ3NDEKTSV4RRFFQ69G5FAA",
            session_id="session-1",
            api_keys={},
        ),
        quota_context=QuotaContext(
            mode=quota_mode,
            workflow_id="workflow-1",
            workflow_kind="test_workflow",
        ),
    )


def test_normalize_usage_derives_reasoning_tokens_from_total():
    provider = _TestProvider(_build_request(provider="openai"))

    usage = provider._normalize_usage(
        generated_text="hello",
        provider_input_tokens=100,
        provider_output_tokens=40,
        provider_total_tokens=170,
        usage_source="provider",
    )

    assert usage["reasoning_tokens"] == 30
    assert usage["billable_reasoning_tokens"] == 30
    assert usage["billable_total_tokens"] == 170
    assert usage["token_basis"] == "openai"


def test_begin_usage_metering_reserves_thinking_budget_for_gemini():
    provider = _TestProvider(_build_request(provider="gemini", thinking_budget=256, quota_mode="admitted_workflow"))

    provider._begin_usage_metering()

    reserve_call = provider.quota_manager.reserve_calls[0]
    assert reserve_call["estimated_tokens"] > 356
    assert reserve_call["quota_mode"] == "admitted_workflow"
    assert reserve_call["workflow_id"] == "workflow-1"


def test_log_generation_to_db_writes_extended_usage_fields():
    app = Flask(__name__)
    provider = _TestProvider(_build_request(provider="openai"))
    normalized = provider._normalize_usage(
        generated_text="Generated response",
        provider_input_tokens=10,
        provider_output_tokens=5,
        provider_total_tokens=17,
        usage_source="provider",
    )
    billable_usage = provider._finalize_usage_metering("Generated response", normalized_usage=normalized)

    with app.app_context():
        response = provider._build_response(
            generated_text="Generated response",
            request_id="550e8400-e29b-41d4-a716-446655440000",
            provider_request_id="provider-1",
            input_tokens=normalized["input_tokens"],
            output_tokens=normalized["output_tokens"],
            reasoning_tokens=normalized["reasoning_tokens"],
            total_tokens=normalized["total_tokens"],
            usage_source=normalized["usage_source"],
        )
        provider._log_generation_to_db(response, billable_usage=billable_usage)

    executed = provider.quota_manager.connection.cursor_obj.executed
    assert len(executed) == 1
    query, params = executed[0]
    assert "reasoning_tokens" in query
    assert "billable_reasoning_tokens" in query
    assert "quota_mode" in query
    assert "workflow_id" in query
    assert len(params) == 31
