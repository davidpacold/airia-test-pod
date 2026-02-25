"""Vision model test — validates any OpenAI-compatible vision endpoint.

Supports vision-capable models deployed as:
- Azure ML Studio serverless endpoints (e.g., LLaMA 3.2 Vision)
- Self-hosted models with OpenAI-compatible APIs (e.g., vLLM, Ollama)
- Any endpoint that accepts /v1/chat/completions with image_url content
"""

import os

from openai import OpenAI

from .ai_provider_base import (
    VISION_PROMPT,
    BaseAIProviderTest,
    load_test_image_base64,
)


class VisionModelTest(BaseAIProviderTest):
    _supports_chat = True
    _supports_vision = True

    def __init__(self):
        super().__init__()
        self.endpoint = os.getenv("VISION_MODEL_ENDPOINT", "")
        self.api_key = os.getenv("VISION_MODEL_API_KEY", "")
        self.model = os.getenv("VISION_MODEL_NAME", "")

        # If no vision image available, skip vision sub-test
        if not load_test_image_base64():
            self._supports_vision = False

    @property
    def test_name(self) -> str:
        return "Vision Model"

    @property
    def test_description(self) -> str:
        return "Tests vision-capable model endpoint (OpenAI-compatible)"

    @property
    def test_id(self) -> str:
        return "vision_model"

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def get_configuration_help(self) -> str:
        return (
            "Configure Vision Model with: VISION_MODEL_ENDPOINT "
            "(OpenAI-compatible endpoint URL), VISION_MODEL_API_KEY, "
            "VISION_MODEL_NAME (optional, defaults to endpoint's model)"
        )

    def _get_client(self) -> OpenAI:
        base_url = self.endpoint.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url += "/v1"
        return OpenAI(base_url=base_url, api_key=self.api_key)

    def _test_chat(self):
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model or "default",
            messages=[{"role": "user", "content": "What is 2+2? Reply with just the number."}],
            max_tokens=10,
        )
        content = response.choices[0].message.content.strip()
        return {
            "message": f"Chat response: {content}",
            "model": self.model or response.model or "default",
            "response": content,
            "endpoint": self.endpoint,
        }

    def _test_vision(self):
        client = self._get_client()
        image_b64 = load_test_image_base64()
        if not image_b64:
            raise RuntimeError("Test image not found")

        response = client.chat.completions.create(
            model=self.model or "default",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                ],
            }],
            max_tokens=150,
        )
        description = response.choices[0].message.content.strip()
        return {
            "message": f"Vision response: {description}",
            "model": self.model or response.model or "default",
            "description": description,
            "endpoint": self.endpoint,
        }
