"""Anthropic API test — API key validation + chat."""

import os

import anthropic

from .ai_provider_base import CHAT_PROMPT, BaseAIProviderTest


class AnthropicTest(BaseAIProviderTest):
    _supports_chat = True

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    @property
    def test_name(self) -> str:
        return "Anthropic"

    @property
    def test_description(self) -> str:
        return "Tests Anthropic API connectivity and key validation"

    @property
    def test_id(self) -> str:
        return "anthropic"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_configuration_help(self) -> str:
        return "Configure with: ANTHROPIC_API_KEY, ANTHROPIC_MODEL (default: claude-sonnet-4-20250514)"

    def _test_chat(self):
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=10,
            messages=[{"role": "user", "content": CHAT_PROMPT}],
        )
        content = response.content[0].text.strip()
        return {
            "message": f"Chat response: {content}",
            "model": self.model,
            "response": content,
        }
