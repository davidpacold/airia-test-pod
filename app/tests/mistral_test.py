"""Mistral AI API test — API key validation + chat."""

import os

from mistralai import Mistral

from .ai_provider_base import CHAT_PROMPT, BaseAIProviderTest


class MistralTest(BaseAIProviderTest):
    _supports_chat = True

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("MISTRAL_API_KEY", "")
        self.model = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

    @property
    def test_name(self) -> str:
        return "Mistral"

    @property
    def test_description(self) -> str:
        return "Tests Mistral AI API connectivity and key validation"

    @property
    def test_id(self) -> str:
        return "mistral"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_configuration_help(self) -> str:
        return "Configure with: MISTRAL_API_KEY, MISTRAL_MODEL (default: mistral-small-latest)"

    def _test_chat(self):
        client = Mistral(api_key=self.api_key)
        response = client.chat.complete(
            model=self.model,
            messages=[{"role": "user", "content": CHAT_PROMPT}],
            max_tokens=10,
        )
        content = response.choices[0].message.content.strip()
        return {
            "message": f"Chat response: {content}",
            "model": self.model,
            "response": content,
        }
