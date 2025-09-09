"""
Error handlers for FastAPI application.

This module provides centralized error handling for all Test Pod exceptions
and standard HTTP errors, ensuring consistent error response format.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .base import TestPodException, ErrorCode
import logging

logger = logging.getLogger(__name__)


async def test_pod_exception_handler(
    request: Request, exc: TestPodException
) -> JSONResponse:
    """
    Handle Test Pod custom exceptions.

    Args:
        request: The FastAPI request object
        exc: The Test Pod exception that was raised

    Returns:
        JSONResponse with structured error information
    """
    # Log the error for debugging
    logger.error(
        f"TestPodException: {exc.message}",
        extra={
            "error_code": exc.error_code.value if exc.error_code else None,
            "service": exc.service_name,
            "details": exc.details,
            "path": str(request.url),
            "method": request.method,
        },
    )

    # Determine HTTP status code based on error type
    status_code = _get_http_status_for_error_code(exc.error_code)

    return JSONResponse(status_code=status_code, content=exc.to_dict())


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle standard FastAPI HTTPExceptions.

    Args:
        request: The FastAPI request object
        exc: The HTTP exception that was raised

    Returns:
        JSONResponse with standardized error format
    """
    logger.warning(
        f"HTTPException: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": str(request.url),
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "details": {},
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: The FastAPI request object
        exc: The validation exception that was raised

    Returns:
        JSONResponse with validation error details
    """
    logger.warning(
        f"ValidationError: {len(exc.errors())} validation errors",
        extra={
            "errors": exc.errors(),
            "path": str(request.url),
            "method": request.method,
        },
    )

    # Format validation errors for user-friendly response
    error_details = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        error_details.append(
            {
                "field": field_path,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Request validation failed",
            "error_code": ErrorCode.VALIDATION_FAILED.value,
            "details": {"validation_errors": error_details},
            "remediation": "Please check the request format and ensure all required fields are provided with valid values",
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Args:
        request: The FastAPI request object
        exc: The unexpected exception that was raised

    Returns:
        JSONResponse with generic error message
    """
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "path": str(request.url),
            "method": request.method,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "An unexpected error occurred",
            "error_code": "INTERNAL_ERROR",
            "details": {},
            "remediation": "Please try again later. If the problem persists, contact support.",
        },
    )


def _get_http_status_for_error_code(error_code: ErrorCode) -> int:
    """
    Map error codes to appropriate HTTP status codes.

    Args:
        error_code: The Test Pod error code

    Returns:
        HTTP status code integer
    """
    if not error_code:
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    # Configuration errors -> 400 Bad Request
    if error_code.value.startswith("CONFIG_"):
        return status.HTTP_400_BAD_REQUEST

    # Service errors -> various status codes
    if error_code.value.startswith("SERVICE_"):
        if error_code == ErrorCode.SERVICE_AUTH_FAILED:
            return status.HTTP_401_UNAUTHORIZED
        elif error_code == ErrorCode.SERVICE_TIMEOUT:
            return status.HTTP_408_REQUEST_TIMEOUT
        else:
            return status.HTTP_503_SERVICE_UNAVAILABLE

    # Validation errors -> 400 Bad Request or 422 Unprocessable Entity
    if error_code.value.startswith("VALIDATION_"):
        if error_code == ErrorCode.CREDENTIALS_INVALID:
            return status.HTTP_401_UNAUTHORIZED
        else:
            return status.HTTP_400_BAD_REQUEST

    # Test errors -> 424 Failed Dependency
    if error_code.value.startswith("TEST_"):
        return status.HTTP_424_FAILED_DEPENDENCY

    # Infrastructure errors -> various status codes
    if error_code.value.startswith("INFRA_"):
        if error_code == ErrorCode.RESOURCE_NOT_FOUND:
            return status.HTTP_404_NOT_FOUND
        elif error_code == ErrorCode.PERMISSION_DENIED:
            return status.HTTP_403_FORBIDDEN
        elif error_code == ErrorCode.QUOTA_EXCEEDED:
            return status.HTTP_429_TOO_MANY_REQUESTS
        else:
            return status.HTTP_503_SERVICE_UNAVAILABLE

    # Default to 500 for unknown error codes
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def setup_error_handlers(app):
    """
    Register all error handlers with the FastAPI application.

    Args:
        app: The FastAPI application instance
    """
    app.add_exception_handler(TestPodException, test_pod_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
