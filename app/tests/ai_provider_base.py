"""Base class for AI provider tests with standardized test inputs."""

import base64
import logging
import os
import time
from abc import abstractmethod
from typing import Any, Dict, Optional

from .base_test import BaseTest, TestResult

logger = logging.getLogger(__name__)

# Standardized test inputs — every AI provider uses these exact strings
CHAT_PROMPT = "What is 2+2? Reply with just the number."
EMBEDDING_INPUT = "The quick brown fox jumps over the lazy dog."
VISION_PROMPT = "Describe what you see in this image in one sentence."

# Path to bundled test image
TEST_IMAGE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "static", "test-assets", "test-image.png"
)


def load_test_image_base64() -> Optional[str]:
    """Load the bundled test image as a base64 string.

    Returns None if the test image file does not exist.
    """
    if not os.path.isfile(TEST_IMAGE_PATH):
        logger.warning("Test image not found at %s", TEST_IMAGE_PATH)
        return None
    with open(TEST_IMAGE_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def load_test_image_bytes() -> Optional[bytes]:
    """Load the bundled test image as raw bytes.

    Returns None if the test image file does not exist.
    """
    if not os.path.isfile(TEST_IMAGE_PATH):
        logger.warning("Test image not found at %s", TEST_IMAGE_PATH)
        return None
    with open(TEST_IMAGE_PATH, "rb") as f:
        return f.read()


class BaseAIProviderTest(BaseTest):
    """Base class for AI provider tests.

    Subclasses set _supports_chat, _supports_embedding, _supports_vision flags
    and implement the corresponding _test_* methods.
    """

    _supports_chat: bool = False
    _supports_embedding: bool = False
    _supports_vision: bool = False

    @property
    def is_optional(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 60

    @abstractmethod
    def is_configured(self) -> bool:
        pass

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        passed = 0
        failed = 0
        total = 0

        if self._supports_chat:
            total += 1
            try:
                start = time.time()
                chat_result = self._test_chat()
                latency = round(time.time() - start, 2)
                chat_result["latency_seconds"] = latency
                chat_result["prompt"] = CHAT_PROMPT
                result.add_sub_test("chat", {
                    "success": True,
                    "message": chat_result.get("message", "Chat test passed"),
                    **chat_result,
                })
                passed += 1
            except Exception as e:
                result.add_sub_test("chat", {
                    "success": False,
                    "message": f"Chat test failed: {e}",
                })
                failed += 1

        if self._supports_embedding:
            total += 1
            try:
                start = time.time()
                emb_result = self._test_embedding()
                latency = round(time.time() - start, 2)
                emb_result["latency_seconds"] = latency
                emb_result["input"] = EMBEDDING_INPUT
                result.add_sub_test("embedding", {
                    "success": True,
                    "message": emb_result.get("message", "Embedding test passed"),
                    **emb_result,
                })
                passed += 1
            except Exception as e:
                result.add_sub_test("embedding", {
                    "success": False,
                    "message": f"Embedding test failed: {e}",
                })
                failed += 1

        if self._supports_vision:
            total += 1
            try:
                start = time.time()
                vis_result = self._test_vision()
                latency = round(time.time() - start, 2)
                vis_result["latency_seconds"] = latency
                vis_result["prompt"] = VISION_PROMPT
                result.add_sub_test("vision", {
                    "success": True,
                    "message": vis_result.get("message", "Vision test passed"),
                    **vis_result,
                })
                passed += 1
            except Exception as e:
                result.add_sub_test("vision", {
                    "success": False,
                    "message": f"Vision test failed: {e}",
                })
                failed += 1

        if failed == 0 and passed > 0:
            result.complete(True, f"All {passed}/{total} sub-tests passed")
        elif passed > 0:
            result.complete(False, f"{passed}/{total} sub-tests passed, {failed} failed")
        else:
            result.fail(f"All {total} sub-tests failed")

        return result

    def _test_chat(self) -> Dict[str, Any]:
        """Override to implement chat test. Return dict with 'message' and any details."""
        raise NotImplementedError

    def _test_embedding(self) -> Dict[str, Any]:
        """Override to implement embedding test. Return dict with 'message', 'dimensions'."""
        raise NotImplementedError

    def _test_vision(self) -> Dict[str, Any]:
        """Override to implement vision test. Return dict with 'message', 'description'."""
        raise NotImplementedError
