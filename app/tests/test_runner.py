from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
from .base_test import test_suite, TestResult
from .postgres_test_v2 import PostgreSQLTestV2
from .blob_storage_test import BlobStorageTest
from .pvc_test import PVCTest
from .ssl_test import SSLTest
from .openai_test import OpenAITest
from .document_intelligence_test import DocumentIntelligenceTest
from .llama_test import LlamaTest
from .minio_test import MinioTest
from .s3_test import S3Test
from .embedding_test import EmbeddingTest
from .cassandra_test import CassandraTest
from ..models import TestStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class TestRunner:
    """Manages test execution and results"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self._register_tests()

    def _register_tests(self):
        """Register all available tests"""
        # Register PostgreSQL test
        postgres_test = PostgreSQLTestV2()
        test_suite.register_test(postgres_test)

        # Register Blob Storage test
        blob_storage_test = BlobStorageTest()
        test_suite.register_test(blob_storage_test)

        # Register PVC test
        pvc_test = PVCTest()
        test_suite.register_test(pvc_test)

        # Register SSL test
        ssl_test = SSLTest()
        test_suite.register_test(ssl_test)

        # Register OpenAI test
        openai_test = OpenAITest()
        test_suite.register_test(openai_test)

        # Register Document Intelligence test
        doc_intel_test = DocumentIntelligenceTest()
        test_suite.register_test(doc_intel_test)

        # Register Llama test
        llama_test = LlamaTest()
        test_suite.register_test(llama_test)

        # Register Minio test
        minio_test = MinioTest()
        test_suite.register_test(minio_test)

        # Register S3 test
        s3_test = S3Test()
        test_suite.register_test(s3_test)

        # Register Embedding test
        embedding_test = EmbeddingTest()
        test_suite.register_test(embedding_test)

        # Register Cassandra test
        cassandra_test = CassandraTest()
        test_suite.register_test(cassandra_test)

        self.logger.info(f"Registered {len(test_suite.tests)} tests")

    def get_test_status(self) -> Dict[str, Any]:
        """Get current status of all tests"""
        return {
            "tests": self.test_results,
            "available_tests": test_suite.list_tests(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def run_test(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Run a specific test"""
        self.logger.info(f"Running test: {test_id}")

        result = test_suite.run_test(test_id)
        if not result:
            return None

        # Store result
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

        return self.test_results[test_id]

    def run_all_tests(self, skip_optional: bool = False) -> Dict[str, Any]:
        """Run all configured tests"""
        self.logger.info("Running all tests")

        start_time = datetime.now(timezone.utc)
        results = test_suite.run_all_tests(skip_optional=skip_optional)

        # Update stored results
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
        if test_id not in self.test_results:
            return []

        result_data = self.test_results[test_id].get("result", {})
        return result_data.get("logs", [])

    def get_remediation_suggestions(self, test_id: str) -> List[str]:
        """Get remediation suggestions for a failed test"""
        if test_id not in self.test_results:
            return []

        result_data = self.test_results[test_id].get("result", {})
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
        self.test_results.clear()
        self.logger.info("Cleared all test results")

    def get_test_summary(self) -> Dict[str, Any]:
        """Get a summary of all test results"""
        if not self.test_results:
            return {"total_tests": 0, "last_run": None, "overall_status": "not_run"}

        statuses = [result["status"] for result in self.test_results.values()]
        last_runs = [
            datetime.fromisoformat(result["last_run"])
            for result in self.test_results.values()
            if result["last_run"]
        ]

        return {
            "total_tests": len(self.test_results),
            "passed_count": statuses.count("passed"),
            "failed_count": statuses.count("failed"),
            "skipped_count": statuses.count("skipped"),
            "last_run": max(last_runs).isoformat() if last_runs else None,
            "overall_status": (
                "passed"
                if all(s == "passed" or s == "skipped" for s in statuses)
                else "failed"
            ),
        }


# Global test runner instance
test_runner = TestRunner()
