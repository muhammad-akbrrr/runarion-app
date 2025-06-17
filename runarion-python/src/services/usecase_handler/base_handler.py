# services/usecase_handler/base_handler.py

from abc import ABC, abstractmethod
from models.request import BaseGenerationRequest

class UseCaseHandler(ABC):
    @abstractmethod
    def build_request(self, raw_json: dict) -> BaseGenerationRequest:
        pass
