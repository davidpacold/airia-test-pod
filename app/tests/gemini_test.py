"""Google Gemini API test — API key validation + chat."""

import os

import google.generativeai as genai

from .ai_provider_base import CHAT_PROMPT, BaseAIProviderTest


class GeminiTest(BaseAIProviderTest):
    _supports_chat = True

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    @property
    def test_name(self) -> str:
        return "Google Gemini"

    @property
    def test_description(self) -> str:
        return "Tests Google Gemini API connectivity and key validation"

    @property
    def test_id(self) -> str:
        return "gemini"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_configuration_help(self) -> str:
        return "Configure with: GEMINI_API_KEY, GEMINI_MODEL (default: gemini-2.0-flash)"

    def _test_chat(self):
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(CHAT_PROMPT)
        content = response.text.strip()
        return {
            "message": f"Chat response: {content}",
            "model": self.model,
            "response": content,
        }
