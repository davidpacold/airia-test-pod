import json
import os
import time
from typing import Any, Dict, Optional

import requests

from ..models import TestStatus
from .base_test import BaseTest, TestResult


class LlamaTest(BaseTest):
    """Test Ollama native API connectivity and capabilities"""

    def __init__(self):
        super().__init__()
        # Ollama-specific configuration (native API)
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model_name = os.getenv("OLLAMA_MODEL_NAME", "llama2")
        self.ollama_max_tokens = int(os.getenv("OLLAMA_MAX_TOKENS", "100"))
        self.ollama_temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))

        # Test configuration
        self.request_timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))

    @property
    def test_name(self) -> str:
        return "Ollama API (Native)"

    @property
    def test_description(self) -> str:
        return "Tests Ollama native API connectivity and model generation"

    @property
    def test_id(self) -> str:
        return "llama"

    @property
    def is_optional(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 120  # Ollama models can be slower

    def is_configured(self) -> bool:
        """Check if Ollama API is configured"""
        return bool(self.ollama_base_url and self.ollama_model_name)

    def get_configuration_help(self) -> str:
        return (
            "Ollama native API configuration required. "
            "OLLAMA_BASE_URL (default: http://localhost:11434), "
            "OLLAMA_MODEL_NAME (default: llama2), "
            "OLLAMA_MAX_TOKENS (default: 100), "
            "OLLAMA_TEMPERATURE (default: 0.7), "
            "OLLAMA_TIMEOUT (default: 60)"
        )

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        self.logger.info("Starting Ollama native API test...")
        print("🦙 Starting Ollama native API test...")
        print(f"🔧 Ollama endpoint: {self.ollama_base_url}")
        print(f"🤖 Model: {self.ollama_model_name}")

        result.add_log("INFO", f"Ollama endpoint: {self.ollama_base_url}")
        result.add_log("INFO", f"Model: {self.ollama_model_name}")

        try:
            all_passed = True

            # Test 1: Check Ollama version and connectivity
            print("\n🔗 Testing Ollama API connectivity...")
            version_result = self._test_version()
            result.add_sub_test("API Connection", version_result)
            if version_result["success"]:
                print(f"✅ Connected to Ollama {version_result.get('version', 'unknown')}")
            else:
                print(f"❌ Connection failed: {version_result.get('message', 'Unknown error')}")
                all_passed = False

            # Test 2: List available models
            print("\n📋 Listing available models...")
            tags_result = self._test_list_models()
            result.add_sub_test("List Models", tags_result)
            if tags_result["success"]:
                model_count = len(tags_result.get('models', []))
                print(f"✅ Found {model_count} model(s)")
                if tags_result.get('model_found'):
                    print(f"   ✓ Target model '{self.ollama_model_name}' is available")
                else:
                    print(f"   ⚠️ Target model '{self.ollama_model_name}' not found")
            else:
                print(f"❌ Failed to list models: {tags_result.get('message', 'Unknown error')}")
                all_passed = False

            # Test 3: Generate text using native /api/generate endpoint
            print("\n💬 Testing text generation (native API)...")
            generate_result = self._test_generate()
            result.add_sub_test("Text Generation", generate_result)
            if generate_result["success"]:
                print("✅ Text generation successful")
                print(f"   📝 Prompt: {generate_result.get('prompt', 'N/A')[:50]}...")
                response_text = generate_result.get('response', 'N/A')
                print(f"   💬 Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
                print(f"   ⏱️  Duration: {generate_result.get('duration_seconds', 0):.2f}s")
                print(f"   🎯 Tokens: {generate_result.get('eval_count', 'N/A')}")
            else:
                print(f"❌ Text generation failed: {generate_result.get('message', 'Unknown error')}")
                all_passed = False

            # Test 4: Chat completion using native /api/chat endpoint
            print("\n💭 Testing chat completion (native API)...")
            chat_result = self._test_chat()
            result.add_sub_test("Chat Completion", chat_result)
            if chat_result["success"]:
                print("✅ Chat completion successful")
                print(f"   📝 Message: {chat_result.get('user_message', 'N/A')[:50]}...")
                response_text = chat_result.get('response', 'N/A')
                print(f"   💬 Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}")
                print(f"   ⏱️  Duration: {chat_result.get('duration_seconds', 0):.2f}s")
            else:
                print(f"❌ Chat completion failed: {chat_result.get('message', 'Unknown error')}")
                all_passed = False

            if all_passed:
                print("\n" + "="*60)
                print("🎉 All Ollama native API tests passed successfully!")
                print("="*60)
                print(f"🔧 Endpoint: {self.ollama_base_url}")
                print(f"🤖 Model: {self.ollama_model_name}")
                print("="*60)
                result.complete(True, "All Ollama native API tests passed successfully")
            else:
                failed_tests = [
                    name
                    for name, test_result in result.sub_tests.items()
                    if not test_result.get("success", False)
                ]
                result.fail(
                    f"Ollama API tests failed: {', '.join(failed_tests)}",
                    remediation="Check Ollama service is running, model is installed (ollama pull <model>), and endpoint is accessible",
                )

        except Exception as e:
            error_msg = f"Ollama API test failed: {str(e)}"
            self.logger.error(f"💥 {error_msg}")
            print(f"💥 {error_msg}")
            result.fail(
                error_msg,
                error=e,
                remediation="Verify Ollama is installed and running (ollama serve)",
            )

        return result

    def _test_version(self) -> Dict[str, Any]:
        """Test Ollama API version endpoint"""
        try:
            response = requests.get(
                f"{self.ollama_base_url}/api/version",
                timeout=10
            )
            response.raise_for_status()
            version_data = response.json()

            return {
                "success": True,
                "message": f"Connected to Ollama version {version_data.get('version', 'unknown')}",
                "version": version_data.get('version', 'unknown'),
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "message": "Cannot connect to Ollama API - is Ollama running?",
                "remediation": "Start Ollama service with 'ollama serve' or check OLLAMA_BASE_URL",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Version check failed: {str(e)}",
                "remediation": "Verify Ollama API endpoint is correct",
            }

    def _test_list_models(self) -> Dict[str, Any]:
        """Test listing models using native /api/tags endpoint"""
        try:
            response = requests.get(
                f"{self.ollama_base_url}/api/tags",
                timeout=10
            )
            response.raise_for_status()
            tags_data = response.json()

            models = tags_data.get('models', [])
            model_names = [m.get('name', 'unknown') for m in models]

            # Check if our target model is available
            model_found = any(self.ollama_model_name in name for name in model_names)

            return {
                "success": True,
                "message": f"Found {len(models)} model(s)",
                "models": model_names,
                "model_found": model_found,
                "target_model": self.ollama_model_name,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list models: {str(e)}",
                "remediation": "Check Ollama API accessibility",
            }

    def _test_generate(self) -> Dict[str, Any]:
        """Test text generation using native /api/generate endpoint"""
        try:
            start_time = time.time()

            prompt = "What is the capital of France? Answer in one word."

            payload = {
                "model": self.ollama_model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": self.ollama_max_tokens,
                    "temperature": self.ollama_temperature,
                }
            }

            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=self.request_timeout
            )
            response.raise_for_status()

            duration = time.time() - start_time
            result_data = response.json()

            return {
                "success": True,
                "message": "Text generation successful",
                "prompt": prompt,
                "response": result_data.get('response', ''),
                "duration_seconds": duration,
                "eval_count": result_data.get('eval_count'),
                "prompt_eval_count": result_data.get('prompt_eval_count'),
                "total_duration_ns": result_data.get('total_duration'),
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": f"Generation timed out after {self.request_timeout}s",
                "remediation": "Increase OLLAMA_TIMEOUT or use a smaller model",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Generation failed: {str(e)}",
                "remediation": "Verify model is installed (ollama pull <model>)",
            }

    def _test_chat(self) -> Dict[str, Any]:
        """Test chat completion using native /api/chat endpoint"""
        try:
            start_time = time.time()

            user_message = "Hello! Can you introduce yourself in one sentence?"

            payload = {
                "model": self.ollama_model_name,
                "messages": [
                    {"role": "user", "content": user_message}
                ],
                "stream": False,
                "options": {
                    "num_predict": self.ollama_max_tokens,
                    "temperature": self.ollama_temperature,
                }
            }

            response = requests.post(
                f"{self.ollama_base_url}/api/chat",
                json=payload,
                timeout=self.request_timeout
            )
            response.raise_for_status()

            duration = time.time() - start_time
            result_data = response.json()

            message_content = result_data.get('message', {}).get('content', '')

            return {
                "success": True,
                "message": "Chat completion successful",
                "user_message": user_message,
                "response": message_content,
                "duration_seconds": duration,
                "eval_count": result_data.get('eval_count'),
                "prompt_eval_count": result_data.get('prompt_eval_count'),
                "total_duration_ns": result_data.get('total_duration'),
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": f"Chat timed out after {self.request_timeout}s",
                "remediation": "Increase OLLAMA_TIMEOUT or use a smaller model",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Chat failed: {str(e)}",
                "remediation": "Verify model supports chat format",
            }

    def test_with_custom_input(
        self,
        custom_prompt: str,
        custom_file_content: str = None,
        file_type: str = None,
        system_message: str = None,
    ) -> Dict[str, Any]:
        """Test with custom user input using Ollama native API"""
        self.logger.info(f"Starting custom input test with prompt: {custom_prompt[:100]}{'...' if len(custom_prompt) > 100 else ''}")
        print(f"🎯 Starting custom Ollama test with prompt: {custom_prompt[:100]}{'...' if len(custom_prompt) > 100 else ''}")

        try:
            start_time = time.time()

            # Prepare messages for chat API
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})

            # If file content is provided, include it in the prompt
            if custom_file_content:
                if file_type == "pdf":
                    user_content = f"Here is a PDF document to analyze:\n\n{custom_file_content}\n\nUser request: {custom_prompt}"
                elif file_type in ["jpg", "jpeg", "png"]:
                    # For vision models (like llava), Ollama supports base64 images
                    user_content = f"[Image provided as base64]\n\nUser request: {custom_prompt}"
                    # Note: For actual vision support, would need to use Ollama's vision model format
                else:
                    user_content = f"Here is some file content:\n\n{custom_file_content}\n\nUser request: {custom_prompt}"
                messages.append({"role": "user", "content": user_content})
            else:
                messages.append({"role": "user", "content": custom_prompt})

            payload = {
                "model": self.ollama_model_name,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": 500,  # Allow more tokens for custom responses
                    "temperature": self.ollama_temperature,
                }
            }

            response = requests.post(
                f"{self.ollama_base_url}/api/chat",
                json=payload,
                timeout=self.request_timeout
            )
            response.raise_for_status()

            duration = time.time() - start_time
            result_data = response.json()

            message_content = result_data.get('message', {}).get('content', '')

            return {
                "success": True,
                "message": "Custom input test successful",
                "model": self.ollama_model_name,
                "prompt": custom_prompt,
                "file_provided": bool(custom_file_content),
                "file_type": file_type or "none",
                "system_message": system_message or "None",
                "response_text": message_content,
                "response_time_ms": round(duration * 1000, 2),
                "response_length": len(message_content),
                "eval_count": result_data.get('eval_count'),
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Custom input test failed: {str(e)}",
                "error": str(e),
                "remediation": "Check Ollama configuration and model availability",
            }
