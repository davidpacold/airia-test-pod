"""
Base exception classes for the Airia Infrastructure Test Pod.

This module provides a standardized exception hierarchy with enhanced
error information including details, remediation suggestions, and
structured error codes.
"""

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(Enum):
    """Standardized error codes for different types of failures."""

    # Configuration errors (1xxx)
    CONFIG_MISSING = "CONFIG_1001"
    CONFIG_INVALID = "CONFIG_1002"
    CONFIG_REQUIRED = "CONFIG_1003"

    # Service connectivity errors (2xxx)
    SERVICE_UNAVAILABLE = "SERVICE_2001"
    SERVICE_TIMEOUT = "SERVICE_2002"
    SERVICE_AUTH_FAILED = "SERVICE_2003"
    SERVICE_CONNECTION_FAILED = "SERVICE_2004"

    # Validation errors (3xxx)
    VALIDATION_FAILED = "VALIDATION_3001"
    INPUT_INVALID = "VALIDATION_3002"
    FILE_INVALID = "VALIDATION_3003"
    CREDENTIALS_INVALID = "VALIDATION_3004"

    # Test execution errors (4xxx)
    TEST_FAILED = "TEST_4001"
    TEST_TIMEOUT = "TEST_4002"
    TEST_DEPENDENCY_FAILED = "TEST_4003"
    TEST_CONFIGURATION_ERROR = "TEST_4004"
    TEST_NOT_FOUND = "TEST_4005"
    TEST_ALREADY_RUNNING = "TEST_4006"
    TEST_EXECUTION_FAILED = "TEST_4007"

    # Infrastructure errors (5xxx)
    RESOURCE_NOT_FOUND = "INFRA_5001"
    PERMISSION_DENIED = "INFRA_5002"
    QUOTA_EXCEEDED = "INFRA_5003"
    NETWORK_ERROR = "INFRA_5004"


class TestPodException(Exception):
    """
    Base exception for all Test Pod errors.

    Provides structured error information including error codes,
    details, and remediation suggestions to help users resolve issues.
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = None,
        details: Dict[str, Any] = None,
        remediation: str = None,
        service_name: str = None,
    ):
        """
        Initialize a Test Pod exception.

        Args:
            message: Human-readable error message
            error_code: Standardized error code for the error type
            details: Additional structured information about the error
            remediation: Suggested steps to resolve the issue
            service_name: Name of the service that caused the error
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.remediation = remediation
        self.service_name = service_name
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format for API responses."""
        result = {
            "error": self.message,
            "error_code": self.error_code.value if self.error_code else None,
            "details": self.details,
        }

        if self.remediation:
            result["remediation"] = self.remediation

        if self.service_name:
            result["service"] = self.service_name

        return result


class ConfigurationError(TestPodException):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.CONFIG_INVALID,
        config_key: str = None,
        expected_value: str = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key
        if expected_value:
            details["expected_value"] = expected_value

        super().__init__(
            message=message, error_code=error_code, details=details, **kwargs
        )


class ServiceUnavailableError(TestPodException):
    """Service connectivity errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.SERVICE_UNAVAILABLE,
        service_name: str = None,
        endpoint: str = None,
        status_code: int = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if endpoint:
            details["endpoint"] = endpoint
        if status_code:
            details["status_code"] = status_code

        super().__init__(
            message=message,
            error_code=error_code,
            service_name=service_name,
            details=details,
            **kwargs
        )


class ValidationError(TestPodException):
    """Input validation errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.VALIDATION_FAILED,
        field_name: str = None,
        provided_value: Any = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if field_name:
            details["field"] = field_name
        if provided_value is not None:
            details["provided_value"] = str(provided_value)

        super().__init__(
            message=message, error_code=error_code, details=details, **kwargs
        )


class TestExecutionError(TestPodException):
    """Test execution related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.TEST_FAILED,
        test_id: str = None,
        duration: float = None,
        details: Dict[str, Any] = None,
        remediation: str = None,
        service_name: str = None,
    ):
        details = details or {}
        if test_id:
            details["test_id"] = test_id
        if duration is not None:
            details["duration_seconds"] = duration

        super().__init__(
            message=message, 
            error_code=error_code, 
            details=details,
            remediation=remediation,
            service_name=service_name
        )


class InfrastructureError(TestPodException):
    """Infrastructure and resource related errors."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.RESOURCE_NOT_FOUND,
        resource_type: str = None,
        resource_name: str = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if resource_type:
            details["resource_type"] = resource_type
        if resource_name:
            details["resource_name"] = resource_name

        super().__init__(
            message=message, error_code=error_code, details=details, **kwargs
        )
