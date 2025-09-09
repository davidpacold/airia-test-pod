"""
Base service class with common functionality for all services.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..exceptions import ErrorCode, ServiceUnavailableError


class BaseService(ABC):
    """Base class for all service layer implementations."""

    def __init__(self):
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        self.initialized = False
        self.last_health_check = None

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Name of the service for logging and error reporting."""
        pass

    @property
    def health_check_interval_seconds(self) -> int:
        """How often to perform health checks (default: 300 seconds = 5 minutes)."""
        return 300

    async def initialize(self) -> None:
        """
        Initialize the service. Override in subclasses if needed.
        This is called once when the service is first used.
        """
        self.logger.info(f"Initializing {self.service_name} service")
        self.initialized = True

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the service.
        Override in subclasses to implement service-specific checks.
        """
        return {
            "service": self.service_name,
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "initialized": self.initialized,
        }

    async def ensure_initialized(self) -> None:
        """Ensure the service is initialized before use."""
        if not self.initialized:
            await self.initialize()

    async def ensure_healthy(self, force_check: bool = False) -> None:
        """
        Ensure the service is healthy, performing a health check if needed.

        Args:
            force_check: Force a health check even if within interval

        Raises:
            ServiceUnavailableError: If health check fails
        """
        now = datetime.now(timezone.utc)

        # Check if we need to perform a health check
        if (
            force_check
            or self.last_health_check is None
            or (now - self.last_health_check).total_seconds()
            > self.health_check_interval_seconds
        ):

            try:
                health_result = await self.health_check()

                if health_result.get("status") != "healthy":
                    raise ServiceUnavailableError(
                        message=f"{self.service_name} service is unhealthy",
                        error_code=ErrorCode.SERVICE_UNAVAILABLE,
                        service_name=self.service_name,
                        details=health_result,
                        remediation=f"Please check {self.service_name} service configuration and connectivity",
                    )

                self.last_health_check = now
                self.logger.debug(f"{self.service_name} health check passed")

            except Exception as e:
                if isinstance(e, ServiceUnavailableError):
                    raise

                raise ServiceUnavailableError(
                    message=f"{self.service_name} health check failed",
                    error_code=ErrorCode.SERVICE_UNAVAILABLE,
                    service_name=self.service_name,
                    details={"error": str(e)},
                    remediation=f"Please check {self.service_name} service status and connectivity",
                )

    def log_operation(self, operation: str, details: Dict[str, Any] = None) -> None:
        """Log a service operation with structured data."""
        log_data = {
            "service": self.service_name,
            "operation": operation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if details:
            log_data.update(details)

        self.logger.info(f"Service operation", extra=log_data)

    def handle_service_error(
        self, operation: str, error: Exception, **kwargs
    ) -> ServiceUnavailableError:
        """
        Convert various exceptions into ServiceUnavailableError with context.

        Args:
            operation: The operation that failed
            error: The original exception
            **kwargs: Additional context

        Returns:
            ServiceUnavailableError with appropriate context
        """
        error_details = {
            "operation": operation,
            "original_error": str(error),
            "error_type": type(error).__name__,
            **kwargs,
        }

        self.logger.error(
            f"{self.service_name} operation failed: {operation}", extra=error_details
        )

        return ServiceUnavailableError(
            message=f"{self.service_name} operation '{operation}' failed: {str(error)}",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            service_name=self.service_name,
            details=error_details,
            remediation=f"Please check {self.service_name} configuration and try again",
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.ensure_initialized()
        await self.ensure_healthy()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if exc_type is not None:
            self.logger.error(
                f"Exception in {self.service_name} service context: {exc_val}"
            )
        return False
