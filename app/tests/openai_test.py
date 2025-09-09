import json
import os
import time
from typing import Any, Dict, List, Optional

from openai import AzureOpenAI, OpenAI

from ..models import TestStatus
from .base_test import BaseTest, TestResult


class OpenAITest(BaseTest):
    """Test Azure OpenAI and OpenAI-compatible API connectivity"""

    def __init__(self):
        super().__init__()
        # Azure OpenAI configuration
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        self.azure_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.azure_embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

        # Generic OpenAI-compatible configuration (for self-hosted models)
        self.openai_base_url = os.getenv("OPENAI_BASE_URL")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
        self.openai_embedding_model = os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"
        )

        # Test configuration
        self.test_completion = os.getenv("TEST_COMPLETION", "true").lower() == "true"
        self.test_embedding = os.getenv("TEST_EMBEDDING", "true").lower() == "true"
        self.request_timeout = int(os.getenv("OPENAI_TIMEOUT", "30"))

        # Custom test configuration
        self.custom_test_prompt = os.getenv("OPENAI_CUSTOM_PROMPT", "")
        self.custom_system_message = os.getenv(
            "OPENAI_CUSTOM_SYSTEM_MESSAGE", "You are a helpful assistant."
        )

    @property
    def test_name(self) -> str:
        return "AI Models (OpenAI/Llama)"

    @property
    def test_description(self) -> str:
        return "Tests AI model APIs: Azure OpenAI, OpenAI, Llama, and compatible APIs"

    @property
    def test_id(self) -> str:
        return "openai"

    @property
    def is_optional(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 90  # AI requests can take longer

    def is_configured(self) -> bool:
        """Check if Azure OpenAI or OpenAI-compatible API is configured"""
        # Azure OpenAI configuration
        azure_configured = (
            self.azure_endpoint and self.azure_api_key and self.azure_deployment_name
        )

        # Generic OpenAI configuration
        openai_configured = self.openai_base_url and self.openai_api_key

        return azure_configured or openai_configured

    def get_configuration_help(self) -> str:
        return (
            "AI model API configuration required. Supports Azure OpenAI, OpenAI, Llama, and compatible APIs. "
            "For Azure OpenAI: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME, "
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT (optional), AZURE_OPENAI_API_VERSION (default: 2024-02-01). "
            "For self-hosted: OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL_NAME (default: gpt-3.5-turbo), "
            "OPENAI_EMBEDDING_MODEL (default: text-embedding-ada-002). "
            "Optional: TEST_COMPLETION (default: true), TEST_EMBEDDING (default: true), OPENAI_TIMEOUT (default: 30)"
        )

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        try:
            # Determine which configuration to use
            use_azure = (
                self.azure_endpoint
                and self.azure_api_key
                and self.azure_deployment_name
            )

            if use_azure:
                result.add_log(
                    "INFO", f"Using Azure OpenAI configuration: {self.azure_endpoint}"
                )
                result.add_log(
                    "INFO", f"Model deployment: {self.azure_deployment_name}"
                )
                client = AzureOpenAI(
                    api_key=self.azure_api_key,
                    api_version=self.azure_api_version,
                    azure_endpoint=self.azure_endpoint,
                    timeout=self.request_timeout,
                )
                completion_model = self.azure_deployment_name
                embedding_model = self.azure_embedding_deployment
            else:
                result.add_log(
                    "INFO", f"Using OpenAI-compatible API: {self.openai_base_url}"
                )
                result.add_log("INFO", f"Model: {self.openai_model_name}")
                # Detect common Llama model patterns
                if "llama" in self.openai_model_name.lower():
                    result.add_log(
                        "INFO", "Detected Llama model - testing compatibility"
                    )
                client = OpenAI(
                    api_key=self.openai_api_key,
                    base_url=self.openai_base_url,
                    timeout=self.request_timeout,
                )
                completion_model = self.openai_model_name
                embedding_model = self.openai_embedding_model

            all_passed = True

            # Test 1: Basic connection and model listing (if available)
            connection_result = self._test_connection(client, use_azure)
            result.add_sub_test("API Connection", connection_result)
            if not connection_result["success"]:
                all_passed = False

            # Test 2: Completion API
            if self.test_completion and completion_model:
                completion_result = self._test_completion(
                    client, completion_model, use_azure
                )
                result.add_sub_test("Text Completion", completion_result)
                if not completion_result["success"]:
                    all_passed = False
            else:
                result.add_log(
                    "INFO", "Skipping completion test - not configured or disabled"
                )

            # Test 3: Embedding API
            if self.test_embedding and embedding_model:
                embedding_result = self._test_embedding(
                    client, embedding_model, use_azure
                )
                result.add_sub_test("Text Embedding", embedding_result)
                if not embedding_result["success"]:
                    all_passed = False
            else:
                result.add_log(
                    "INFO", "Skipping embedding test - not configured or disabled"
                )

            # Test 4: Custom prompt test (if configured)
            if self.custom_test_prompt and completion_model:
                custom_result = self._test_custom_prompt(
                    client, completion_model, use_azure
                )
                result.add_sub_test("Custom Prompt", custom_result)
                if not custom_result["success"]:
                    all_passed = False
            else:
                result.add_log(
                    "INFO", "Skipping custom prompt test - no custom prompt configured"
                )

            if all_passed:
                result.complete(True, "All OpenAI API tests passed successfully")
            else:
                failed_tests = [
                    name
                    for name, test_result in result.sub_tests.items()
                    if not test_result.get("success", False)
                ]
                result.fail(
                    f"OpenAI API tests failed: {', '.join(failed_tests)}",
                    remediation="Check API credentials, model deployments, and network connectivity",
                )

        except Exception as e:
            result.fail(
                f"OpenAI test failed: {str(e)}",
                error=e,
                remediation="Check API configuration, credentials, and network connectivity",
            )

        return result

    def _test_connection(self, client, use_azure: bool) -> Dict[str, Any]:
        """Test basic API connection"""
        try:
            start_time = time.time()

            # For Azure OpenAI, we can't easily list models, so we'll do a minimal completion test
            # For other OpenAI APIs, try to list models first
            if not use_azure:
                try:
                    models = client.models.list()
                    model_list = [model.id for model in models.data]
                    duration = time.time() - start_time

                    return {
                        "success": True,
                        "message": f"Successfully connected and retrieved {len(model_list)} models",
                        "models": model_list[
                            :10
                        ],  # Limit to first 10 models for display
                        "response_time_ms": round(duration * 1000, 2),
                    }
                except Exception as model_error:
                    # If model listing fails, fall back to basic connection test
                    result = self._basic_connection_test(client, use_azure)
                    result["model_list_error"] = str(model_error)
                    return result
            else:
                # For Azure OpenAI, do a basic connection test
                return self._basic_connection_test(client, use_azure)

        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "error": str(e),
                "remediation": "Verify API endpoint, credentials, and network connectivity",
            }

    def _basic_connection_test(self, client, use_azure: bool) -> Dict[str, Any]:
        """Perform a basic connection test with minimal API call"""
        try:
            start_time = time.time()

            # Make a very simple completion request to test connection
            test_model = (
                self.azure_deployment_name if use_azure else self.openai_model_name
            )

            response = client.chat.completions.create(
                model=test_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=1,
                temperature=0,
            )

            duration = time.time() - start_time

            return {
                "success": True,
                "message": "API connection successful",
                "response_time_ms": round(duration * 1000, 2),
                "model_used": test_model,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Basic connection test failed: {str(e)}",
                "error": str(e),
            }

    def _test_completion(self, client, model: str, use_azure: bool) -> Dict[str, Any]:
        """Test text completion functionality"""
        try:
            start_time = time.time()

            # Test prompt
            test_messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Respond briefly.",
                },
                {
                    "role": "user",
                    "content": "What is 2+2? Answer with just the number.",
                },
            ]

            response = client.chat.completions.create(
                model=model, messages=test_messages, max_tokens=10, temperature=0
            )

            duration = time.time() - start_time

            # Extract response details
            choice = response.choices[0]
            response_text = choice.message.content.strip()

            # Simple validation - check if response contains "4"
            contains_expected = "4" in response_text

            return {
                "success": True,
                "message": f"Completion successful: '{response_text}'",
                "model": model,
                "response_text": response_text,
                "response_time_ms": round(duration * 1000, 2),
                "tokens_used": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "validation_passed": contains_expected,
                "finish_reason": choice.finish_reason,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Completion test failed: {str(e)}",
                "error": str(e),
                "remediation": "Check model deployment name and API permissions",
            }

    def _test_embedding(self, client, model: str, use_azure: bool) -> Dict[str, Any]:
        """Test text embedding functionality"""
        try:
            start_time = time.time()

            # Test text for embedding
            test_text = "This is a test sentence for embedding."

            response = client.embeddings.create(model=model, input=test_text)

            duration = time.time() - start_time

            # Extract embedding details
            embedding_data = response.data[0]
            embedding_vector = embedding_data.embedding

            # Basic validation - check embedding dimensions and values
            embedding_length = len(embedding_vector)
            has_values = any(
                abs(val) > 0.001 for val in embedding_vector[:10]
            )  # Check first 10 values

            return {
                "success": True,
                "message": f"Embedding successful - {embedding_length} dimensions",
                "model": model,
                "input_text": test_text,
                "embedding_dimensions": embedding_length,
                "response_time_ms": round(duration * 1000, 2),
                "tokens_used": response.usage.total_tokens,
                "has_meaningful_values": has_values,
                "sample_values": embedding_vector[:5],  # First 5 values for inspection
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Embedding test failed: {str(e)}",
                "error": str(e),
                "remediation": "Check embedding model deployment name and API permissions",
            }

    def _test_custom_prompt(
        self, client, model: str, use_azure: bool
    ) -> Dict[str, Any]:
        """Test custom prompt functionality"""
        try:
            start_time = time.time()

            # Use custom prompt
            test_messages = [
                {"role": "system", "content": self.custom_system_message},
                {"role": "user", "content": self.custom_test_prompt},
            ]

            response = client.chat.completions.create(
                model=model,
                messages=test_messages,
                max_tokens=150,  # Allow more tokens for custom responses
                temperature=0.7,  # Allow some creativity
            )

            duration = time.time() - start_time

            # Extract response details
            choice = response.choices[0]
            response_text = choice.message.content.strip()

            return {
                "success": True,
                "message": f"Custom prompt test successful",
                "model": model,
                "prompt": self.custom_test_prompt,
                "system_message": self.custom_system_message,
                "response_text": response_text,
                "response_time_ms": round(duration * 1000, 2),
                "tokens_used": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "finish_reason": choice.finish_reason,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Custom prompt test failed: {str(e)}",
                "error": str(e),
                "remediation": "Check custom prompt format and model permissions",
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
            use_azure = (
                self.azure_endpoint
                and self.azure_api_key
                and self.azure_deployment_name
            )

            if use_azure:
                client = AzureOpenAI(
                    api_key=self.azure_api_key,
                    api_version=self.azure_api_version,
                    azure_endpoint=self.azure_endpoint,
                    timeout=self.request_timeout,
                )
                completion_model = self.azure_deployment_name
            else:
                client = OpenAI(
                    api_key=self.openai_api_key,
                    base_url=self.openai_base_url,
                    timeout=self.request_timeout,
                )
                completion_model = self.openai_model_name

            start_time = time.time()

            # Prepare messages
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})

            # If file content is provided, include it in the prompt based on file type
            user_content = custom_prompt
            if custom_file_content:
                if file_type == "pdf":
                    user_content = f"Here is a PDF document to analyze:\n\n{custom_file_content}\n\nUser request: {custom_prompt}"
                elif file_type in ["jpg", "jpeg", "png"]:
                    # For image files, we'll need vision model support
                    # For now, treat as base64 data with description
                    user_content = f"Here is an image file (base64 encoded) to analyze. The image is a {file_type.upper()} file.\n\nUser request: {custom_prompt}\n\nNote: This model may not support image analysis. Consider using GPT-4V or similar vision model."
                else:
                    # Text files
                    user_content = f"Here is some file content to analyze:\n\n{custom_file_content}\n\nUser request: {custom_prompt}"

            messages.append({"role": "user", "content": user_content})

            response = client.chat.completions.create(
                model=completion_model,
                messages=messages,
                max_tokens=500,  # Allow more tokens for custom responses
                temperature=0.7,
            )

            duration = time.time() - start_time

            # Extract response details
            choice = response.choices[0]
            response_text = choice.message.content.strip()

            return {
                "success": True,
                "message": "Custom input test successful",
                "model": completion_model,
                "prompt": custom_prompt,
                "file_provided": bool(custom_file_content),
                "file_type": file_type or "none",
                "system_message": system_message or "None",
                "response_text": response_text,
                "response_time_ms": round(duration * 1000, 2),
                "tokens_used": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                "finish_reason": choice.finish_reason,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Custom input test failed: {str(e)}",
                "error": str(e),
                "remediation": "Check API configuration and input format",
            }
