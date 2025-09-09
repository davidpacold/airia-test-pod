from fastapi import FastAPI, Request, Depends, Form, status, BackgroundTasks, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
import uvicorn
from datetime import datetime, timedelta
import os
from typing import Optional, Dict, Any
import json

from .auth import (
    authenticate_user, create_access_token, get_current_user, require_auth
)
from .config import get_settings
from .models import TestResult, TestStatus
from .tests.test_runner import test_runner
from fastapi import HTTPException

settings = get_settings()
app = FastAPI(title="Airia Infrastructure Test Pod", version="1.0.70")

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

# Custom AI Model Testing Endpoints
@app.post("/api/tests/openai/custom")
async def test_openai_custom(
    prompt: str = Form(...),
    system_message: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: str = Depends(require_auth)
):
    """Test OpenAI with custom prompt and optional file"""
    try:
        # Get OpenAI test instance
        from .tests.openai_test import OpenAITest
        openai_test = OpenAITest()
        
        if not openai_test.is_configured():
            raise HTTPException(status_code=400, detail="OpenAI test not configured")
        
        # Read file content if provided
        file_content = None
        file_type = None
        if file:
            # Check file size (limit to 25MB)
            content = await file.read()
            if len(content) > 25 * 1024 * 1024:  # 25MB limit
                raise HTTPException(status_code=400, detail="File too large (max 25MB)")
            
            # Get file extension to determine processing method
            file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            
            if file_extension in ['txt', 'md', 'json', 'csv', 'log']:
                # Text files - decode as UTF-8
                try:
                    file_content = content.decode('utf-8')
                    file_type = 'text'
                except UnicodeDecodeError:
                    raise HTTPException(status_code=400, detail="Text file must be UTF-8 encoded")
            elif file_extension == 'pdf':
                # PDF files - extract text
                try:
                    from .utils.file_processors import process_pdf
                    file_content = process_pdf(content)
                    file_type = 'pdf'
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Failed to process PDF: {str(e)}")
            elif file_extension in ['jpg', 'jpeg', 'png']:
                # Image files - encode as base64 for vision models
                try:
                    import base64
                    file_content = base64.b64encode(content).decode('utf-8')
                    file_type = file_extension
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type. Supported: txt, md, json, csv, log, pdf, jpg, jpeg, png")
        
        # Run custom test
        result = openai_test.test_with_custom_input(
            custom_prompt=prompt,
            custom_file_content=file_content,
            file_type=file_type,
            system_message=system_message
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom test failed: {str(e)}")

@app.post("/api/tests/llama/custom")
async def test_llama_custom(
    prompt: str = Form(...),
    system_message: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: str = Depends(require_auth)
):
    """Test Llama with custom prompt and optional file"""
    try:
        # Get Llama test instance
        from .tests.llama_test import LlamaTest
        llama_test = LlamaTest()
        
        if not llama_test.is_configured():
            raise HTTPException(status_code=400, detail="Llama test not configured")
        
        # Read file content if provided
        file_content = None
        file_type = None
        if file:
            # Check file size (limit to 25MB)
            content = await file.read()
            if len(content) > 25 * 1024 * 1024:  # 25MB limit
                raise HTTPException(status_code=400, detail="File too large (max 25MB)")
            
            # Get file extension to determine processing method
            file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            
            if file_extension in ['txt', 'md', 'json', 'csv', 'log']:
                # Text files - decode as UTF-8
                try:
                    file_content = content.decode('utf-8')
                    file_type = 'text'
                except UnicodeDecodeError:
                    raise HTTPException(status_code=400, detail="Text file must be UTF-8 encoded")
            elif file_extension == 'pdf':
                # PDF files - extract text
                try:
                    from .utils.file_processors import process_pdf
                    file_content = process_pdf(content)
                    file_type = 'pdf'
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Failed to process PDF: {str(e)}")
            elif file_extension in ['jpg', 'jpeg', 'png']:
                # Image files - encode as base64 for vision models
                try:
                    import base64
                    file_content = base64.b64encode(content).decode('utf-8')
                    file_type = file_extension
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type. Supported: txt, md, json, csv, log, pdf, jpg, jpeg, png")
        
        # Run custom test
        if hasattr(llama_test, 'test_with_custom_input'):
            result = llama_test.test_with_custom_input(
                custom_prompt=prompt,
                custom_file_content=file_content,
                file_type=file_type,
                system_message=system_message
            )
        else:
            raise HTTPException(status_code=501, detail="Custom input not yet implemented for Llama test")
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom Llama test failed: {str(e)}")

@app.post("/api/tests/docintel/custom")
async def test_docintel_custom(
    prompt: Optional[str] = Form(None),
    file: UploadFile = File(...),  # File is required for Document Intelligence
    current_user: str = Depends(require_auth)
):
    """Test Document Intelligence with custom file upload"""
    try:
        # Get Document Intelligence test instance
        from .tests.document_intelligence_test import DocumentIntelligenceTest
        docintel_test = DocumentIntelligenceTest()
        
        if not docintel_test.is_configured():
            raise HTTPException(status_code=400, detail="Document Intelligence test not configured")
        
        # Check file size (limit to 25MB)
        content = await file.read()
        if len(content) > 25 * 1024 * 1024:  # 25MB limit
            raise HTTPException(status_code=400, detail="File too large (max 25MB)")
        
        # Get file extension to determine processing method
        file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        
        # Document Intelligence supports many formats: PDF, images, Office docs, etc.
        if file_extension not in ['pdf', 'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'docx', 'xlsx', 'pptx']:
            raise HTTPException(status_code=400, detail="Unsupported file type for Document Intelligence. Supported: PDF, images (jpg, png, bmp, tiff), Office documents (docx, xlsx, pptx)")
        
        # Run custom test
        result = docintel_test.test_with_custom_file(
            file_content=content,
            file_type=file_extension,
            custom_prompt=prompt
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom Document Intelligence test failed: {str(e)}")

@app.post("/api/tests/embeddings/custom")
async def test_embeddings_custom(
    text: str = Form(...),
    batch_texts: Optional[str] = Form(None),  # Comma-separated additional texts
    file: Optional[UploadFile] = File(None),
    current_user: str = Depends(require_auth)
):
    """Test embedding generation with custom text input and optional file"""
    try:
        # Get Embedding test instance
        from .tests.embedding_test import EmbeddingTest
        embedding_test = EmbeddingTest()
        
        if not embedding_test.is_configured():
            raise HTTPException(status_code=400, detail="Embedding test not configured")
        
        # Process file content if provided
        file_content = None
        file_type = None
        if file:
            # Check file size (limit to 25MB)
            content = await file.read()
            if len(content) > 25 * 1024 * 1024:  # 25MB limit
                raise HTTPException(status_code=400, detail="File too large (max 25MB)")
            
            # Get file extension to determine processing method
            file_extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
            
            if file_extension in ['txt', 'md', 'json', 'csv', 'log']:
                # Text files - decode as UTF-8
                try:
                    file_content = content.decode('utf-8')
                    file_type = 'text'
                except UnicodeDecodeError:
                    raise HTTPException(status_code=400, detail="Text file must be UTF-8 encoded")
            elif file_extension == 'pdf':
                # PDF files - extract text
                try:
                    from .utils.file_processors import process_pdf
                    file_content = process_pdf(content)
                    file_type = 'pdf'
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Failed to process PDF: {str(e)}")
            elif file_extension in ['jpg', 'jpeg', 'png']:
                # Image files - note that these aren't ideal for text embeddings
                try:
                    import base64
                    file_content = base64.b64encode(content).decode('utf-8')
                    file_type = file_extension
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type for embeddings. Supported: txt, md, json, csv, log, pdf")
        
        # Process batch texts if provided
        batch_text_list = None
        if batch_texts:
            # Split by comma and clean up
            batch_text_list = [t.strip() for t in batch_texts.split(',') if t.strip()]
        
        # Run custom test
        result = embedding_test.test_with_custom_input(
            custom_text=text,
            custom_file_content=file_content,
            file_type=file_type,
            batch_texts=batch_text_list
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom embedding test failed: {str(e)}")

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