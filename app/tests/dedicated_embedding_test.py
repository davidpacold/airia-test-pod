"""Dedicated embedding test — validates any OpenAI-compatible embedding endpoint.

Supports embedding models deployed as:
- Self-hosted models (LM Studio, vLLM, Ollama, TGI)
- OpenAI-compatible embedding APIs
- Any endpoint that accepts POST /v1/embeddings
"""

import os
import time

from openai import OpenAI

from .base_test import BaseTest, TestResult


class DedicatedEmbeddingTest(BaseTest):

    def __init__(self):
        super().__init__()
        self.base_url = os.getenv("DEDICATED_EMBEDDING_BASE_URL", "")
        self.api_key = os.getenv("DEDICATED_EMBEDDING_API_KEY", "")
        self.model = os.getenv("DEDICATED_EMBEDDING_MODEL", "")
        self.expected_dimensions = int(os.getenv("DEDICATED_EMBEDDING_DIMENSIONS", "0"))

    @property
    def test_name(self) -> str:
        return "Dedicated Embedding"

    @property
    def test_description(self) -> str:
        return "Tests OpenAI-compatible embedding endpoint"

    @property
    def test_id(self) -> str:
        return "dedicated_embedding"

    @property
    def is_optional(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 60

    def is_configured(self) -> bool:
        return bool(self.base_url and self.model)

    def get_configuration_help(self) -> str:
        return (
            "Configure with: DEDICATED_EMBEDDING_BASE_URL "
            "(e.g., http://host:1234/v1), DEDICATED_EMBEDDING_MODEL, "
            "DEDICATED_EMBEDDING_API_KEY (optional), "
            "DEDICATED_EMBEDDING_DIMENSIONS (optional, validates vector size)"
        )

    def _get_client(self) -> OpenAI:
        base_url = self.base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url += "/v1"
        return OpenAI(base_url=base_url, api_key=self.api_key or "not-required")

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        passed = 0
        failed = 0

        # Sub-test 1: connection
        client = self._get_client()
        try:
            start = time.time()
            response = client.embeddings.create(
                model=self.model,
                input="test",
            )
            latency = round(time.time() - start, 2)

            result.add_sub_test("connection", {
                "success": True,
                "message": f"Connected to endpoint ({latency}s)",
                "latency_seconds": latency,
            })
            passed += 1
        except Exception as e:
            result.add_sub_test("connection", {
                "success": False,
                "message": f"Connection failed: {e}",
                "remediation": (
                    "Check that baseUrl is correct and the embedding server is running. "
                    "Verify network connectivity from the pod to the endpoint."
                ),
            })
            failed += 1

        # Sub-test 2: embedding — validate response shape
        embedding_vector = None
        if passed > 0:
            try:
                start = time.time()
                response = client.embeddings.create(
                    model=self.model,
                    input="The quick brown fox jumps over the lazy dog.",
                )
                latency = round(time.time() - start, 2)

                embedding_vector = response.data[0].embedding
                if not embedding_vector or not isinstance(embedding_vector, list):
                    raise ValueError("data[0].embedding is empty or not an array")

                dims = len(embedding_vector)
                result.add_sub_test("embedding", {
                    "success": True,
                    "message": f"Embedding generated: {dims} dimensions ({latency}s)",
                    "dimensions": dims,
                    "latency_seconds": latency,
                    "model": response.model or self.model,
                })
                passed += 1
            except Exception as e:
                result.add_sub_test("embedding", {
                    "success": False,
                    "message": f"Embedding test failed: {e}",
                    "remediation": (
                        "Verify the model name is correct and the server supports "
                        "the /v1/embeddings endpoint with the expected response format"
                    ),
                })
                failed += 1

        # Sub-test 3: dimensions — only if expected_dimensions > 0
        if self.expected_dimensions > 0 and embedding_vector is not None:
            actual_dims = len(embedding_vector)
            if actual_dims == self.expected_dimensions:
                result.add_sub_test("dimensions", {
                    "success": True,
                    "message": f"Dimensions match: {actual_dims} (expected {self.expected_dimensions})",
                    "expected": self.expected_dimensions,
                    "actual": actual_dims,
                })
                passed += 1
            else:
                result.add_sub_test("dimensions", {
                    "success": False,
                    "message": (
                        f"Dimension mismatch: expected {self.expected_dimensions}, "
                        f"got {actual_dims}"
                    ),
                    "expected": self.expected_dimensions,
                    "actual": actual_dims,
                    "remediation": (
                        "The embedding model returned a different vector size than expected. "
                        "Check the model name and configuration, or update the expected "
                        "dimensions value to match."
                    ),
                })
                failed += 1
        elif self.expected_dimensions > 0 and embedding_vector is None:
            result.add_sub_test("dimensions", {
                "success": False,
                "message": "Cannot validate dimensions — embedding sub-test failed",
            })
            failed += 1

        total = passed + failed
        if failed == 0 and passed > 0:
            result.complete(True, f"All {passed}/{total} sub-tests passed")
        elif passed > 0:
            result.complete(False, f"{passed}/{total} sub-tests passed, {failed} failed")
        else:
            result.fail(f"All {total} sub-tests failed")

        return result
