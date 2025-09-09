"""
Pytest configuration and shared fixtures for airia-test-pod unit tests.

This file contains shared test fixtures, configuration, and utilities
used across all unit tests.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
import io

# Import application components
from app.main import app
from app.config import Settings, get_settings
from app.auth import create_access_token
from datetime import timedelta


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Create test settings with safe defaults."""
    return Settings(
        app_name="Test Airia Pod",
        version="1.0.0-test",
        auth_username="testuser",
        auth_password="testpass",
        secret_key="test-secret-key-for-testing-only",
        algorithm="HS256",
        access_token_expire_minutes=30,
        port=8080,
        postgres_host="localhost",
        postgres_port=5432,
        postgres_database="test_db",
        postgres_user="test_user",
        postgres_password="test_pass",
        postgres_sslmode="disable"
    )


@pytest.fixture
def override_settings(test_settings):
    """Override the settings dependency for testing."""
    def _get_test_settings():
        return test_settings
    
    app.dependency_overrides[get_settings] = _get_test_settings
    yield test_settings
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_settings):
    """Create a test client for FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(client, test_settings):
    """Create a test client with authentication token."""
    # Create access token
    access_token = create_access_token(
        data={"sub": test_settings.auth_username},
        expires_delta=timedelta(minutes=30)
    )
    
    # Set the token in the client's cookies
    client.cookies.set("access_token", f"Bearer {access_token}")
    
    yield client


@pytest.fixture
def mock_file_upload():
    """Create a mock file upload for testing."""
    def _create_mock_file(filename="test.txt", content="test content", content_type="text/plain"):
        file_content = content.encode() if isinstance(content, str) else content
        return UploadFile(
            filename=filename,
            file=io.BytesIO(file_content),
            content_type=content_type
        )
    return _create_mock_file


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"test content")
        tf.flush()
        yield tf.name
    # Clean up
    os.unlink(tf.name)


@pytest.fixture
def mock_postgres_connection():
    """Mock PostgreSQL connection for testing."""
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = None
    mock_conn.fetch.return_value = [{"version": "PostgreSQL 13.0"}]
    mock_conn.fetchrow.return_value = {"version": "PostgreSQL 13.0"}
    mock_conn.close.return_value = None
    return mock_conn


@pytest.fixture
def mock_blob_client():
    """Mock Azure Blob Storage client for testing."""
    mock_client = Mock()
    mock_client.upload_blob.return_value = None
    mock_client.download_blob.return_value = Mock(readall=lambda: b"test blob content")
    mock_client.list_blobs.return_value = [Mock(name="test.txt")]
    return mock_client


@pytest.fixture
def sample_user_inputs():
    """Sample user inputs for testing sanitization."""
    return {
        "clean_text": "This is clean text",
        "html_input": "<script>alert('xss')</script>Hello World",
        "sql_injection": "'; DROP TABLE users; --",
        "long_text": "A" * 15000,  # Longer than 10KB limit
        "javascript_url": "javascript:alert('xss')",
        "event_handler": "<div onclick='alert(1)'>Click me</div>",
        "null_bytes": "Hello\x00World\x01Test",
        "unicode_text": "Hello 世界 🌍",
        "empty_text": "",
        "whitespace_only": "   \t\n   ",
    }


@pytest.fixture
def sample_ai_prompts():
    """Sample AI prompts for testing."""
    return {
        "valid_prompt": "Explain the concept of machine learning",
        "short_prompt": "Hi",
        "long_prompt": "A" * 5000,  # Longer than 4KB limit
        "empty_prompt": "",
        "xss_prompt": "<script>alert('hack')</script>Explain AI",
        "injection_prompt": "'; DROP TABLE models; --",
    }


@pytest.fixture
def sample_credentials():
    """Sample credentials for testing authentication."""
    return {
        "valid": {"username": "testuser", "password": "testpass"},
        "invalid_user": {"username": "wronguser", "password": "testpass"},
        "invalid_pass": {"username": "testuser", "password": "wrongpass"},
        "empty_user": {"username": "", "password": "testpass"},
        "empty_pass": {"username": "testuser", "password": ""},
        "xss_user": {"username": "<script>alert('xss')</script>", "password": "test"},
        "long_user": {"username": "a" * 100, "password": "test"},
        "special_chars": {"username": "user@domain.com", "password": "p@$$w0rd!"},
    }


@pytest.fixture
def mock_jwt_payload():
    """Mock JWT payload for testing."""
    return {
        "sub": "testuser",
        "exp": 1234567890,
        "iat": 1234567800
    }


# Test markers for organizing tests
pytest_plugins = []

# Custom assertions and utilities
class TestHelpers:
    @staticmethod
    def assert_no_xss(text: str):
        """Assert that text doesn't contain XSS patterns."""
        xss_patterns = ["<script", "javascript:", "vbscript:", "on\\w+\\s*="]
        for pattern in xss_patterns:
            assert pattern.lower() not in text.lower(), f"XSS pattern '{pattern}' found in: {text}"
    
    @staticmethod
    def assert_safe_filename(filename: str):
        """Assert that filename is safe for filesystem."""
        dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "/", "\\", "\x00"]
        for char in dangerous_chars:
            assert char not in filename, f"Dangerous character '{char}' found in filename: {filename}"
    
    @staticmethod
    def assert_length_limit(text: str, max_length: int):
        """Assert that text doesn't exceed length limit."""
        assert len(text) <= max_length, f"Text length {len(text)} exceeds limit {max_length}"


@pytest.fixture
def test_helpers():
    """Provide test helper utilities."""
    return TestHelpers