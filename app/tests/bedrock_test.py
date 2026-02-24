"""AWS Bedrock test with chat, embedding, and vision sub-tests."""

import json
import os

import boto3

from .ai_provider_base import (
    CHAT_PROMPT,
    EMBEDDING_INPUT,
    VISION_PROMPT,
    BaseAIProviderTest,
    load_test_image_bytes,
)


class BedrockTest(BaseAIProviderTest):
    _supports_chat = True
    _supports_embedding = True
    _supports_vision = True

    def __init__(self):
        super().__init__()
        self.region = os.getenv("BEDROCK_REGION", "us-east-1")
        self.access_key = os.getenv("BEDROCK_ACCESS_KEY_ID", "")
        self.secret_key = os.getenv("BEDROCK_SECRET_ACCESS_KEY", "")
        self.chat_model = os.getenv("BEDROCK_CHAT_MODEL_ID", "")
        self.embedding_model = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "")
        self.vision_model = os.getenv("BEDROCK_VISION_MODEL_ID", "")

        if not self.embedding_model:
            self._supports_embedding = False
        if not self.vision_model:
            self._supports_vision = False

    @property
    def test_name(self) -> str:
        return "AWS Bedrock"

    @property
    def test_description(self) -> str:
        return "Tests AWS Bedrock connectivity (chat, embeddings, vision)"

    @property
    def test_id(self) -> str:
        return "bedrock"

    def is_configured(self) -> bool:
        return bool(self.access_key and self.secret_key and self.chat_model)

    def get_configuration_help(self) -> str:
        return (
            "Configure AWS Bedrock with: BEDROCK_REGION, BEDROCK_ACCESS_KEY_ID, "
            "BEDROCK_SECRET_ACCESS_KEY, BEDROCK_CHAT_MODEL_ID, "
            "BEDROCK_EMBEDDING_MODEL_ID (optional), BEDROCK_VISION_MODEL_ID (optional)"
        )

    def _get_client(self):
        return boto3.client(
            "bedrock-runtime",
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    def _test_chat(self):
        client = self._get_client()
        response = client.converse(
            modelId=self.chat_model,
            messages=[{
                "role": "user",
                "content": [{"text": CHAT_PROMPT}],
            }],
            inferenceConfig={"maxTokens": 10},
        )
        content = response["output"]["message"]["content"][0]["text"].strip()
        return {
            "message": f"Chat response: {content}",
            "model": self.chat_model,
            "response": content,
            "region": self.region,
        }

    def _test_embedding(self):
        client = self._get_client()
        body = json.dumps({"inputText": EMBEDDING_INPUT})
        response = client.invoke_model(
            modelId=self.embedding_model,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        # Support multiple provider response formats:
        # - Titan: {"embedding": [...]}
        # - Cohere: {"embeddings": [[...]]}
        embedding = result.get("embedding") or []
        if not embedding and "embeddings" in result:
            embeddings = result["embeddings"]
            embedding = embeddings[0] if embeddings else []
        dims = len(embedding)
        return {
            "message": f"Embedding generated: {dims} dimensions",
            "model": self.embedding_model,
            "dimensions": dims,
        }

    def _test_vision(self):
        client = self._get_client()
        image_bytes = load_test_image_bytes()
        response = client.converse(
            modelId=self.vision_model,
            messages=[{
                "role": "user",
                "content": [
                    {"text": VISION_PROMPT},
                    {"image": {"format": "png", "source": {"bytes": image_bytes}}},
                ],
            }],
            inferenceConfig={"maxTokens": 100},
        )
        description = response["output"]["message"]["content"][0]["text"].strip()
        return {
            "message": f"Vision response: {description}",
            "model": self.vision_model,
            "description": description,
        }
