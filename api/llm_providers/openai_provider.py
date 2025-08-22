# api/llm_providers/openai_provider.py
from openai import OpenAI
from .base import BaseLLMProvider
import json

class OpenAIProvider(BaseLLMProvider):
    def generate_analysis(self, prompt):
        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        # OpenAI's JSON mode returns a string that needs to be parsed
        return json.loads(response.choices[0].message.content)
    