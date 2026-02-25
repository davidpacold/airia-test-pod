import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models import TestStatus
from .base_test import TestResult, test_suite

# Storage tests
from .blob_storage_test import BlobStorageTest
from .s3_test import S3Test
from .s3_compatible_test import S3CompatibleTest

# AI provider tests
from .azure_openai_test import AzureOpenAITest
from .bedrock_test import BedrockTest
from .openai_direct_test import OpenAIDirectTest
from .anthropic_test import AnthropicTest
from .gemini_test import GeminiTest
from .mistral_test import MistralTest
from .azure_ml_vision_test import VisionModelTest
from .dedicated_embedding_test import DedicatedEmbeddingTest

# Document processing
from .document_intelligence_test import DocumentIntelligenceTest

# Database tests
from .postgres_test_v2 import PostgreSQLTestV2
from .cassandra_test import CassandraTest

# Infrastructure tests
from .pvc_test import PVCTest
from .gpu_test import GPUTest
from .dns_test import DNSTest
from .ssl_test import SSLTest


class TestRunner:
    """Manages test execution and results"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._last_run_time: Optional[datetime] = None
        self._register_tests()

    def _register_tests(self):
        """Register all 18 test cards"""
        tests = [
            # Storage (3)
            BlobStorageTest(),
            S3Test(),
            S3CompatibleTest(),
            # AI providers (8)
            AzureOpenAITest(),
            BedrockTest(),
            OpenAIDirectTest(),
            AnthropicTest(),
            GeminiTest(),
            MistralTest(),
            VisionModelTest(),
            DedicatedEmbeddingTest(),
            # Document processing (1)
            DocumentIntelligenceTest(),
            # Databases (2)
            PostgreSQLTestV2(),
            CassandraTest(),
            # Infrastructure (4)
            PVCTest(),
            GPUTest(),
            DNSTest(),
            SSLTest(),
        ]
        for test in tests:
            test_suite.register_test(test)
        self.logger.info(f"Registered {len(test_suite.tests)} tests")

    def get_test_status(self) -> Dict[str, Any]:
        """Get current status of all tests"""
        with self._lock:
            results_copy = dict(self.test_results)
        return {
            "tests": results_copy,
            "available_tests": test_suite.list_tests(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def run_test(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Run a specific test"""
        self.logger.info(f"Running test: {test_id}")

        result = test_suite.run_test(test_id)
        if not result:
            return None

        stored = {
            "name": result.test_name,
            "status": result.status.value,
            "last_run": (
                result.end_time.isoformat()
                if result.end_time
                else datetime.now(timezone.utc).isoformat()
            ),
            "duration_seconds": result.duration_seconds,
            "message": result.message,
            "result": result.to_dict(),
        }

        with self._lock:
            self.test_results[test_id] = stored

        return stored

    def run_all_tests(self, skip_optional: bool = False) -> Dict[str, Any]:
        """Run all configured tests"""
        self.logger.info("Running all tests")

        start_time = datetime.now(timezone.utc)
        results = test_suite.run_all_tests(skip_optional=skip_optional)

        with self._lock:
            for test_id, result in results.items():
                self.test_results[test_id] = {
                    "name": result.test_name,
                    "status": result.status.value,
                    "last_run": (
                        result.end_time.isoformat()
                        if result.end_time
                        else datetime.now(timezone.utc).isoformat()
                    ),
                    "duration_seconds": result.duration_seconds,
                    "message": result.message,
                    "result": result.to_dict(),
                }
            self._last_run_time = datetime.now(timezone.utc)

        # Calculate overall status
        all_passed = all(
            r.status == TestStatus.PASSED
            for r in results.values()
            if r.status not in [TestStatus.SKIPPED]
        )

        end_time = datetime.now(timezone.utc)

        return {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "overall_status": "passed" if all_passed else "failed",
            "test_count": len(results),
            "passed_count": len(
                [r for r in results.values() if r.status == TestStatus.PASSED]
            ),
            "failed_count": len(
                [r for r in results.values() if r.status == TestStatus.FAILED]
            ),
            "skipped_count": len(
                [r for r in results.values() if r.status == TestStatus.SKIPPED]
            ),
            "results": {
                test_id: result.to_dict() for test_id, result in results.items()
            },
        }

    def get_test_logs(self, test_id: str) -> List[Dict[str, Any]]:
        """Get logs for a specific test"""
        with self._lock:
            test_result = self.test_results.get(test_id)
        if not test_result:
            return []

        result_data = test_result.get("result", {})
        return result_data.get("logs", [])

    def get_remediation_suggestions(self, test_id: str) -> List[str]:
        """Get remediation suggestions for a failed test"""
        with self._lock:
            test_result = self.test_results.get(test_id)
        if not test_result:
            return []

        result_data = test_result.get("result", {})
        suggestions = []

        # Add specific remediation if available
        if result_data.get("remediation"):
            suggestions.append(result_data["remediation"])

        # Add sub-test remediations
        for sub_test in result_data.get("sub_tests", {}).values():
            if sub_test.get("remediation"):
                suggestions.append(sub_test["remediation"])

        return suggestions

    def clear_results(self):
        """Clear all test results"""
        with self._lock:
            self.test_results.clear()
            self._last_run_time = None
        self.logger.info("Cleared all test results")

    def get_test_summary(self) -> Dict[str, Any]:
        """Get a summary of all test results"""
        with self._lock:
            results_copy = dict(self.test_results)
        if not results_copy:
            return {"total_tests": 0, "last_run": None, "overall_status": "not_run"}

        statuses = [result["status"] for result in results_copy.values()]
        last_runs = [
            datetime.fromisoformat(result["last_run"])
            for result in results_copy.values()
            if result["last_run"]
        ]

        return {
            "total_tests": len(results_copy),
            "passed_count": statuses.count("passed"),
            "failed_count": statuses.count("failed"),
            "skipped_count": statuses.count("skipped"),
            "last_run": max(last_runs).isoformat() if last_runs else None,
            "overall_status": (
                "passed"
                if all(s in ("passed", "skipped") for s in statuses)
                else "running"
                if any(s in ("pending", "running") for s in statuses)
                else "failed"
            ),
        }


# Global test runner instance
test_runner = TestRunner()
