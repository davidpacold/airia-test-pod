"""OpenAI API direct test — API key validation + chat."""

import os

from openai import OpenAI

from .ai_provider_base import CHAT_PROMPT, BaseAIProviderTest


class OpenAIDirectTest(BaseAIProviderTest):
    _supports_chat = True

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("OPENAI_DIRECT_API_KEY", "")
        self.model = os.getenv("OPENAI_DIRECT_MODEL", "gpt-4o-mini")

    @property
    def test_name(self) -> str:
        return "OpenAI"

    @property
    def test_description(self) -> str:
        return "Tests OpenAI API connectivity and key validation"

    @property
    def test_id(self) -> str:
        return "openai_direct"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_configuration_help(self) -> str:
        return "Configure with: OPENAI_DIRECT_API_KEY, OPENAI_DIRECT_MODEL (default: gpt-4o-mini)"

    def _test_chat(self):
        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
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
