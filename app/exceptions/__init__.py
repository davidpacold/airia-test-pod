"""
Exception handling package for Airia Infrastructure Test Pod.

This package provides standardized exception classes and error handling
utilities for consistent error management across the application.
"""

from .base import (ConfigurationError, ErrorCode, InfrastructureError,
                   ServiceUnavailableError, TestExecutionError,
                   TestPodException, ValidationError)
from .handlers import setup_error_handlers

__all__ = [
    "TestPodException",
    "ConfigurationError",
    "ServiceUnavailableError",
    "ValidationError",
    "TestExecutionError",
    "InfrastructureError",
    "ErrorCode",
    "setup_error_handlers",
]
