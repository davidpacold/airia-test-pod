"""
Connection test mixin for standardizing connection testing patterns.

This mixin provides common functionality for testing connections to various
services with retry logic, timeout handling, and consistent error reporting.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, Optional, Union

from ..exceptions import ErrorCode, ServiceUnavailableError, TestExecutionError


class ConnectionTestMixin:
    """Standardized connection testing patterns for all test modules."""

    def test_connection_with_retry(
        self,
        connect_func: Callable,
        retries: int = 3,
        delay_factor: float = 2.0,
        timeout_seconds: int = 30,
        service_name: str = None,
    ) -> Dict[str, Any]:
        """
        Test connection with exponential backoff retry logic.

        Args:
            connect_func: Function to call for connection testing
            retries: Number of retry attempts (default: 3)
            delay_factor: Exponential backoff multiplier (default: 2.0)
            timeout_seconds: Timeout for each connection attempt
            service_name: Name of the service being tested

        Returns:
            Dictionary with connection test results

        Raises:
            ServiceUnavailableError: If all connection attempts fail
        """
        last_error = None

        for attempt in range(retries):
            try:
                start_time = time.time()
                result = connect_func()
                duration = time.time() - start_time

                return {
                    "success": True,
                    "duration": round(duration, 3),
                    "attempt": attempt + 1,
                    "details": (
                        result if isinstance(result, dict) else {"status": "connected"}
                    ),
                }

            except Exception as e:
                last_error = e
                duration = time.time() - start_time

                # Don't retry on the last attempt
                if attempt == retries - 1:
                    break

                # Calculate delay with exponential backoff
                delay = delay_factor**attempt
                time.sleep(delay)

        # All attempts failed
        raise ServiceUnavailableError(
            message=f"Connection failed after {retries} attempts",
            error_code=ErrorCode.SERVICE_CONNECTION_FAILED,
            service_name=service_name or "Unknown",
            details={
                "attempts": retries,
                "last_error": str(last_error),
                "total_duration": round(time.time() - start_time, 3),
            },
            remediation=f"Please check that {service_name or 'the service'} is running and accessible",
        )

    async def test_async_connection_with_retry(
        self,
        connect_func: Callable,
        retries: int = 3,
        delay_factor: float = 2.0,
        timeout_seconds: int = 30,
        service_name: str = None,
    ) -> Dict[str, Any]:
        """
        Async version of test_connection_with_retry.

        Args:
            connect_func: Async function to call for connection testing
            retries: Number of retry attempts (default: 3)
            delay_factor: Exponential backoff multiplier (default: 2.0)
            timeout_seconds: Timeout for each connection attempt
            service_name: Name of the service being tested

        Returns:
            Dictionary with connection test results

        Raises:
            ServiceUnavailableError: If all connection attempts fail
        """
        last_error = None
        start_time = time.time()

        for attempt in range(retries):
            try:
                attempt_start = time.time()

                # Use asyncio timeout for each attempt
                result = await asyncio.wait_for(connect_func(), timeout=timeout_seconds)

                duration = time.time() - attempt_start

                return {
                    "success": True,
                    "duration": round(duration, 3),
                    "attempt": attempt + 1,
                    "details": (
                        result if isinstance(result, dict) else {"status": "connected"}
                    ),
                }

            except asyncio.TimeoutError:
                last_error = "Connection timeout"
                if attempt == retries - 1:
                    break

            except Exception as e:
                last_error = e
                if attempt == retries - 1:
                    break

            # Calculate delay with exponential backoff
            if attempt < retries - 1:
                delay = delay_factor**attempt
                await asyncio.sleep(delay)

        # All attempts failed
        raise ServiceUnavailableError(
            message=f"Async connection failed after {retries} attempts",
            error_code=ErrorCode.SERVICE_CONNECTION_FAILED,
            service_name=service_name or "Unknown",
            details={
                "attempts": retries,
                "last_error": str(last_error),
                "total_duration": round(time.time() - start_time, 3),
            },
            remediation=f"Please check that {service_name or 'the service'} is running and accessible",
        )

    def validate_connection_config(
        self, config: Dict[str, Any], required_fields: list, service_name: str = None
    ) -> None:
        """
        Validate that required configuration fields are present.

        Args:
            config: Configuration dictionary to validate
            required_fields: List of required field names
            service_name: Name of the service for error messages

        Raises:
            ConfigurationError: If required fields are missing
        """
        missing_fields = [field for field in required_fields if not config.get(field)]

        if missing_fields:
            from ..exceptions import ConfigurationError

            raise ConfigurationError(
                message=f"Missing required configuration for {service_name or 'service'}",
                error_code=ErrorCode.CONFIG_REQUIRED,
                service_name=service_name,
                details={"missing_fields": missing_fields},
                remediation=f"Please set the following environment variables: {', '.join(missing_fields)}",
            )

    def format_connection_result(
        self,
        success: bool,
        details: Dict[str, Any] = None,
        error: Exception = None,
        service_name: str = None,
        duration: float = None,
    ) -> Dict[str, Any]:
        """
        Format connection test results in a standardized format.

        Args:
            success: Whether the connection test succeeded
            details: Additional details about the connection
            error: Exception that occurred (if any)
            service_name: Name of the service tested
            duration: Time taken for the test

        Returns:
            Formatted result dictionary
        """
        result = {
            "success": success,
            "service": service_name or "Unknown",
            "timestamp": time.time(),
        }

        if duration is not None:
            result["duration"] = round(duration, 3)

        if success:
            result["status"] = "connected"
            if details:
                result["details"] = details
        else:
            result["status"] = "failed"
            result["error"] = str(error) if error else "Connection failed"
            if hasattr(error, "error_code"):
                result["error_code"] = error.error_code.value

        return result

    @asynccontextmanager
    async def connection_context(
        self,
        connect_func: Callable,
        disconnect_func: Callable = None,
        service_name: str = None,
    ):
        """
        Context manager for managing connections with automatic cleanup.

        Args:
            connect_func: Function to establish connection
            disconnect_func: Function to close connection (optional)
            service_name: Name of service for error reporting

        Yields:
            Connection object

        Raises:
            ServiceUnavailableError: If connection fails
        """
        connection = None
        try:
            connection = await connect_func()
            yield connection
        except Exception as e:
            raise ServiceUnavailableError(
                message=f"Failed to establish connection to {service_name or 'service'}",
                error_code=ErrorCode.SERVICE_CONNECTION_FAILED,
                service_name=service_name,
                details={"error": str(e)},
                remediation=f"Please check {service_name or 'service'} connectivity and credentials",
            )
        finally:
            if connection and disconnect_func:
                try:
                    await disconnect_func(connection)
                except Exception:
                    # Log but don't raise cleanup errors
                    pass
