"""Azure OpenAI test with chat, embedding, and vision sub-tests."""

import os

from openai import AzureOpenAI

from .ai_provider_base import (
    CHAT_PROMPT,
    EMBEDDING_INPUT,
    VISION_PROMPT,
    BaseAIProviderTest,
    load_test_image_base64,
)


class AzureOpenAITest(BaseAIProviderTest):
    _supports_chat = True
    _supports_embedding = True
    _supports_vision = True

    def __init__(self):
        super().__init__()
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        self.chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "")
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "")
        self.vision_deployment = os.getenv("AZURE_OPENAI_VISION_DEPLOYMENT", "")

        # Vision is optional — only test if deployment is configured
        if not self.vision_deployment:
            self._supports_vision = False

    @property
    def test_name(self) -> str:
        return "Azure OpenAI"

    @property
    def test_description(self) -> str:
        return "Tests Azure OpenAI Service connectivity (chat, embeddings, vision)"

    @property
    def test_id(self) -> str:
        return "azure_openai"

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.api_key and self.chat_deployment)

    def get_configuration_help(self) -> str:
        return (
            "Configure Azure OpenAI with: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, "
            "AZURE_OPENAI_CHAT_DEPLOYMENT, AZURE_OPENAI_EMBEDDING_DEPLOYMENT (optional), "
            "AZURE_OPENAI_VISION_DEPLOYMENT (optional)"
        )

    def _get_client(self) -> AzureOpenAI:
        return AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )

    def _test_chat(self):
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.chat_deployment,
            messages=[{"role": "user", "content": CHAT_PROMPT}],
            max_tokens=10,
        )
        content = response.choices[0].message.content.strip()
        return {
            "message": f"Chat response: {content}",
            "model": self.chat_deployment,
            "response": content,
            "endpoint": self.endpoint,
        }

    def _test_embedding(self):
        client = self._get_client()
        response = client.embeddings.create(
            model=self.embedding_deployment,
            input=EMBEDDING_INPUT,
        )
        dims = len(response.data[0].embedding)
        return {
            "message": f"Embedding generated: {dims} dimensions",
            "model": self.embedding_deployment,
            "dimensions": dims,
        }

    def _test_vision(self):
        client = self._get_client()
        image_b64 = load_test_image_base64()
        response = client.chat.completions.create(
            model=self.vision_deployment,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                ],
            }],
            max_tokens=100,
        )
        description = response.choices[0].message.content.strip()
        return {
            "message": f"Vision response: {description}",
            "model": self.vision_deployment,
            "description": description,
        }
