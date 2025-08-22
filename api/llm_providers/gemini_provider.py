# api/llm_providers/gemini_provider.py
import json
from .base import BaseLLMProvider
from .requests_provider import RequestsProvider
from api.utils import parse_gemini_response


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key, model_id, config):
        super().__init__(api_key, model_id)
        self.config = config
        # --- THIS IS THE FIX ---
        # Initialize the HTTP client with SSL verification turned OFF for development
        self.http_client = RequestsProvider(verify=False)

    def generate_analysis(self, prompt):
        path = self.config['generate_content_path'].format(model_name=self.model_id)
        gemini_url = f"{self.config['base_url']}{path}"

        gemini_data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.api_key
        }

        # Use the http_client which now has verify=False
        response = self.http_client.post(gemini_url, headers=headers, json=gemini_data)
        response.raise_for_status()
        response_data = response.json()

        return parse_gemini_response(response_data)