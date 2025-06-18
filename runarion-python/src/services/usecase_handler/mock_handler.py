# services/usecase_handler/mock_handler.py

from services.usecase_handler.base_handler import UseCaseHandler
from models.request import BaseGenerationRequest

class MockHandler(UseCaseHandler):
    """
    A no‑op handler for smoke‑testing. It expects the caller to supply a body that
    already matches BaseGenerationRequest.
    """
    def build_request(self, raw_json: dict) -> BaseGenerationRequest:
        # Directly cast to BaseGenerationRequest class
        return BaseGenerationRequest(**raw_json)