"""
Test service for managing infrastructure test execution and coordination.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..exceptions import ErrorCode, TestExecutionError, ValidationError
from ..repositories.test_repository import TestRepository
from ..tests.base_test import BaseTest, TestResult, TestSuite
from .base_service import BaseService


class TestService(BaseService):
    """Service for managing test execution, coordination, and results."""

    def __init__(self, test_repository: Optional[TestRepository] = None):
        super().__init__()
        self.test_suite = TestSuite()
        self.repository = test_repository or TestRepository()
        self.active_tests: Dict[str, asyncio.Task] = {}

    @property
    def service_name(self) -> str:
        return "TestService"

    async def initialize(self) -> None:
        """Initialize the test service and register all available tests."""
        await super().initialize()
        await self.repository.initialize()
        await self._register_all_tests()

    async def _register_all_tests(self) -> None:
        """Register all available test implementations."""
        # Import and register all test classes
        from ..tests.anthropic_test import AnthropicTest
        from ..tests.azure_openai_test import AzureOpenAITest
        from ..tests.bedrock_test import BedrockTest
        from ..tests.blob_storage_test import BlobStorageTest
        from ..tests.dedicated_embedding_test import DedicatedEmbeddingTest
        from ..tests.cassandra_test import CassandraTest
        from ..tests.dns_test import DNSTest
        from ..tests.document_intelligence_test import DocumentIntelligenceTest
        from ..tests.gemini_test import GeminiTest
        from ..tests.s3_compatible_test import S3CompatibleTest
        from ..tests.mistral_test import MistralTest
        from ..tests.openai_direct_test import OpenAIDirectTest
        from ..tests.postgres_test_v2 import PostgreSQLTestV2
        from ..tests.pvc_test import PVCTest
        from ..tests.s3_test import S3Test
        from ..tests.ssl_test import SSLTest
        from ..tests.gpu_test import GPUTest

        test_classes = [
            BlobStorageTest,
            S3Test,
            S3CompatibleTest,
            AzureOpenAITest,
            BedrockTest,
            OpenAIDirectTest,
            AnthropicTest,
            GeminiTest,
            MistralTest,
            DedicatedEmbeddingTest,
            DocumentIntelligenceTest,
            PostgreSQLTestV2,
            CassandraTest,
            PVCTest,
            GPUTest,
            DNSTest,
            SSLTest,
        ]

        for test_class in test_classes:
            try:
                test_instance = test_class()
                self.test_suite.register_test(test_instance)
                self.logger.info(f"Registered test: {test_instance.test_name}")
            except Exception as e:
                self.logger.error(
                    f"Failed to register test {test_class.__name__}: {str(e)}"
                )

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on test service."""
        base_health = await super().health_check()

        test_count = len(self.test_suite.tests)
        configured_count = sum(
            1 for test in self.test_suite.tests.values() if test.is_configured()
        )
        active_count = len(self.active_tests)

        base_health.update(
            {
                "total_tests": test_count,
                "configured_tests": configured_count,
                "active_tests": active_count,
                "repository_status": (
                    "connected" if self.repository.initialized else "disconnected"
                ),
            }
        )

        return base_health

    async def list_available_tests(self) -> List[Dict[str, Any]]:
        """
        Get list of all available tests with their configuration status.

        Returns:
            List of test information dictionaries
        """
        await self.ensure_initialized()

        tests = []
        for test in self.test_suite.tests.values():
            test_info = {
                "id": test.test_id,
                "name": test.test_name,
                "description": test.test_description,
                "is_optional": test.is_optional,
                "is_configured": test.is_configured(),
                "depends_on": test.depends_on,
                "timeout_seconds": test.timeout_seconds,
            }

            if not test.is_configured():
                test_info["configuration_help"] = test.get_configuration_help()

            tests.append(test_info)

        return sorted(tests, key=lambda x: x["name"])

    async def get_test_info(self, test_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific test.

        Args:
            test_id: The test identifier

        Returns:
            Test information dictionary or None if not found
        """
        await self.ensure_initialized()

        test = self.test_suite.get_test(test_id)
        if not test:
            return None

        return {
            "id": test.test_id,
            "name": test.test_name,
            "description": test.test_description,
            "is_optional": test.is_optional,
            "is_configured": test.is_configured(),
            "depends_on": test.depends_on,
            "timeout_seconds": test.timeout_seconds,
            "configuration_help": (
                test.get_configuration_help() if not test.is_configured() else None
            ),
            "is_active": test_id in self.active_tests,
        }

    async def execute_test(
        self,
        test_id: str,
        user_id: Optional[str] = None,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> TestResult:
        """
        Execute a single test with proper error handling and logging.

        Args:
            test_id: The test identifier
            user_id: Optional user ID for tracking
            custom_config: Optional custom configuration for the test

        Returns:
            TestResult with execution details

        Raises:
            ValidationError: If test_id is invalid
            TestExecutionError: If test execution fails
        """
        await self.ensure_initialized()

        test = self.test_suite.get_test(test_id)
        if not test:
            raise ValidationError(
                message=f"Test not found: {test_id}",
                error_code=ErrorCode.TEST_NOT_FOUND,
                field_name="test_id",
                provided_value=test_id,
                remediation="Use /api/tests to list available tests",
            )

        # Check if test is already running
        if test_id in self.active_tests:
            raise TestExecutionError(
                message=f"Test {test_id} is already running",
                error_code=ErrorCode.TEST_ALREADY_RUNNING,
                test_id=test_id,
                remediation="Wait for the current test to complete or cancel it first",
            )

        self.log_operation(
            "execute_test",
            {
                "test_id": test_id,
                "user_id": user_id,
                "has_custom_config": custom_config is not None,
            },
        )

        try:
            # Apply custom configuration if provided
            if custom_config:
                # This would need to be implemented based on how tests accept config
                pass

            # Execute the test
            start_time = datetime.now(timezone.utc)
            result = test.execute()

            # Store result in repository
            await self.repository.store_test_result(
                test_id=test_id,
                result=result,
                user_id=user_id,
                execution_time=start_time,
            )

            self.log_operation(
                "test_completed",
                {
                    "test_id": test_id,
                    "status": result.status.value,
                    "duration": result.duration_seconds,
                    "user_id": user_id,
                },
            )

            return result

        except Exception as e:
            error_msg = f"Test execution failed: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "test_id": test_id,
                    "user_id": user_id,
                    "error_type": type(e).__name__,
                },
            )

            raise TestExecutionError(
                message=error_msg,
                error_code=ErrorCode.TEST_EXECUTION_FAILED,
                test_id=test_id,
                details={"original_error": str(e)},
                remediation="Check test configuration and logs for details",
            )

    async def execute_test_async(
        self,
        test_id: str,
        user_id: Optional[str] = None,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Execute a test asynchronously and return a task ID for monitoring.

        Args:
            test_id: The test identifier
            user_id: Optional user ID for tracking
            custom_config: Optional custom configuration

        Returns:
            Task ID for monitoring the async execution

        Raises:
            ValidationError: If test_id is invalid
            TestExecutionError: If test is already running
        """
        await self.ensure_initialized()

        if test_id in self.active_tests:
            raise TestExecutionError(
                message=f"Test {test_id} is already running",
                error_code=ErrorCode.TEST_ALREADY_RUNNING,
                test_id=test_id,
                remediation="Wait for the current test to complete or cancel it first",
            )

        # Create async task for test execution
        task = asyncio.create_task(self.execute_test(test_id, user_id, custom_config))

        task_id = f"{test_id}_{datetime.now(timezone.utc).isoformat()}"
        self.active_tests[task_id] = task

        # Clean up completed tasks
        task.add_done_callback(lambda t: self.active_tests.pop(task_id, None))

        return task_id

    async def get_test_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of an async test execution.

        Args:
            task_id: The task identifier returned by execute_test_async

        Returns:
            Dictionary with task status information or None if not found
        """
        task = self.active_tests.get(task_id)
        if not task:
            return None

        status = {
            "task_id": task_id,
            "status": "running" if not task.done() else "completed",
            "created_at": task_id.split("_", 1)[1],  # Extract timestamp
        }

        if task.done():
            try:
                result = task.result()
                status["result"] = result.to_dict()
                status["success"] = result.status.value == "passed"
            except Exception as e:
                status["error"] = str(e)
                status["success"] = False

        return status

    async def cancel_test(self, task_id: str) -> bool:
        """
        Cancel an async test execution.

        Args:
            task_id: The task identifier to cancel

        Returns:
            True if task was cancelled, False if not found or already completed
        """
        task = self.active_tests.get(task_id)
        if not task or task.done():
            return False

        task.cancel()
        self.active_tests.pop(task_id, None)

        self.log_operation("test_cancelled", {"task_id": task_id})
        return True

    async def execute_test_suite(
        self,
        test_ids: Optional[List[str]] = None,
        skip_optional: bool = False,
        user_id: Optional[str] = None,
    ) -> Dict[str, TestResult]:
        """
        Execute multiple tests in proper dependency order.

        Args:
            test_ids: Specific tests to run (None = all tests)
            skip_optional: Whether to skip optional tests
            user_id: Optional user ID for tracking

        Returns:
            Dictionary mapping test_id to TestResult
        """
        await self.ensure_initialized()

        if test_ids:
            # Validate all test IDs exist
            for test_id in test_ids:
                if not self.test_suite.get_test(test_id):
                    raise ValidationError(
                        message=f"Test not found: {test_id}",
                        error_code=ErrorCode.TEST_NOT_FOUND,
                        field_name="test_ids",
                        provided_value=test_id,
                        remediation="Use /api/tests to list available tests",
                    )

        self.log_operation(
            "execute_test_suite",
            {
                "test_count": len(test_ids) if test_ids else len(self.test_suite.tests),
                "skip_optional": skip_optional,
                "user_id": user_id,
            },
        )

        try:
            # Execute tests using the test suite
            if test_ids:
                # Create a temporary suite with only specified tests
                temp_suite = TestSuite()
                for test_id in test_ids:
                    test = self.test_suite.get_test(test_id)
                    temp_suite.register_test(test)
                results = temp_suite.run_all_tests(skip_optional)
            else:
                results = self.test_suite.run_all_tests(skip_optional)

            # Store all results
            for test_id, result in results.items():
                await self.repository.store_test_result(
                    test_id=test_id,
                    result=result,
                    user_id=user_id,
                    execution_time=datetime.now(timezone.utc),
                )

            self.log_operation(
                "test_suite_completed",
                {
                    "total_tests": len(results),
                    "passed_tests": sum(
                        1 for r in results.values() if r.status.value == "passed"
                    ),
                    "failed_tests": sum(
                        1 for r in results.values() if r.status.value == "failed"
                    ),
                    "user_id": user_id,
                },
            )

            return results

        except Exception as e:
            raise TestExecutionError(
                message=f"Test suite execution failed: {str(e)}",
                error_code=ErrorCode.TEST_EXECUTION_FAILED,
                details={"original_error": str(e)},
                remediation="Check individual test configurations and logs",
            )

    async def get_test_history(
        self,
        test_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get historical test execution results.

        Args:
            test_id: Filter by specific test (None = all tests)
            user_id: Filter by specific user (None = all users)
            limit: Maximum number of results to return

        Returns:
            List of historical test results
        """
        await self.ensure_initialized()

        return await self.repository.get_test_history(
            test_id=test_id, user_id=user_id, limit=limit
        )
