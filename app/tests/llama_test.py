import json
import os
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from ..models import TestStatus
from .base_test import BaseTest, TestResult


class LlamaTest(BaseTest):
    """Test Llama model connectivity and capabilities"""

    def __init__(self):
        super().__init__()
        # Llama-specific configuration
        self.llama_base_url = os.getenv("LLAMA_BASE_URL")
        self.llama_api_key = os.getenv(
            "LLAMA_API_KEY", "not-required"
        )  # Many self-hosted don't need keys
        self.llama_model_name = os.getenv("LLAMA_MODEL_NAME", "llama2")
        self.llama_max_tokens = int(os.getenv("LLAMA_MAX_TOKENS", "100"))
        self.llama_temperature = float(os.getenv("LLAMA_TEMPERATURE", "0.1"))

        # Alternative generic OpenAI-compatible config
        self.openai_base_url = os.getenv("OPENAI_BASE_URL")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "not-required")
        self.openai_model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")

        # Test configuration
        self.request_timeout = int(os.getenv("LLAMA_TIMEOUT", "60"))

    @property
    def test_name(self) -> str:
        return "Llama Model"

    @property
    def test_description(self) -> str:
        return "Tests Llama model API connectivity and text generation"

    @property
    def test_id(self) -> str:
        return "llama"

    @property
    def is_optional(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 120  # Llama models can be slower

    def is_configured(self) -> bool:
        """Check if Llama or compatible API is configured"""
        # Specific Llama configuration
        llama_configured = bool(self.llama_base_url)

        # Generic OpenAI-compatible configuration with Llama model name
        openai_llama_configured = (
            self.openai_base_url and "llama" in self.openai_model_name.lower()
        )

        return llama_configured or openai_llama_configured

    def get_configuration_help(self) -> str:
        return (
            "Llama model API configuration required. "
            "For dedicated Llama API: LLAMA_BASE_URL, LLAMA_MODEL_NAME (default: llama2), "
            "LLAMA_API_KEY (optional), LLAMA_MAX_TOKENS (default: 100), LLAMA_TEMPERATURE (default: 0.1). "
            "For OpenAI-compatible: OPENAI_BASE_URL, OPENAI_MODEL_NAME (with 'llama' in name), "
            "OPENAI_API_KEY (optional). "
            "Optional: LLAMA_TIMEOUT (default: 60)"
        )

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        try:
            # Determine which configuration to use
            use_llama_config = bool(self.llama_base_url)

            if use_llama_config:
                result.add_log(
                    "INFO", f"Using Llama API configuration: {self.llama_base_url}"
                )
                result.add_log("INFO", f"Model: {self.llama_model_name}")
                client = OpenAI(
                    api_key=self.llama_api_key,
                    base_url=self.llama_base_url,
                    timeout=self.request_timeout,
                )
                model_name = self.llama_model_name
                max_tokens = self.llama_max_tokens
                temperature = self.llama_temperature
            else:
                result.add_log(
                    "INFO", f"Using OpenAI-compatible API: {self.openai_base_url}"
                )
                result.add_log("INFO", f"Model: {self.openai_model_name}")
                result.add_log(
                    "INFO", "Detected Llama model via OpenAI-compatible interface"
                )
                client = OpenAI(
                    api_key=self.openai_api_key,
                    base_url=self.openai_base_url,
                    timeout=self.request_timeout,
                )
                model_name = self.openai_model_name
                max_tokens = 100
                temperature = 0.1

            all_passed = True

            # Test 1: Basic connection test
            connection_result = self._test_connection(client)
            result.add_sub_test("API Connection", connection_result)
            if not connection_result["success"]:
                all_passed = False

            # Test 2: Simple text completion
            completion_result = self._test_completion(
                client, model_name, max_tokens, temperature
            )
            result.add_sub_test("Text Generation", completion_result)
            if not completion_result["success"]:
                all_passed = False

            # Test 3: Llama-specific prompt test
            llama_prompt_result = self._test_llama_prompt(
                client, model_name, max_tokens, temperature
            )
            result.add_sub_test("Llama-style Prompt", llama_prompt_result)
            if not llama_prompt_result["success"]:
                all_passed = False

            if all_passed:
                result.complete(True, "All Llama model tests passed successfully")
            else:
                result.complete(False, "One or more Llama model tests failed")

        except Exception as e:
            result.fail(f"Llama model test failed: {str(e)}")
            result.add_log("ERROR", f"Exception: {str(e)}")

        result.end()
        return result

    def _test_connection(self, client: OpenAI) -> Dict[str, Any]:
        """Test basic API connection"""
        try:
            # Try to list models if endpoint supports it
            try:
                models = client.models.list()
                model_names = (
                    [model.id for model in models.data]
                    if hasattr(models, "data")
                    else []
                )
                return {
                    "success": True,
                    "message": f"Connected successfully. Found {len(model_names)} models",
                    "models": model_names[:5],  # Show first 5 models
                }
            except Exception:
                # Model listing not supported, that's OK
                return {
                    "success": True,
                    "message": "Connected successfully (model listing not supported)",
                    "models": [],
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "remediation": "Check that the Llama API endpoint is correct and accessible",
            }

    def _test_completion(
        self, client: OpenAI, model_name: str, max_tokens: int, temperature: float
    ) -> Dict[str, Any]:
        """Test basic text completion"""
        try:
            start_time = time.time()

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": "Hello! Can you introduce yourself briefly?",
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            duration = time.time() - start_time

            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content.strip()
                return {
                    "success": True,
                    "message": f"Text generation successful (took {duration:.2f}s)",
                    "response_preview": (
                        content[:100] + "..." if len(content) > 100 else content
                    ),
                    "response_length": len(content),
                    "duration_seconds": duration,
                }
            else:
                return {
                    "success": False,
                    "message": "No response content generated",
                    "remediation": "Check model configuration and prompt format",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Text generation failed: {str(e)}",
                "remediation": "Verify model name and API compatibility",
            }

    def _test_llama_prompt(
        self, client: OpenAI, model_name: str, max_tokens: int, temperature: float
    ) -> Dict[str, Any]:
        """Test Llama-specific prompt format"""
        try:
            start_time = time.time()

            # Use a prompt format that works well with Llama models
            llama_prompt = """<s>[INST] You are a helpful AI assistant. Please answer this question concisely:
What are the key capabilities of Llama models? [/INST]"""

            # For chat completions, we'll use the system/user format
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {
                        "role": "user",
                        "content": "What are the key capabilities of Llama models? Please answer concisely.",
                    },
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            duration = time.time() - start_time

            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content.strip()

                # Check if response mentions Llama (indicates model awareness)
                mentions_llama = "llama" in content.lower()

                return {
                    "success": True,
                    "message": f"Llama prompt test successful (took {duration:.2f}s)",
                    "response_preview": (
                        content[:150] + "..." if len(content) > 150 else content
                    ),
                    "mentions_llama": mentions_llama,
                    "response_length": len(content),
                    "duration_seconds": duration,
                }
            else:
                return {
                    "success": False,
                    "message": "No response to Llama-specific prompt",
                    "remediation": "Check if the model supports the prompt format",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Llama prompt test failed: {str(e)}",
                "remediation": "Verify Llama model compatibility and prompt format",
            }

    def test_with_custom_input(
        self,
        custom_prompt: str,
        custom_file_content: str = None,
        file_type: str = None,
        system_message: str = None,
    ) -> Dict[str, Any]:
        """Test with custom user input - can be called directly from API"""
        try:
            # Determine which configuration to use
            use_llama_config = bool(self.llama_base_url)

            if use_llama_config:
                client = OpenAI(
                    api_key=self.llama_api_key,
                    base_url=self.llama_base_url,
                    timeout=self.request_timeout,
                )
                model_name = self.llama_model_name
                max_tokens = self.llama_max_tokens
                temperature = self.llama_temperature
            else:
                client = OpenAI(
                    api_key=self.openai_api_key,
                    base_url=self.openai_base_url,
                    timeout=self.request_timeout,
                )
                model_name = self.openai_model_name
                max_tokens = 150
                temperature = 0.7

            start_time = time.time()

            # Prepare messages
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            else:
                messages.append(
                    {"role": "system", "content": "You are a helpful AI assistant."}
                )

            # If file content is provided, include it in the prompt based on file type
            user_content = custom_prompt
            if custom_file_content:
                if file_type == "pdf":
                    user_content = f"Here is a PDF document to analyze:\n\n{custom_file_content}\n\nUser request: {custom_prompt}"
                elif file_type in ["jpg", "jpeg", "png"]:
                    # For image files, most Llama models don't support vision
                    user_content = f"Here is an image file (base64 encoded) to analyze. The image is a {file_type.upper()} file.\n\nUser request: {custom_prompt}\n\nNote: This Llama model may not support image analysis. Consider using a multimodal Llama variant."
                else:
                    # Text files
                    user_content = f"Here is some file content to analyze:\n\n{custom_file_content}\n\nUser request: {custom_prompt}"

            messages.append({"role": "user", "content": user_content})

            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            duration = time.time() - start_time

            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content.strip()

                return {
                    "success": True,
                    "message": "Custom input test successful",
                    "model": model_name,
                    "prompt": custom_prompt,
                    "file_provided": bool(custom_file_content),
                    "file_type": file_type or "none",
                    "system_message": system_message
                    or "You are a helpful AI assistant.",
                    "response_text": content,
                    "response_time_ms": round(duration * 1000, 2),
                    "response_length": len(content),
                    "tokens_used": (
                        getattr(response.usage, "total_tokens", None)
                        if hasattr(response, "usage")
                        else None
                    ),
                }
            else:
                return {
                    "success": False,
                    "message": "No response content generated",
                    "remediation": "Check model configuration and prompt format",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Custom input test failed: {str(e)}",
                "error": str(e),
                "remediation": "Check API configuration and input format",
            }
