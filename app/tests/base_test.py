import logging
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from ..models import TestStatus


class TestResult:
    """Standardized test result structure"""

    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = datetime.now(timezone.utc)
        self.end_time = None
        self.duration_seconds = None
        self.status = TestStatus.PENDING
        self.message = ""
        self.details = {}
        self.sub_tests = {}
        self.error = None
        self.error_type = None
        self.traceback = None
        self.remediation = None
        self.logs = []

    def start(self):
        """Mark test as started"""
        self.start_time = datetime.now(timezone.utc)
        self.status = TestStatus.RUNNING

    def complete(self, success: bool, message: str, details: Dict[str, Any] = None):
        """Mark test as completed"""
        self.end_time = datetime.now(timezone.utc)
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.status = TestStatus.PASSED if success else TestStatus.FAILED
        self.message = message
        if details:
            self.details.update(details)

    def fail(self, message: str, error: Exception = None, remediation: str = None):
        """Mark test as failed"""
        self.end_time = datetime.now(timezone.utc)
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.status = TestStatus.FAILED
        self.message = message
        if error:
            self.error = str(error)
            self.error_type = type(error).__name__
            self.traceback = traceback.format_exc()
        self.remediation = remediation

    def skip(self, message: str):
        """Mark test as skipped"""
        self.end_time = datetime.now(timezone.utc)
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.status = TestStatus.SKIPPED
        self.message = message

    def add_sub_test(self, name: str, result: Dict[str, Any]):
        """Add a sub-test result"""
        self.sub_tests[name] = result

    def add_log(self, level: str, message: str):
        """Add a log entry"""
        self.logs.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "message": message,
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "test_name": self.test_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "message": self.message,
            "details": self.details,
            "sub_tests": self.sub_tests,
            "error": self.error,
            "error_type": self.error_type,
            "traceback": self.traceback,
            "remediation": self.remediation,
            "logs": self.logs,
        }


class BaseTest(ABC):
    """Base class for all infrastructure tests"""

    def __init__(self):
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    @property
    @abstractmethod
    def test_name(self) -> str:
        """Human-readable name of the test"""
        pass

    @property
    @abstractmethod
    def test_description(self) -> str:
        """Brief description of what the test does"""
        pass

    @property
    def test_id(self) -> str:
        """Unique identifier for the test"""
        return self.__class__.__name__.lower().replace("test", "")

    @property
    def is_optional(self) -> bool:
        """Whether this test is optional"""
        return False

    @property
    def depends_on(self) -> List[str]:
        """List of test IDs this test depends on"""
        return []

    @property
    def timeout_seconds(self) -> int:
        """Maximum time the test should take"""
        return 30

    @abstractmethod
    def run_test(self) -> TestResult:
        """Run the test and return result"""
        pass

    def is_configured(self) -> bool:
        """Check if the test is properly configured"""
        return True

    def get_configuration_help(self) -> str:
        """Return help text for configuring this test"""
        return f"No configuration required for {self.test_name}"

    def execute(self) -> TestResult:
        """Execute the test with proper error handling and logging"""
        result = TestResult(self.test_name)
        result.start()

        try:
            self.logger.info(f"Starting {self.test_name}")
            result.add_log("INFO", f"Starting {self.test_name}")

            # Check if test is configured
            if not self.is_configured():
                result.skip(f"Test not configured. {self.get_configuration_help()}")
                self.logger.warning(f"Skipping {self.test_name} - not configured")
                return result

            # Run the actual test with timeout
            start_time = time.time()
            test_result = self.run_test()

            # Check for timeout
            if time.time() - start_time > self.timeout_seconds:
                result.fail(
                    f"Test timed out after {self.timeout_seconds} seconds",
                    remediation=f"Check network connectivity and increase timeout if needed",
                )
                self.logger.error(f"{self.test_name} timed out")
                return result

            # Copy results from the test implementation
            if isinstance(test_result, TestResult):
                return test_result
            else:
                # Handle legacy format
                result.complete(
                    test_result.get("success", False),
                    test_result.get("message", "Test completed"),
                    test_result.get("details", {}),
                )

        except Exception as e:
            result.fail(
                f"Test failed with error: {str(e)}",
                error=e,
                remediation=self._get_error_remediation(e),
            )
            self.logger.error(f"{self.test_name} failed: {str(e)}")

        result.add_log(
            "INFO", f"Completed {self.test_name} with status {result.status.value}"
        )
        self.logger.info(
            f"Completed {self.test_name} with status {result.status.value}"
        )
        return result

    def _get_error_remediation(self, error: Exception) -> Optional[str]:
        """Get remediation suggestions based on error type"""
        error_type = type(error).__name__
        error_msg = str(error).lower()

        # Connection-related errors
        if "connection" in error_msg or "timeout" in error_msg:
            return (
                "Check network connectivity, firewall rules, and service availability"
            )
        elif "authentication" in error_msg or "permission" in error_msg:
            return "Verify credentials and permissions are correct"
        elif "not found" in error_msg or "does not exist" in error_msg:
            return "Ensure the service/resource exists and is properly configured"
        elif "ssl" in error_msg or "certificate" in error_msg:
            return "Check SSL/TLS configuration and certificate validity"
        else:
            return None


class TestSuite:
    """Manages and executes multiple tests"""

    def __init__(self):
        self.tests: Dict[str, BaseTest] = {}
        self.logger = logging.getLogger(__name__)

    def register_test(self, test: BaseTest):
        """Register a test with the suite"""
        self.tests[test.test_id] = test
        self.logger.info(f"Registered test: {test.test_name} ({test.test_id})")

    def get_test(self, test_id: str) -> Optional[BaseTest]:
        """Get a test by ID"""
        return self.tests.get(test_id)

    def list_tests(self) -> List[Dict[str, Any]]:
        """List all registered tests"""
        return [
            {
                "id": test.test_id,
                "name": test.test_name,
                "description": test.test_description,
                "is_optional": test.is_optional,
                "is_configured": test.is_configured(),
                "depends_on": test.depends_on,
            }
            for test in self.tests.values()
        ]

    def run_test(self, test_id: str) -> Optional[TestResult]:
        """Run a specific test"""
        test = self.get_test(test_id)
        if not test:
            self.logger.error(f"Test not found: {test_id}")
            return None

        return test.execute()

    def run_all_tests(self, skip_optional: bool = False) -> Dict[str, TestResult]:
        """Run all tests in dependency order"""
        results = {}

        # Sort tests by dependencies (simple approach)
        test_order = self._resolve_dependencies()

        for test_id in test_order:
            test = self.tests[test_id]

            # Skip optional tests if requested
            if skip_optional and test.is_optional:
                continue

            # Check if dependencies passed
            if not self._dependencies_met(test, results):
                result = TestResult(test.test_name)
                result.skip("Dependencies not met")
                results[test_id] = result
                continue

            results[test_id] = test.execute()

        return results

    def _resolve_dependencies(self) -> List[str]:
        """Resolve test execution order based on dependencies"""
        # Simple topological sort
        visited = set()
        order = []

        def visit(test_id: str):
            if test_id in visited:
                return
            visited.add(test_id)

            test = self.tests.get(test_id)
            if test:
                for dep in test.depends_on:
                    if dep in self.tests:
                        visit(dep)
                order.append(test_id)

        for test_id in self.tests:
            visit(test_id)

        return order

    def _dependencies_met(self, test: BaseTest, results: Dict[str, TestResult]) -> bool:
        """Check if test dependencies are met"""
        for dep_id in test.depends_on:
            if dep_id not in results:
                return False
            if results[dep_id].status != TestStatus.PASSED:
                return False
        return True


# Global test suite instance
test_suite = TestSuite()
