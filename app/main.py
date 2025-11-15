import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

# Test change to verify automated version workflow v1.0.155 -> v1.0.156

import uvicorn
from fastapi import (BackgroundTasks, Depends, FastAPI, File, Form,
                     HTTPException, Request, UploadFile, status)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import (authenticate_user, create_access_token, get_current_user,
                   require_auth)
from .config import get_settings
from .exceptions import (ConfigurationError, ErrorCode,
                         ServiceUnavailableError, TestExecutionError,
                         TestPodException, ValidationError,
                         setup_error_handlers)
from .models import TestResult, TestStatus
from .tests.test_runner import test_runner
from .utils.file_handler import FileUploadHandler
from .utils.sanitization import (InputSanitizer, sanitize_ai_prompt,
                                 sanitize_login_credentials,
                                 sanitize_user_input, validate_file_upload)

app = FastAPI(title="Airia Infrastructure Test Pod", version="1.0.193")

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


# Real-time updates will be implemented in a future version
# For now, the application works perfectly with manual refresh

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
        "version": get_settings().version,
        "image_tag": os.getenv("IMAGE_TAG", "unknown"),
        "build_timestamp": os.getenv("BUILD_TIMESTAMP", "unknown"),
        "deployment_time": os.getenv("BUILD_TIMESTAMP", "unknown")
    }


@app.get("/api/version")
async def get_api_version():
    import os
    return {
        "version": get_settings().version,
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
        "login.html", {"request": request, "title": settings.app_name, "version": settings.version}
    )


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
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

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=get_settings().access_token_expire_minutes * 60,
        expires=get_settings().access_token_expire_minutes * 60,
    )
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: str = Depends(require_auth)):
    if isinstance(current_user, RedirectResponse):
        return current_user
    settings = get_settings()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "title": settings.app_name, "username": current_user, "version": settings.version},
    )


@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token")
    return response


@app.post("/token")
async def token(form_data: OAuth2PasswordRequestForm = Depends()):
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


@app.post("/api/tests/run-all")
async def run_all_tests(current_user: str = Depends(require_auth)):
    """Run all configured tests"""
    return test_runner.run_all_tests()


@app.post("/api/tests/{test_id}")
async def run_single_test(test_id: str, current_user: str = Depends(require_auth)):
    """Run a specific test"""
    result = test_runner.run_test(test_id)
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


# Custom AI Model Testing Endpoints
@app.post("/api/tests/openai/custom")
async def test_openai_custom(
    prompt: str = Form(...),
    system_message: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: str = Depends(require_auth),
):
    """Test OpenAI with custom prompt and optional file"""
    try:
        # Sanitize inputs
        sanitized_prompt = sanitize_ai_prompt(prompt)
        sanitized_system_message = None
        if system_message:
            sanitized_system_message = sanitize_user_input(system_message)

        # Process file upload if provided
        processed_file = await FileUploadHandler.process_ai_model_upload(file)

        # Get OpenAI test instance
        from .tests.openai_test import OpenAITest

        openai_test = OpenAITest()

        if not openai_test.is_configured():
            raise ConfigurationError(
                message="OpenAI test not configured",
                error_code=ErrorCode.CONFIG_REQUIRED,
                service_name="OpenAI",
                remediation="Please configure OpenAI API key and endpoint in your environment variables",
            )

        # Run custom test with sanitized inputs
        result = openai_test.test_with_custom_input(
            custom_prompt=sanitized_prompt,
            custom_file_content=processed_file.content if processed_file else None,
            file_type=processed_file.file_type if processed_file else None,
            system_message=sanitized_system_message,
        )

        return JSONResponse(content=result)

    except (TestPodException, HTTPException):
        # Let our custom exceptions and HTTP exceptions pass through
        raise
    except Exception as e:
        raise TestExecutionError(
            message=f"OpenAI custom test failed: {str(e)}",
            error_code=ErrorCode.TEST_FAILED,
            test_id="openai_custom",
            service_name="OpenAI",
            details={"original_error": str(e), "error_type": type(e).__name__},
            remediation="Please check your OpenAI configuration and try again. If the problem persists, check the service status.",
        )


@app.post("/api/tests/llama/custom")
async def test_llama_custom(
    prompt: str = Form(...),
    system_message: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: str = Depends(require_auth),
):
    """Test Llama with custom prompt and optional file"""
    try:
        # Sanitize inputs
        sanitized_prompt = sanitize_ai_prompt(prompt)
        sanitized_system_message = None
        if system_message:
            sanitized_system_message = sanitize_user_input(system_message)

        # Process file upload if provided
        processed_file = await FileUploadHandler.process_ai_model_upload(file)

        # Get Llama test instance
        from .tests.llama_test import LlamaTest

        llama_test = LlamaTest()

        if not llama_test.is_configured():
            raise ConfigurationError(
                message="Llama test not configured",
                error_code=ErrorCode.CONFIG_REQUIRED,
                service_name="Llama",
                remediation="Please configure Llama API key and endpoint in your environment variables",
            )

        # Run custom test with sanitized inputs
        if hasattr(llama_test, "test_with_custom_input"):
            result = llama_test.test_with_custom_input(
                custom_prompt=sanitized_prompt,
                custom_file_content=processed_file.content if processed_file else None,
                file_type=processed_file.file_type if processed_file else None,
                system_message=sanitized_system_message,
            )
        else:
            raise TestExecutionError(
                message="Custom input not yet implemented for Llama test",
                error_code=ErrorCode.TEST_CONFIGURATION_ERROR,
                test_id="llama_custom",
                service_name="Llama",
                remediation="Please contact support to enable custom input functionality for Llama",
            )

        return JSONResponse(content=result)

    except (TestPodException, HTTPException):
        # Let our custom exceptions and HTTP exceptions pass through
        raise
    except Exception as e:
        raise TestExecutionError(
            message=f"Llama custom test failed: {str(e)}",
            error_code=ErrorCode.TEST_FAILED,
            test_id="llama_custom",
            service_name="Llama",
            details={"original_error": str(e), "error_type": type(e).__name__},
            remediation="Please check your Llama configuration and try again. If the problem persists, check the service status.",
        )


@app.post("/api/tests/docintel/custom")
async def test_docintel_custom(
    prompt: Optional[str] = Form(None),
    file: UploadFile = File(...),  # File is required for Document Intelligence
    current_user: str = Depends(require_auth),
):
    """Test Document Intelligence with custom file upload"""
    try:
        # Sanitize inputs
        sanitized_prompt = None
        if prompt:
            sanitized_prompt = sanitize_ai_prompt(prompt)

        # Process file upload (Document Intelligence requires a file)
        processed_file = await FileUploadHandler.process_document_intel_upload(file)

        # Get Document Intelligence test instance
        from .tests.document_intelligence_test import DocumentIntelligenceTest

        docintel_test = DocumentIntelligenceTest()

        if not docintel_test.is_configured():
            raise ConfigurationError(
                message="Document Intelligence test not configured",
                error_code=ErrorCode.CONFIG_REQUIRED,
                service_name="DocumentIntelligence",
                remediation="Please configure Azure Document Intelligence API key and endpoint in your environment variables",
            )

        # Read original file content for Document Intelligence API
        await file.seek(0)  # Reset file pointer to beginning
        content = await file.read()

        # Run custom test with sanitized inputs
        result = docintel_test.test_with_custom_file(
            file_content=content,
            file_type=processed_file.extension,
            custom_prompt=sanitized_prompt,
        )

        return JSONResponse(content=result)

    except (TestPodException, HTTPException):
        # Let our custom exceptions and HTTP exceptions pass through
        raise
    except Exception as e:
        raise TestExecutionError(
            message=f"Document Intelligence custom test failed: {str(e)}",
            error_code=ErrorCode.TEST_FAILED,
            test_id="docintel_custom",
            service_name="DocumentIntelligence",
            details={"original_error": str(e), "error_type": type(e).__name__},
            remediation="Please check your Document Intelligence configuration and try again. If the problem persists, check the service status.",
        )


@app.post("/api/tests/embeddings/custom")
async def test_embeddings_custom(
    text: str = Form(...),
    batch_texts: Optional[str] = Form(None),  # Comma-separated additional texts
    current_user: str = Depends(require_auth),
):
    """Test embedding generation with custom text input"""
    try:
        # Sanitize inputs
        sanitized_text = sanitize_user_input(text)
        sanitized_batch_texts = InputSanitizer.sanitize_batch_texts(batch_texts)

        # Get Embedding test instance
        from .tests.embedding_test import EmbeddingTest

        embedding_test = EmbeddingTest()

        if not embedding_test.is_configured():
            raise ConfigurationError(
                message="Embedding test not configured",
                error_code=ErrorCode.CONFIG_REQUIRED,
                service_name="Embeddings",
                remediation="Please configure embedding API key and endpoint in your environment variables",
            )

        # Use sanitized batch texts
        batch_text_list = sanitized_batch_texts if sanitized_batch_texts else None

        # Run custom test with sanitized inputs (no file support)
        result = embedding_test.test_with_custom_input(
            custom_text=sanitized_text,
            custom_file_content=None,
            file_type=None,
            batch_texts=batch_text_list,
        )

        return JSONResponse(content=result)

    except (TestPodException, HTTPException):
        # Let our custom exceptions and HTTP exceptions pass through
        raise
    except Exception as e:
        raise TestExecutionError(
            message=f"Embedding custom test failed: {str(e)}",
            error_code=ErrorCode.TEST_FAILED,
            test_id="embedding_custom",
            service_name="Embeddings",
            details={"original_error": str(e), "error_type": type(e).__name__},
            remediation="Please check your embedding configuration and try again. If the problem persists, check the service status.",
        )


# Legacy endpoint for backward compatibility
@app.post("/api/tests/postgres")
async def run_postgres_test(current_user: str = Depends(require_auth)):
    """Run PostgreSQL connectivity test - legacy endpoint"""
    result = test_runner.run_test("postgresql")
    if not result:
        raise HTTPException(status_code=404, detail="PostgreSQL test not found")
    return result.get("result", result)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=get_settings().port)

# Export the app for production deployment
application = app
