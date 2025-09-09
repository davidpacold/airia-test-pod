"""
Repository for storing and retrieving test execution results and history.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..tests.base_test import TestResult
from .base_repository import InMemoryRepository


class TestRepository(InMemoryRepository):
    """Repository for managing test execution data."""

    @property
    def repository_name(self) -> str:
        return "TestRepository"

    async def initialize(self) -> None:
        """Initialize the test repository."""
        await super().initialize()

        # Initialize data structures
        if "test_results" not in self.data:
            await self.store_data("test_results", [])
        if "test_configurations" not in self.data:
            await self.store_data("test_configurations", {})
        if "test_metadata" not in self.data:
            await self.store_data("test_metadata", {})

    async def store_test_result(
        self,
        test_id: str,
        result: TestResult,
        user_id: Optional[str] = None,
        execution_time: Optional[datetime] = None,
    ) -> str:
        """
        Store a test execution result.

        Args:
            test_id: The test identifier
            result: TestResult object
            user_id: User who executed the test
            execution_time: When the test was executed

        Returns:
            Unique result ID for the stored result
        """
        execution_time = execution_time or datetime.now(timezone.utc)
        result_id = f"{test_id}_{execution_time.isoformat()}_{user_id or 'anonymous'}"

        # Convert TestResult to dict and add metadata
        result_data = result.to_dict()
        result_data.update(
            {
                "result_id": result_id,
                "test_id": test_id,
                "user_id": user_id,
                "execution_time": execution_time.isoformat(),
                "stored_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        # Get current results list
        results = await self.get_data("test_results") or []
        results.append(result_data)

        # Keep only last 1000 results to prevent memory issues
        if len(results) > 1000:
            results = results[-1000:]

        await self.store_data("test_results", results)

        self.log_operation(
            "store_test_result",
            {
                "result_id": result_id,
                "test_id": test_id,
                "status": result.status.value,
                "user_id": user_id,
            },
        )

        return result_id

    async def get_test_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific test result by ID.

        Args:
            result_id: The result identifier

        Returns:
            Test result dictionary or None if not found
        """
        results = await self.get_data("test_results") or []

        for result in results:
            if result.get("result_id") == result_id:
                return result

        return None

    async def get_test_history(
        self,
        test_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get historical test results with optional filtering.

        Args:
            test_id: Filter by specific test
            user_id: Filter by specific user
            limit: Maximum number of results
            status_filter: Filter by test status (passed, failed, skipped)

        Returns:
            List of test result dictionaries
        """
        results = await self.get_data("test_results") or []

        # Apply filters
        filtered_results = []
        for result in results:
            if test_id and result.get("test_id") != test_id:
                continue
            if user_id and result.get("user_id") != user_id:
                continue
            if status_filter and result.get("status") != status_filter:
                continue

            filtered_results.append(result)

        # Sort by execution time (newest first) and limit
        filtered_results.sort(key=lambda x: x.get("execution_time", ""), reverse=True)

        self.log_operation(
            "get_test_history",
            {
                "test_id": test_id,
                "user_id": user_id,
                "limit": limit,
                "status_filter": status_filter,
                "results_count": len(filtered_results[:limit]),
            },
        )

        return filtered_results[:limit]

    async def get_test_statistics(
        self, test_id: Optional[str] = None, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get test execution statistics.

        Args:
            test_id: Filter by specific test (None = all tests)
            days: Number of days to look back

        Returns:
            Dictionary with test statistics
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        results = await self.get_data("test_results") or []

        # Filter by date and test_id
        filtered_results = []
        for result in results:
            execution_time_str = result.get("execution_time", "")
            try:
                execution_time = datetime.fromisoformat(
                    execution_time_str.replace("Z", "+00:00")
                )
                if execution_time >= cutoff_date:
                    if not test_id or result.get("test_id") == test_id:
                        filtered_results.append(result)
            except ValueError:
                continue

        # Calculate statistics
        total_executions = len(filtered_results)
        if total_executions == 0:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "average_duration": 0.0,
                "status_breakdown": {},
                "test_breakdown": {},
                "date_range_days": days,
            }

        passed_count = sum(1 for r in filtered_results if r.get("status") == "passed")
        failed_count = sum(1 for r in filtered_results if r.get("status") == "failed")
        skipped_count = sum(1 for r in filtered_results if r.get("status") == "skipped")

        # Calculate average duration (excluding None values)
        durations = [
            r.get("duration_seconds")
            for r in filtered_results
            if r.get("duration_seconds")
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Test breakdown
        test_breakdown = {}
        for result in filtered_results:
            tid = result.get("test_id", "unknown")
            if tid not in test_breakdown:
                test_breakdown[tid] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                }
            test_breakdown[tid]["total"] += 1
            test_breakdown[tid][result.get("status", "unknown")] += 1

        stats = {
            "total_executions": total_executions,
            "success_rate": (
                round(passed_count / total_executions * 100, 2)
                if total_executions > 0
                else 0.0
            ),
            "average_duration": round(avg_duration, 2),
            "status_breakdown": {
                "passed": passed_count,
                "failed": failed_count,
                "skipped": skipped_count,
            },
            "test_breakdown": test_breakdown,
            "date_range_days": days,
        }

        self.log_operation(
            "get_test_statistics",
            {
                "test_id": test_id,
                "days": days,
                "total_executions": total_executions,
                "success_rate": stats["success_rate"],
            },
        )

        return stats

    async def store_test_configuration(
        self, test_id: str, configuration: Dict[str, Any], user_id: Optional[str] = None
    ) -> None:
        """
        Store a test configuration for reuse.

        Args:
            test_id: The test identifier
            configuration: Configuration dictionary
            user_id: User who created the configuration
        """
        configurations = await self.get_data("test_configurations") or {}

        if test_id not in configurations:
            configurations[test_id] = []

        config_data = {
            "configuration": configuration,
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config_id": f"{test_id}_{len(configurations[test_id])}",
        }

        configurations[test_id].append(config_data)
        await self.store_data("test_configurations", configurations)

        self.log_operation(
            "store_test_configuration",
            {
                "test_id": test_id,
                "user_id": user_id,
                "config_id": config_data["config_id"],
            },
        )

    async def get_test_configurations(self, test_id: str) -> List[Dict[str, Any]]:
        """
        Get stored configurations for a test.

        Args:
            test_id: The test identifier

        Returns:
            List of configuration dictionaries
        """
        configurations = await self.get_data("test_configurations") or {}
        return configurations.get(test_id, [])

    async def delete_test_configuration(self, test_id: str, config_id: str) -> bool:
        """
        Delete a stored test configuration.

        Args:
            test_id: The test identifier
            config_id: The configuration identifier

        Returns:
            True if configuration was deleted, False if not found
        """
        configurations = await self.get_data("test_configurations") or {}

        if test_id not in configurations:
            return False

        test_configs = configurations[test_id]
        for i, config in enumerate(test_configs):
            if config.get("config_id") == config_id:
                test_configs.pop(i)
                await self.store_data("test_configurations", configurations)

                self.log_operation(
                    "delete_test_configuration",
                    {"test_id": test_id, "config_id": config_id},
                )
                return True

        return False

    async def cleanup_old_results(self, days_to_keep: int = 90) -> int:
        """
        Clean up old test results to save memory.

        Args:
            days_to_keep: Number of days of results to keep

        Returns:
            Number of results deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        results = await self.get_data("test_results") or []

        # Filter out old results
        kept_results = []
        deleted_count = 0

        for result in results:
            execution_time_str = result.get("execution_time", "")
            try:
                execution_time = datetime.fromisoformat(
                    execution_time_str.replace("Z", "+00:00")
                )
                if execution_time >= cutoff_date:
                    kept_results.append(result)
                else:
                    deleted_count += 1
            except ValueError:
                # Keep results with invalid timestamps
                kept_results.append(result)

        if deleted_count > 0:
            await self.store_data("test_results", kept_results)

        self.log_operation(
            "cleanup_old_results",
            {
                "days_to_keep": days_to_keep,
                "deleted_count": deleted_count,
                "kept_count": len(kept_results),
            },
        )

        return deleted_count
