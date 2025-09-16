import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import openai
from openai import OpenAI

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from ..models import TestStatus
from .base_test import BaseTest, TestResult


class EmbeddingTest(BaseTest):
    """Test OpenAI-compatible embedding model endpoints"""

    def __init__(self):
        super().__init__()
        # Get embedding configuration from environment
        self.api_key = os.getenv("EMBEDDING_API_KEY", "")
        self.base_url = os.getenv("EMBEDDING_BASE_URL", "")
        self.model_name = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-ada-002")
        self.custom_headers = {}

        # Parse custom headers if provided
        custom_headers_str = os.getenv("EMBEDDING_CUSTOM_HEADERS", "")
        if custom_headers_str:
            try:
                # Expected format: "Header1:Value1,Header2:Value2"
                for header_pair in custom_headers_str.split(","):
                    if ":" in header_pair:
                        key, value = header_pair.split(":", 1)
                        self.custom_headers[key.strip()] = value.strip()
            except:
                pass  # Ignore malformed headers

    @property
    def test_name(self) -> str:
        return "Embedding Models"

    @property
    def test_description(self) -> str:
        return (
            "Tests OpenAI-compatible embedding model endpoints for text vectorization"
        )

    @property
    def test_id(self) -> str:
        return "embeddings"

    @property
    def is_optional(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 45

    def is_configured(self) -> bool:
        """Check if embedding service is configured"""
        return bool(self.api_key and self.base_url and self.model_name)

    def get_configuration_help(self) -> str:
        return (
            "Embedding model testing requires configuration. "
            "Configure using environment variables: "
            "EMBEDDING_API_KEY (API key for authentication), "
            "EMBEDDING_BASE_URL (e.g., https://api.openai.com/v1 or custom endpoint), "
            "EMBEDDING_MODEL_NAME (default: text-embedding-ada-002), "
            "EMBEDDING_CUSTOM_HEADERS (optional: Header1:Value1,Header2:Value2)"
        )

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        try:
            if not self.is_configured():
                result.skip("Embedding model not configured")
                return result

            # Test 1: Basic embedding generation
            single_embedding_result = self._test_single_embedding()
            result.add_sub_test("single_embedding", single_embedding_result)

            # Test 2: Batch embedding generation
            batch_embedding_result = self._test_batch_embeddings()
            result.add_sub_test("batch_embeddings", batch_embedding_result)

            # Test 3: Empty text handling
            empty_text_result = self._test_empty_text_handling()
            result.add_sub_test("empty_text_handling", empty_text_result)

            # Test 4: Large text handling
            large_text_result = self._test_large_text_handling()
            result.add_sub_test("large_text_handling", large_text_result)

            # Test 5: Similarity validation (optional)
            if single_embedding_result["success"] and batch_embedding_result["success"]:
                similarity_result = self._test_embedding_similarity()
                result.add_sub_test("similarity_validation", similarity_result)

            # Determine overall success
            critical_tests_passed = (
                single_embedding_result["success"] and batch_embedding_result["success"]
            )

            if critical_tests_passed:
                embedding_dim = single_embedding_result.get("details", {}).get(
                    "dimension", "unknown"
                )
                result.complete(
                    True,
                    "Embedding model tests completed successfully",
                    {
                        "endpoint": self.base_url,
                        "model": self.model_name,
                        "embedding_dimension": embedding_dim,
                    },
                )
            else:
                failed_tests = []
                if not single_embedding_result["success"]:
                    failed_tests.append("single_embedding")
                if not batch_embedding_result["success"]:
                    failed_tests.append("batch_embeddings")

                result.fail(
                    f"Embedding model tests failed: {', '.join(failed_tests)}",
                    remediation="Check embedding API endpoint, credentials, and model availability",
                )

        except Exception as e:
            result.fail(
                f"Embedding test failed: {str(e)}",
                error=e,
                remediation="Check embedding service configuration and network connectivity",
            )

        return result

    def _get_client(self):
        """Create OpenAI client for embedding service"""
        client_params = {"api_key": self.api_key, "base_url": self.base_url}

        # Add custom headers if provided
        if self.custom_headers:
            client_params["default_headers"] = self.custom_headers

        return OpenAI(**client_params)

    def _test_single_embedding(self) -> Dict[str, Any]:
        """Test generating embedding for a single text"""
        test_text = "This is a test sentence for embedding generation."

        try:
            client = self._get_client()

            start_time = datetime.now()
            response = client.embeddings.create(
                model=self.model_name, input=test_text, encoding_format="float"
            )
            end_time = datetime.now()

            embedding = response.data[0].embedding

            # Validate embedding
            if not embedding or len(embedding) == 0:
                return {
                    "success": False,
                    "message": "Received empty embedding",
                    "remediation": "Check model configuration and API response format",
                }

            # Basic validation
            if not isinstance(embedding, list) or not all(
                isinstance(x, (int, float)) for x in embedding
            ):
                return {
                    "success": False,
                    "message": "Invalid embedding format received",
                    "remediation": "Embedding should be a list of numerical values",
                }

            response_time = (end_time - start_time).total_seconds()

            return {
                "success": True,
                "message": f"Successfully generated embedding for single text",
                "details": {
                    "input_text_length": len(test_text),
                    "dimension": len(embedding),
                    "response_time_seconds": round(response_time, 3),
                    "embedding_range": {
                        "min": round(min(embedding), 6),
                        "max": round(max(embedding), 6),
                    },
                    "usage": {
                        "prompt_tokens": (
                            response.usage.prompt_tokens
                            if hasattr(response, "usage") and response.usage is not None
                            else None
                        ),
                        "total_tokens": (
                            response.usage.total_tokens
                            if hasattr(response, "usage") and response.usage is not None
                            else None
                        ),
                    },
                },
            }

        except openai.AuthenticationError as e:
            return {
                "success": False,
                "message": "Authentication failed",
                "error": str(e),
                "remediation": "Check EMBEDDING_API_KEY configuration",
            }
        except openai.NotFoundError as e:
            return {
                "success": False,
                "message": f"Model '{self.model_name}' not found",
                "error": str(e),
                "remediation": "Check EMBEDDING_MODEL_NAME configuration",
            }
        except openai.RateLimitError as e:
            return {
                "success": False,
                "message": "Rate limit exceeded",
                "error": str(e),
                "remediation": "Check API usage limits and try again later",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Single embedding generation failed: {str(e)}",
                "error": str(e),
            }

    def _test_batch_embeddings(self) -> Dict[str, Any]:
        """Test generating embeddings for multiple texts"""
        test_texts = [
            "First test sentence for batch embedding.",
            "Second test sentence with different content.",
            "Third sentence to validate batch processing.",
        ]

        try:
            client = self._get_client()

            start_time = datetime.now()
            response = client.embeddings.create(
                model=self.model_name, input=test_texts, encoding_format="float"
            )
            end_time = datetime.now()

            if len(response.data) != len(test_texts):
                return {
                    "success": False,
                    "message": f"Expected {len(test_texts)} embeddings, got {len(response.data)}",
                    "remediation": "Check batch processing support",
                }

            embeddings = [item.embedding for item in response.data]

            # Validate all embeddings
            for i, embedding in enumerate(embeddings):
                if not embedding or len(embedding) == 0:
                    return {
                        "success": False,
                        "message": f"Received empty embedding for text {i+1}",
                        "remediation": "Check batch processing configuration",
                    }

            response_time = (end_time - start_time).total_seconds()

            return {
                "success": True,
                "message": f"Successfully generated {len(embeddings)} batch embeddings",
                "details": {
                    "batch_size": len(test_texts),
                    "embedding_dimension": len(embeddings[0]) if embeddings else 0,
                    "response_time_seconds": round(response_time, 3),
                    "avg_time_per_embedding": (
                        round(response_time / len(embeddings), 3) if embeddings else 0
                    ),
                    "usage": {
                        "prompt_tokens": (
                            response.usage.prompt_tokens
                            if hasattr(response, "usage") and response.usage is not None
                            else None
                        ),
                        "total_tokens": (
                            response.usage.total_tokens
                            if hasattr(response, "usage") and response.usage is not None
                            else None
                        ),
                    },
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Batch embedding generation failed: {str(e)}",
                "error": str(e),
            }

    def _test_empty_text_handling(self) -> Dict[str, Any]:
        """Test handling of empty or whitespace-only text"""
        try:
            client = self._get_client()

            # Test with empty string
            response = client.embeddings.create(
                model=self.model_name, input="", encoding_format="float"
            )

            embedding = response.data[0].embedding

            return {
                "success": True,
                "message": "Successfully handled empty text input",
                "details": {
                    "empty_embedding_dimension": len(embedding) if embedding else 0,
                    "handled_gracefully": True,
                },
            }

        except openai.BadRequestError as e:
            # Some APIs may reject empty input, which is acceptable
            return {
                "success": True,
                "message": "API correctly rejected empty input",
                "details": {"rejects_empty_input": True, "error_message": str(e)},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to handle empty text: {str(e)}",
                "error": str(e),
            }

    def _test_large_text_handling(self) -> Dict[str, Any]:
        """Test handling of large text input"""
        # Create a reasonably large text (but not exceeding typical token limits)
        large_text = "This is a longer test sentence. " * 50  # ~350 words

        try:
            client = self._get_client()

            start_time = datetime.now()
            response = client.embeddings.create(
                model=self.model_name, input=large_text, encoding_format="float"
            )
            end_time = datetime.now()

            embedding = response.data[0].embedding
            response_time = (end_time - start_time).total_seconds()

            return {
                "success": True,
                "message": "Successfully processed large text input",
                "details": {
                    "input_text_length": len(large_text),
                    "input_word_count": len(large_text.split()),
                    "embedding_dimension": len(embedding),
                    "response_time_seconds": round(response_time, 3),
                    "usage": {
                        "prompt_tokens": (
                            response.usage.prompt_tokens
                            if hasattr(response, "usage") and response.usage is not None
                            else None
                        ),
                        "total_tokens": (
                            response.usage.total_tokens
                            if hasattr(response, "usage") and response.usage is not None
                            else None
                        ),
                    },
                },
            }

        except openai.BadRequestError as e:
            if "token" in str(e).lower() or "length" in str(e).lower():
                return {
                    "success": True,
                    "message": "API correctly rejected text exceeding token limits",
                    "details": {"enforces_token_limits": True, "error_message": str(e)},
                }
            return {
                "success": False,
                "message": f"Unexpected error with large text: {str(e)}",
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Large text handling failed: {str(e)}",
                "error": str(e),
            }

    def _test_embedding_similarity(self) -> Dict[str, Any]:
        """Test that similar texts produce similar embeddings"""
        similar_texts = [
            "The cat sat on the mat.",
            "A cat was sitting on the mat.",
            "Dogs are running in the park.",
        ]

        try:
            client = self._get_client()

            response = client.embeddings.create(
                model=self.model_name, input=similar_texts, encoding_format="float"
            )

            embeddings = [item.embedding for item in response.data]

            if not HAS_NUMPY:
                return {
                    "success": True,
                    "message": "Similarity validation skipped (numpy not available)",
                    "details": {"skipped_reason": "numpy dependency not found"},
                }

            # Calculate cosine similarities
            def cosine_similarity(a, b):
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

            # Convert to numpy arrays
            emb1 = np.array(embeddings[0])
            emb2 = np.array(embeddings[1])
            emb3 = np.array(embeddings[2])

            # Calculate similarities
            sim_similar = cosine_similarity(emb1, emb2)  # Should be high
            sim_different = cosine_similarity(emb1, emb3)  # Should be lower

            return {
                "success": True,
                "message": "Embedding similarity validation completed",
                "details": {
                    "similar_texts_similarity": round(float(sim_similar), 4),
                    "different_texts_similarity": round(float(sim_different), 4),
                    "similarity_makes_sense": float(sim_similar) > float(sim_different),
                    "high_similarity_threshold": float(sim_similar) > 0.7,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Similarity validation failed: {str(e)}",
                "error": str(e),
            }

    def test_with_custom_input(
        self,
        custom_text: str,
        custom_file_content: str = None,
        file_type: str = None,
        batch_texts: List[str] = None,
    ) -> Dict[str, Any]:
        """Test embedding generation with custom user input"""
        try:
            if not self.is_configured():
                return {
                    "success": False,
                    "message": "Embedding model not configured",
                    "remediation": self.get_configuration_help(),
                }

            client = self._get_client()
            start_time = datetime.now()

            # Prepare input text(s)
            input_texts = []

            # Add custom text
            if custom_text:
                input_texts.append(custom_text)

            # Add file content if provided
            if custom_file_content:
                if file_type == "pdf":
                    input_texts.append(f"PDF Content:\n{custom_file_content}")
                elif file_type in ["jpg", "jpeg", "png"]:
                    # For images, we can't generate text embeddings directly
                    # Instead, we'll create a description
                    input_texts.append(
                        f"Image file ({file_type.upper()}) - Note: This is base64 encoded image data, not suitable for text embeddings"
                    )
                else:
                    # Text files
                    input_texts.append(f"File Content:\n{custom_file_content}")

            # Add batch texts if provided
            if batch_texts:
                input_texts.extend(batch_texts)

            # If no input provided, use default
            if not input_texts:
                input_texts = ["Default embedding test text"]

            # Determine if single or batch processing
            is_batch = len(input_texts) > 1
            embedding_input = input_texts if is_batch else input_texts[0]

            # Generate embeddings
            response = client.embeddings.create(
                model=self.model_name, input=embedding_input, encoding_format="float"
            )

            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            # Process results
            embeddings_data = response.data
            embeddings = [item.embedding for item in embeddings_data]

            # Calculate embedding statistics
            embedding_stats = []
            for i, embedding in enumerate(embeddings):
                stats = {
                    "index": i,
                    "input_text": (
                        input_texts[i][:100] + "..."
                        if len(input_texts[i]) > 100
                        else input_texts[i]
                    ),
                    "dimension": len(embedding),
                    "embedding_range": {
                        "min": round(min(embedding), 6),
                        "max": round(max(embedding), 6),
                        "mean": round(sum(embedding) / len(embedding), 6),
                    },
                    "vector_norm": (
                        round(float(np.linalg.norm(embedding)), 6)
                        if HAS_NUMPY
                        else None
                    ),
                }
                embedding_stats.append(stats)

            # Calculate similarities if multiple embeddings
            similarities = []
            if len(embeddings) > 1 and HAS_NUMPY:

                def cosine_similarity(a, b):
                    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

                for i in range(len(embeddings)):
                    for j in range(i + 1, len(embeddings)):
                        sim = cosine_similarity(
                            np.array(embeddings[i]), np.array(embeddings[j])
                        )
                        similarities.append(
                            {
                                "text1_index": i,
                                "text2_index": j,
                                "similarity": round(float(sim), 4),
                                "text1_preview": (
                                    input_texts[i][:50] + "..."
                                    if len(input_texts[i]) > 50
                                    else input_texts[i]
                                ),
                                "text2_preview": (
                                    input_texts[j][:50] + "..."
                                    if len(input_texts[j]) > 50
                                    else input_texts[j]
                                ),
                            }
                        )

            return {
                "success": True,
                "message": "Custom embedding generation successful",
                "model": self.model_name,
                "custom_text_provided": bool(custom_text),
                "file_provided": bool(custom_file_content),
                "file_type": file_type or "none",
                "batch_size": len(input_texts),
                "is_batch_processing": is_batch,
                "response_time_ms": round(response_time * 1000, 2),
                "embedding_stats": embedding_stats,
                "similarities": similarities if similarities else None,
                "total_tokens_used": (
                    response.usage.total_tokens
                    if hasattr(response, "usage") and response.usage is not None
                    else None
                ),
                "embeddings_generated": len(embeddings),
                "embedding_dimension": len(embeddings[0]) if embeddings else 0,
            }

        except openai.AuthenticationError as e:
            return {
                "success": False,
                "message": "Authentication failed",
                "error": str(e),
                "remediation": "Check EMBEDDING_API_KEY configuration",
            }
        except openai.NotFoundError as e:
            return {
                "success": False,
                "message": f"Model '{self.model_name}' not found",
                "error": str(e),
                "remediation": "Check EMBEDDING_MODEL_NAME configuration",
            }
        except openai.RateLimitError as e:
            return {
                "success": False,
                "message": "Rate limit exceeded",
                "error": str(e),
                "remediation": "Check API usage limits and try again later",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Custom embedding test failed: {str(e)}",
                "error": str(e),
                "remediation": "Check embedding service configuration and input format",
            }
