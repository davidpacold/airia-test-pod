"""
Comprehensive health check system for application monitoring.

This module provides detailed health checks for all application components
including dependencies, services, and system resources.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil

from .config import get_settings
from .exceptions import ServiceUnavailableError


class HealthStatus(Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """Individual health check definition."""

    def __init__(
        self,
        name: str,
        check_function: Callable,
        critical: bool = False,
        timeout: int = 5,
        description: str = "",
    ):
        self.name = name
        self.check_function = check_function
        self.critical = critical
        self.timeout = timeout
        self.description = description
        self.last_run = None
        self.last_result = None
        self.consecutive_failures = 0


class HealthChecker:
    """Comprehensive health checking system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
        self.checks: Dict[str, HealthCheck] = {}
        self.startup_time = datetime.now(timezone.utc)
        self._register_default_checks()

    def register_check(
        self,
        name: str,
        check_function: Callable,
        critical: bool = False,
        timeout: int = 5,
        description: str = "",
    ) -> None:
        """Register a new health check."""
        self.checks[name] = HealthCheck(
            name=name,
            check_function=check_function,
            critical=critical,
            timeout=timeout,
            description=description,
        )
        self.logger.info(f"Registered health check: {name}")

    def _register_default_checks(self) -> None:
        """Register default system health checks."""
        self.register_check(
            "application_startup",
            self._check_application_startup,
            critical=True,
            description="Verify application started successfully",
        )

        self.register_check(
            "configuration",
            self._check_configuration,
            critical=True,
            description="Validate critical configuration settings",
        )

        self.register_check(
            "memory_usage",
            self._check_memory_usage,
            critical=False,
            description="Monitor memory consumption",
        )

        self.register_check(
            "disk_space",
            self._check_disk_space,
            critical=False,
            description="Monitor available disk space",
        )

        self.register_check(
            "gpu_availability",
            self._check_gpu_availability,
            critical=False,
            timeout=10,
            description="Check GPU availability and status if available",
        )

        self.register_check(
            "database_connectivity",
            self._check_database_connectivity,
            critical=False,
            timeout=10,
            description="Test database connection if configured",
        )

        self.register_check(
            "external_dependencies",
            self._check_external_dependencies,
            critical=False,
            timeout=15,
            description="Validate external service connectivity",
        )

    async def run_check(self, check_name: str) -> Dict[str, Any]:
        """Run a specific health check."""
        if check_name not in self.checks:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": f"Unknown health check: {check_name}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        check = self.checks[check_name]
        start_time = time.time()

        try:
            # Run check with timeout
            result = await asyncio.wait_for(
                check.check_function(), timeout=check.timeout
            )

            duration = time.time() - start_time

            # Ensure result has required fields
            if not isinstance(result, dict):
                result = {"status": HealthStatus.HEALTHY.value}

            if "status" not in result:
                result["status"] = HealthStatus.HEALTHY.value

            result.update(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "duration_seconds": round(duration, 3),
                    "check_name": check_name,
                    "description": check.description,
                    "critical": check.critical,
                }
            )

            # Track consecutive failures
            if result["status"] == HealthStatus.HEALTHY.value:
                check.consecutive_failures = 0
            else:
                check.consecutive_failures += 1

            check.last_run = datetime.now(timezone.utc)
            check.last_result = result

            return result

        except asyncio.TimeoutError:
            check.consecutive_failures += 1
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "error": f"Health check timed out after {check.timeout}s",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": check.timeout,
                "check_name": check_name,
                "description": check.description,
                "critical": check.critical,
                "consecutive_failures": check.consecutive_failures,
            }

        except Exception as e:
            check.consecutive_failures += 1
            self.logger.error(f"Health check {check_name} failed: {str(e)}")
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": time.time() - start_time,
                "check_name": check_name,
                "description": check.description,
                "critical": check.critical,
                "consecutive_failures": check.consecutive_failures,
            }

    async def run_all_checks(self, include_non_critical: bool = True) -> Dict[str, Any]:
        """Run all registered health checks."""
        start_time = time.time()
        results = {}

        # Determine which checks to run
        checks_to_run = []
        for name, check in self.checks.items():
            if include_non_critical or check.critical:
                checks_to_run.append(name)

        # Run checks concurrently
        tasks = [self.run_check(check_name) for check_name in checks_to_run]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        critical_failures = 0
        non_critical_failures = 0

        for i, result in enumerate(check_results):
            check_name = checks_to_run[i]

            if isinstance(result, Exception):
                result = {
                    "status": HealthStatus.UNHEALTHY.value,
                    "error": str(result),
                    "error_type": type(result).__name__,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "check_name": check_name,
                    "critical": self.checks[check_name].critical,
                }

            results[check_name] = result

            # Count failures (degraded is not a failure, just a warning)
            if result["status"] not in (HealthStatus.HEALTHY.value, HealthStatus.DEGRADED.value):
                if result.get("critical", False):
                    critical_failures += 1
                else:
                    non_critical_failures += 1

        # Determine overall status
        if critical_failures > 0:
            overall_status = HealthStatus.UNHEALTHY.value
        elif non_critical_failures > 0:
            overall_status = HealthStatus.DEGRADED.value
        else:
            overall_status = HealthStatus.HEALTHY.value

        total_duration = time.time() - start_time

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": (
                datetime.now(timezone.utc) - self.startup_time
            ).total_seconds(),
            "checks_run": len(checks_to_run),
            "critical_failures": critical_failures,
            "non_critical_failures": non_critical_failures,
            "total_duration_seconds": round(total_duration, 3),
            "checks": results,
            "version": getattr(self.settings, "version", "unknown"),
            "application": getattr(self.settings, "app_name", "Test Application"),
        }

    async def get_readiness_status(self) -> Dict[str, Any]:
        """Get readiness status (critical checks only)."""
        result = await self.run_all_checks(include_non_critical=False)
        return {
            "ready": result["status"] in (HealthStatus.HEALTHY.value, HealthStatus.DEGRADED.value),
            "status": result["status"],
            "timestamp": result["timestamp"],
            "critical_checks": {
                name: check
                for name, check in result["checks"].items()
                if check.get("critical", False)
            },
        }

    async def get_liveness_status(self) -> Dict[str, Any]:
        """Get liveness status (basic application health)."""
        try:
            # Basic liveness check - just verify app is responding
            startup_result = await self.run_check("application_startup")

            return {
                "alive": startup_result["status"] == HealthStatus.HEALTHY.value,
                "status": startup_result["status"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": (
                    datetime.now(timezone.utc) - self.startup_time
                ).total_seconds(),
                "version": getattr(self.settings, "version", "unknown"),
            }
        except Exception as e:
            return {
                "alive": False,
                "status": HealthStatus.UNHEALTHY.value,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    # Default health check implementations

    async def _check_application_startup(self) -> Dict[str, Any]:
        """Check that application has started successfully."""
        uptime = (datetime.now(timezone.utc) - self.startup_time).total_seconds()

        # Application should be considered healthy after startup
        if uptime < 30:  # Grace period for startup
            return {
                "status": HealthStatus.HEALTHY.value,
                "uptime_seconds": uptime,
                "startup_grace_period": True,
            }

        return {
            "status": HealthStatus.HEALTHY.value,
            "uptime_seconds": uptime,
            "startup_time": self.startup_time.isoformat(),
        }

    async def _check_configuration(self) -> Dict[str, Any]:
        """Validate critical configuration settings."""
        issues = []

        # Check critical settings
        secret_key = getattr(self.settings, "secret_key", "")
        if not secret_key or len(secret_key) < 16:
            issues.append("secret_key_too_short")

        if "change-in-production" in secret_key:
            issues.append("default_secret_key_in_use")

        auth_username = getattr(self.settings, "auth_username", "")
        auth_password = getattr(self.settings, "auth_password", "")
        if auth_username == "admin" and auth_password == "changeme":
            issues.append("default_credentials_in_use")

        if issues:
            return {
                "status": HealthStatus.DEGRADED.value,
                "issues": issues,
                "warning": "Configuration has security concerns",
            }

        return {"status": HealthStatus.HEALTHY.value, "configuration_validated": True}

    async def _check_memory_usage(self) -> Dict[str, Any]:
        """Monitor memory usage."""
        try:
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info()

            memory_usage_percent = memory.percent
            process_memory_mb = process_memory.rss / 1024 / 1024

            status = HealthStatus.HEALTHY.value
            if memory_usage_percent > 90:
                status = HealthStatus.UNHEALTHY.value
            elif memory_usage_percent > 80:
                status = HealthStatus.DEGRADED.value

            return {
                "status": status,
                "system_memory_percent": memory_usage_percent,
                "process_memory_mb": round(process_memory_mb, 2),
                "available_memory_mb": round(memory.available / 1024 / 1024, 2),
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": f"Could not check memory usage: {str(e)}",
            }

    async def _check_disk_space(self) -> Dict[str, Any]:
        """Monitor disk space."""
        try:
            disk_usage = psutil.disk_usage("/")

            used_percent = (disk_usage.used / disk_usage.total) * 100
            available_gb = disk_usage.free / 1024 / 1024 / 1024

            status = HealthStatus.HEALTHY.value
            if used_percent > 95:
                status = HealthStatus.UNHEALTHY.value
            elif used_percent > 85:
                status = HealthStatus.DEGRADED.value

            return {
                "status": status,
                "disk_used_percent": round(used_percent, 2),
                "available_gb": round(available_gb, 2),
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": f"Could not check disk space: {str(e)}",
            }

    async def _check_gpu_availability(self) -> Dict[str, Any]:
        """Check GPU availability and status."""
        try:
            import subprocess

            # Check if nvidia-smi is available
            try:
                result = subprocess.run(
                    ["which", "nvidia-smi"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    return {
                        "status": HealthStatus.HEALTHY.value,
                        "message": "No GPU detected (nvidia-smi not available)",
                        "gpu_available": False,
                        "skipped": True,
                    }
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "message": "No GPU detected",
                    "gpu_available": False,
                    "skipped": True,
                }

            # Get GPU information
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=count,name,memory.total,memory.used,temperature.gpu,utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return {
                    "status": HealthStatus.DEGRADED.value,
                    "message": "GPU detected but query failed",
                    "gpu_available": True,
                    "error": result.stderr.strip(),
                }

            # Parse GPU information
            lines = result.stdout.strip().split("\n")
            gpu_count = len(lines)

            if gpu_count == 0:
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "message": "No GPUs detected",
                    "gpu_available": False,
                    "skipped": True,
                }

            # Get info for first GPU (if multiple, show aggregate)
            gpus = []
            max_temp = 0
            total_memory_used_percent = 0

            for line in lines:
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    memory_total = float(parts[2]) if parts[2] != "[N/A]" else 0
                    memory_used = float(parts[3]) if parts[3] != "[N/A]" else 0
                    temp = int(parts[4]) if parts[4] != "[N/A]" else 0
                    util = parts[5] if parts[5] != "[N/A]" else "0"

                    memory_used_percent = (
                        (memory_used / memory_total * 100) if memory_total > 0 else 0
                    )
                    total_memory_used_percent += memory_used_percent
                    max_temp = max(max_temp, temp)

                    gpus.append(
                        {
                            "name": parts[1],
                            "memory_total_mb": round(memory_total, 2),
                            "memory_used_mb": round(memory_used, 2),
                            "memory_used_percent": round(memory_used_percent, 2),
                            "temperature_celsius": temp,
                            "utilization_percent": util,
                        }
                    )

            avg_memory_used_percent = (
                total_memory_used_percent / gpu_count if gpu_count > 0 else 0
            )

            # Determine health status based on temperature and memory
            status = HealthStatus.HEALTHY.value
            warnings = []

            if max_temp > 85:
                status = HealthStatus.DEGRADED.value
                warnings.append(f"High GPU temperature: {max_temp}°C")
            elif max_temp > 80:
                warnings.append(f"Elevated GPU temperature: {max_temp}°C")

            if avg_memory_used_percent > 95:
                status = HealthStatus.DEGRADED.value
                warnings.append(
                    f"High GPU memory usage: {round(avg_memory_used_percent, 1)}%"
                )

            return {
                "status": status,
                "message": f"{gpu_count} GPU(s) available"
                + (f" - {', '.join(warnings)}" if warnings else ""),
                "gpu_available": True,
                "gpu_count": gpu_count,
                "gpus": gpus,
                "max_temperature_celsius": max_temp,
                "warnings": warnings if warnings else None,
            }

        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": f"Could not check GPU availability: {str(e)}",
                "gpu_available": False,
            }

    async def _check_database_connectivity(self) -> Dict[str, Any]:
        """Test database connectivity if configured."""
        try:
            # Check if database is configured
            postgres_host = getattr(self.settings, "postgres_host", "localhost")
            if not postgres_host or postgres_host == "localhost":
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "message": "Database not configured for health checking",
                    "skipped": True,
                }

            # Import here to avoid circular dependencies
            try:
                from .tests.postgres_test_v2 import PostgreSQLTestV2
            except ImportError:
                return {
                    "status": HealthStatus.UNKNOWN.value,
                    "database_connected": False,
                    "error": "PostgreSQLTestV2 not available",
                    "skipped": True,
                }

            postgres_test = PostgreSQLTestV2()
            if not postgres_test.is_configured():
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "message": "PostgreSQL not configured",
                    "skipped": True,
                }

            # Run a quick connection test
            try:
                try:
                    import psycopg2
                except ImportError:
                    return {
                        "status": HealthStatus.UNKNOWN.value,
                        "database_connected": False,
                        "error": "psycopg2 not available",
                        "skipped": True,
                    }

                conn_params = postgres_test.get_connection_params()
                conn_params["connect_timeout"] = 5  # Quick timeout for health check

                with psycopg2.connect(**conn_params) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()

                return {
                    "status": HealthStatus.HEALTHY.value,
                    "database_connected": True,
                    "host": postgres_host,
                }

            except Exception as db_error:
                return {
                    "status": HealthStatus.DEGRADED.value,
                    "database_connected": False,
                    "error": str(db_error),
                    "host": postgres_host,
                }

        except Exception as e:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "error": f"Database health check failed: {str(e)}",
            }

    async def _check_external_dependencies(self) -> Dict[str, Any]:
        """Check external service dependencies."""
        dependencies = {}
        overall_status = HealthStatus.HEALTHY.value

        # Check blob storage if configured
        blob_account_name = getattr(self.settings, "blob_account_name", "")
        if blob_account_name:
            try:
                dependencies["azure_blob"] = {
                    "configured": True,
                    "account": blob_account_name,
                    "status": "configured_not_tested",
                }
            except Exception:
                dependencies["azure_blob"] = {
                    "configured": True,
                    "status": "configuration_error",
                }
                overall_status = HealthStatus.DEGRADED.value
        else:
            dependencies["azure_blob"] = {
                "configured": False,
                "status": "not_configured",
            }

        # Check Cassandra if configured
        cassandra_hosts = getattr(self.settings, "cassandra_hosts", "")
        if cassandra_hosts:
            dependencies["cassandra"] = {
                "configured": True,
                "hosts": cassandra_hosts,
                "status": "configured_not_tested",
            }
        else:
            dependencies["cassandra"] = {
                "configured": False,
                "status": "not_configured",
            }

        return {
            "status": overall_status,
            "dependencies": dependencies,
            "total_dependencies": len(dependencies),
            "configured_dependencies": sum(
                1 for dep in dependencies.values() if dep["configured"]
            ),
        }


# Global health checker instance
health_checker = HealthChecker()
