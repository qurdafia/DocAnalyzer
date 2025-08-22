# api/llm_providers/base.py
from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    def __init__(self, api_key, model_id):
        self.api_key = api_key
        self.model_id = model_id

    @abstractmethod
    def generate_analysis(self, prompt):
        pass