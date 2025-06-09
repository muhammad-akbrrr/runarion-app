# providers/story_generation/base_provider.py

from flask import current_app
from models.story_generation.request import StoryGenerationRequest
from models.story_generation.response import StoryGenerationResponse
from models.response import UsageMetadata, QuotaMetadata
from utils.instruction_builder import InstructionBuilder
from services.quota_manager import QuotaManager
from providers.base_provider import BaseProvider

class StoryGenerationBaseProvider(BaseProvider):
    def __init__(self, request: StoryGenerationRequest):
        super().__init__(request)
        self.instruction = self._build_instruction()
        self.quota_manager = self._get_quota_manager()
        self.remaining_quota = None

    def _get_quota_manager(self) -> QuotaManager:
        return QuotaManager()

    def _check_quota(self):
        self.remaining_quota = self.quota_manager.check_quota(self.request.caller)

    def _update_quota(self, quota_generation_count: int):
        self.quota_manager.update_quota(
            caller=self.request.caller,
            expected_quota=self.remaining_quota,
            quota_generation_count=quota_generation_count
        )

    def _build_instruction(self) -> str:
        builder = InstructionBuilder(self.request.prompt_config)
        instruction = builder.build() if self.request.prompt.strip() else builder.build_from_scratch()
        return instruction.strip()

    def _build_response(self, generated_text: str, finish_reason: str, input_tokens: int,
                        output_tokens: int, total_tokens: int, processing_time_ms: int,
                        request_id: str, quota_generation_count: int,
                        provider_request_id: str = "") -> StoryGenerationResponse:

        metadata = UsageMetadata(
            finish_reason=finish_reason,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            processing_time_ms=processing_time_ms,
        )

        quota = QuotaMetadata(
            user_id=self.request.caller.user_id,
            workspace_id=self.request.caller.workspace_id,
            project_id=self.request.caller.project_id,
            generation_count=quota_generation_count,
        )

        return StoryGenerationResponse(
            success=True,
            text=generated_text,
            provider=self.request.provider,
            model_used=self.model,
            key_used=self.key_used,
            request_id=request_id,
            provider_request_id=provider_request_id,
            metadata=metadata,
            quota=quota,
        )

    def _build_error_response(self, request_id: str, provider_request_id: str = "",
                              error_message: str = "An error occurred during generation.") -> StoryGenerationResponse:

        metadata = UsageMetadata(
            finish_reason="error",
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            processing_time_ms=0,
        )

        quota = QuotaMetadata(
            user_id=self.request.caller.user_id,
            workspace_id=self.request.caller.workspace_id,
            project_id=self.request.caller.project_id,
            generation_count=0,
        )

        return StoryGenerationResponse(
            success=False,
            text="",
            provider=self.request.provider,
            model_used=self.model,
            key_used=self.key_used,
            request_id=request_id,
            provider_request_id=provider_request_id,
            metadata=metadata,
            quota=quota,
            error_message=error_message
        )

    def _log_generation_to_db(self, response: StoryGenerationResponse):
        try:
            with self.quota_manager.connection_pool.getconn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO generation_logs (
                            request_id, user_id, workspace_id, project_id, provider,
                            model_used, key_used, prompt, instruction, generated_text,
                            success, finish_reason, input_tokens, output_tokens, total_tokens,
                            processing_time_ms, error_message, created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, NOW()
                        )
                    """, (
                        response.request_id,
                        int(response.quota.user_id),
                        response.quota.workspace_id,
                        response.quota.project_id,
                        response.provider,
                        response.model_used,
                        response.key_used,
                        self.request.prompt or "",
                        self.instruction or "",
                        response.text or "",
                        response.success,
                        response.metadata.finish_reason,
                        response.metadata.input_tokens,
                        response.metadata.output_tokens,
                        response.metadata.total_tokens,
                        response.metadata.processing_time_ms,
                        response.error_message
                    ))
                    conn.commit()
        except Exception as e:
            current_app.logger.error(f"Failed to log generation to DB: {e}")
