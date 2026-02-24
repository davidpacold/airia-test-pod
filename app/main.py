import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import uvicorn
from fastapi import (Depends, FastAPI, Form,
                     HTTPException, Request, status)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import (authenticate_user, create_access_token, get_current_user,
                   require_auth)
from .config import get_settings
from .exceptions import (ErrorCode, TestExecutionError,
                         ValidationError, setup_error_handlers)
from .models import TestStatus
from .tests.test_runner import test_runner
from .utils.sanitization import (sanitize_login_credentials,
                                 sanitize_user_input)

# Simple in-memory rate limiter for auth endpoints
_rate_limit_lock = threading.Lock()
_rate_limit_attempts: dict[str, list[float]] = {}
_RATE_LIMIT_MAX = 10  # max attempts
_RATE_LIMIT_WINDOW = 60  # per 60 seconds


def _check_rate_limit(client_ip: str) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    now = time.time()
    with _rate_limit_lock:
        attempts = _rate_limit_attempts.get(client_ip, [])
        # Prune old entries
        attempts = [t for t in attempts if now - t < _RATE_LIMIT_WINDOW]
        if len(attempts) >= _RATE_LIMIT_MAX:
            _rate_limit_attempts[client_ip] = attempts
            return False
        attempts.append(now)
        _rate_limit_attempts[client_ip] = attempts
        return True


app = FastAPI(title="Airia Infrastructure Test Pod", version="1.0.198")

# Setup standardized error handling
setup_error_handlers(app)

# Initialize logger
logger = logging.getLogger(__name__)


# Security headers and cache control middleware
@app.middleware("http")
async def add_security_and_cache_headers(request: Request, call_next):
    response = await call_next(request)

    # Basic security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )

    # Cache control for static files
    if request.url.path.startswith("/static/"):
        # Check if URL has version query parameter (cache-busting)
        if request.url.query and "v=" in request.url.query:
            # Versioned static files - cache aggressively (1 year)
            # Cloudflare and browsers can cache since URL changes when content changes
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            # Non-versioned static files - shorter cache with revalidation
            response.headers["Cache-Control"] = "public, max-age=3600, must-revalidate"

        # Tell Cloudflare to respect query strings for caching
        response.headers["Vary"] = "Accept-Encoding"

    return response


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Health check endpoints


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint for monitoring and load balancers."""
    from .health import health_checker

    return await health_checker.run_all_checks()


@app.get("/health/live")
async def liveness_check():
    """Liveness probe for Kubernetes - checks if application is running."""
    from .health import health_checker

    result = await health_checker.get_liveness_status()

    status_code = 200 if result["alive"] else 503
    return JSONResponse(content=result, status_code=status_code)


@app.get("/health/ready")
async def readiness_check():
    """Readiness probe for Kubernetes - checks if application can serve traffic."""
    from .health import health_checker

    result = await health_checker.get_readiness_status()

    status_code = 200 if result["ready"] else 503
    return JSONResponse(content=result, status_code=status_code)


@app.get("/version")
async def get_version():
    import os
    return {
        "version": get_settings().app_version,
        "image_tag": os.getenv("IMAGE_TAG", "unknown"),
        "build_timestamp": os.getenv("BUILD_TIMESTAMP", "unknown"),
        "deployment_time": os.getenv("BUILD_TIMESTAMP", "unknown")
    }


@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request, current_user: Optional[str] = Depends(get_current_user)
):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request, current_user: Optional[str] = Depends(get_current_user)
):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    settings = get_settings()
    return templates.TemplateResponse(
        "login.html", {"request": request, "title": settings.app_name, "version": settings.app_version}
    )


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not _check_rate_limit(request.client.host):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    # Sanitize login credentials
    try:
        sanitized_username, sanitized_password = sanitize_login_credentials(
            username, password
        )
    except HTTPException as e:
        raise ValidationError(
            message="Invalid username or password format",
            error_code=ErrorCode.CREDENTIALS_INVALID,
            field_name="credentials",
            remediation="Ensure username and password contain only valid characters",
        )

    if not authenticate_user(sanitized_username, sanitized_password):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "title": get_settings().app_name,
                "error": "Invalid username or password",
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )

    settings = get_settings()
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        expires=settings.access_token_expire_minutes * 60,
    )
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: str = Depends(require_auth)):
    if isinstance(current_user, RedirectResponse):
        return current_user
    settings = get_settings()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "title": settings.app_name, "username": current_user, "version": settings.app_version},
    )


@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token")
    return response


@app.post("/token")
async def token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    if not _check_rate_limit(request.client.host):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    # Sanitize credentials from OAuth form
    try:
        sanitized_username, sanitized_password = sanitize_login_credentials(
            form_data.username, form_data.password
        )
    except HTTPException:
        raise ValidationError(
            message="Invalid username or password format",
            error_code=ErrorCode.CREDENTIALS_INVALID,
            field_name="credentials",
            remediation="Ensure username and password contain only valid characters",
        )

    if not authenticate_user(sanitized_username, sanitized_password):
        raise ValidationError(
            message="Incorrect username or password",
            error_code=ErrorCode.CREDENTIALS_INVALID,
            field_name="credentials",
            remediation="Please check your username and password and try again",
        )
    settings = get_settings()
    access_token_expires = timedelta(minutes=get_settings().access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/tests/status")
async def get_test_status(current_user: str = Depends(require_auth)):
    """Get the current status of all tests"""
    return test_runner.get_test_status()


@app.get("/api/tests/summary")
async def get_test_summary(current_user: str = Depends(require_auth)):
    """Get a summary of test results"""
    return test_runner.get_test_summary()


@app.get("/api/readiness-gate")
async def readiness_gate(current_user: str = Depends(require_auth)):
    """Programmatic readiness gate for Airia installation.

    Returns HTTP 200 if all non-skipped tests pass, HTTP 503 if any fail.
    Uses cached results if tests were run within the last 5 minutes.
    """
    import asyncio

    use_cached = False
    with test_runner._lock:
        if test_runner._last_run_time and test_runner.test_results:
            age = (datetime.now(timezone.utc) - test_runner._last_run_time).total_seconds()
            if age < 300:
                use_cached = True

    if not use_cached:
        await asyncio.to_thread(test_runner.run_all_tests)

    summary = test_runner.get_test_summary()
    ready = summary.get("overall_status") == "passed"

    response_data = {
        "ready": ready,
        "tests_passed": summary.get("passed_count", 0),
        "tests_failed": summary.get("failed_count", 0),
        "tests_skipped": summary.get("skipped_count", 0),
        "last_run": summary.get("last_run"),
    }

    status_code = 200 if ready else 503
    return JSONResponse(content=response_data, status_code=status_code)


@app.post("/api/tests/run-all")
async def run_all_tests(current_user: str = Depends(require_auth)):
    """Run all configured tests"""
    import asyncio
    return await asyncio.to_thread(test_runner.run_all_tests)


@app.post("/api/tests/{test_id}")
async def run_single_test(test_id: str, current_user: str = Depends(require_auth)):
    """Run a specific test"""
    import asyncio
    result = await asyncio.to_thread(test_runner.run_test, test_id)
    if not result:
        raise TestExecutionError(
            message=f"Test '{test_id}' not found",
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            test_id=test_id,
            remediation=f"Please check that the test ID '{test_id}' is valid. Available tests can be found at /api/tests",
        )
    return result


@app.get("/api/tests/{test_id}/logs")
async def get_test_logs(test_id: str, current_user: str = Depends(require_auth)):
    """Get logs for a specific test"""
    logs = test_runner.get_test_logs(test_id)
    return {"test_id": test_id, "logs": logs}


@app.get("/api/tests/{test_id}/remediation")
async def get_test_remediation(test_id: str, current_user: str = Depends(require_auth)):
    """Get remediation suggestions for a test"""
    suggestions = test_runner.get_remediation_suggestions(test_id)
    return {"test_id": test_id, "suggestions": suggestions}


@app.delete("/api/tests/results")
async def clear_test_results(current_user: str = Depends(require_auth)):
    """Clear all test results"""
    test_runner.clear_results()
    return {"message": "Test results cleared"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=get_settings().port)

# Export the app for production deployment
application = app
