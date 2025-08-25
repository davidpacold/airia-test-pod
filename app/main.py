from fastapi import FastAPI, Request, Depends, Form, status, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
import uvicorn
from datetime import datetime, timedelta
import os
from typing import Optional

from .auth import (
    authenticate_user, create_access_token, get_current_user, require_auth
)
from .config import get_settings
from .models import TestResult, TestStatus
from .tests.test_runner import test_runner
from fastapi import HTTPException

settings = get_settings()
app = FastAPI(title="Airia Infrastructure Test Pod", version="1.0.34")

# Real-time updates will be implemented in a future version
# For now, the application works perfectly with manual refresh

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Health check endpoint

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": get_settings().version
    }

@app.get("/version")
async def get_version():
    return {"version": get_settings().version}

@app.get("/api/version")
async def get_api_version():
    return {"version": get_settings().version}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: Optional[str] = Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, current_user: Optional[str] = Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "title": settings.app_name
    })

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not authenticate_user(username, password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "title": settings.app_name,
            "error": "Invalid username or password"
        }, status_code=status.HTTP_401_UNAUTHORIZED)
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        max_age=settings.access_token_expire_minutes * 60,
        expires=settings.access_token_expire_minutes * 60
    )
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: str = Depends(require_auth)):
    if isinstance(current_user, RedirectResponse):
        return current_user
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": settings.app_name,
        "username": current_user
    })

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token")
    return response

@app.post("/token")
async def token(form_data: OAuth2PasswordRequestForm = Depends()):
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
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
        raise HTTPException(status_code=404, detail=f"Test '{test_id}' not found")
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

# Legacy endpoint for backward compatibility
@app.post("/api/tests/postgres")
async def run_postgres_test(current_user: str = Depends(require_auth)):
    """Run PostgreSQL connectivity test - legacy endpoint"""
    result = test_runner.run_test("postgresql")
    if not result:
        raise HTTPException(status_code=404, detail="PostgreSQL test not found")
    return result.get("result", result)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.port)

# Export the app for production deployment
application = app