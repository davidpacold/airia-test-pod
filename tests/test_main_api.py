"""
Unit tests for main API endpoints.

Tests the main.py FastAPI application endpoints including
health checks, version endpoints, authentication flows, and API routes.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.skip(reason="API integration - disabled for core build pipeline focus")
class TestHealthEndpoints:
    """Test health and version endpoints."""

    def test_health_endpoint(self, client, test_settings):
        """Test the /health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert data["version"] == test_settings.version

    def test_version_endpoint(self, client, test_settings):
        """Test the /version endpoint."""
        response = client.get("/version")

        assert response.status_code == 200
        data = response.json()

        assert "version" in data
        assert data["version"] == test_settings.version

    def test_api_version_endpoint(self, client, test_settings):
        """Test the /api/version endpoint."""
        response = client.get("/api/version")

        assert response.status_code == 200
        data = response.json()

        assert "version" in data
        assert data["version"] == test_settings.version

    def test_version_endpoints_consistency(self, client):
        """Test that all version endpoints return consistent data."""
        version_response = client.get("/version")
        api_version_response = client.get("/api/version")
        health_response = client.get("/health")

        version_data = version_response.json()
        api_version_data = api_version_response.json()
        health_data = health_response.json()

        # All should return the same version
        assert version_data["version"] == api_version_data["version"]
        assert version_data["version"] == health_data["version"]


class TestRootAndAuthRoutes:
    """Test root routing and authentication pages."""

    def test_root_redirect_unauthenticated(self, client):
        """Test root path redirects unauthenticated users to login."""
        response = client.get("/", follow_redirects=False)

        # Should redirect to login
        assert response.status_code == 303
        assert "/login" in response.headers["location"]

    def test_root_redirect_authenticated(self, authenticated_client):
        """Test root path redirects authenticated users to dashboard."""
        response = authenticated_client.get("/", follow_redirects=False)

        # Should redirect to dashboard
        assert response.status_code == 303
        assert "/dashboard" in response.headers["location"]

    def test_login_page_unauthenticated(self, client):
        """Test login page loads for unauthenticated users."""
        response = client.get("/login")

        assert response.status_code == 200
        assert "login" in response.text.lower()

    def test_login_page_authenticated_redirect(self, authenticated_client):
        """Test authenticated users are redirected from login page."""
        response = authenticated_client.get("/login", follow_redirects=False)

        # Should redirect to dashboard
        assert response.status_code == 303
        assert "/dashboard" in response.headers["location"]

    def test_dashboard_unauthenticated_redirect(self, client):
        """Test unauthenticated access to dashboard redirects to login."""
        response = client.get("/dashboard")

        # TestClient follows redirects by default
        assert response.status_code == 200
        # Should end up on login page
        assert "login" in response.url.path.lower()

    def test_dashboard_authenticated(self, authenticated_client, test_settings):
        """Test authenticated access to dashboard."""
        response = authenticated_client.get("/dashboard")

        assert response.status_code == 200
        assert "dashboard" in response.text.lower()
        assert test_settings.app_name in response.text


@pytest.mark.skip(reason="API integration - disabled for core build pipeline focus")
class TestAuthenticationAPI:
    """Test authentication API endpoints."""

    def test_login_success(self, client, test_settings):
        """Test successful login."""
        response = client.post(
            "/login",
            data={
                "username": test_settings.auth_username,
                "password": test_settings.auth_password,
            },
        )

        # Should redirect to dashboard
        assert response.status_code == 303
        assert "/dashboard" in response.headers["location"]

        # Should set authentication cookie
        assert "access_token" in response.cookies
        token_value = response.cookies["access_token"]
        assert token_value.startswith("Bearer ")

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/login", data={"username": "wrong_user", "password": "wrong_pass"}
        )

        assert response.status_code == 401
        assert "Invalid username or password" in response.text

    def test_login_empty_credentials(self, client):
        """Test login with empty credentials."""
        # Empty username
        response = client.post("/login", data={"username": "", "password": "testpass"})
        assert response.status_code == 400

        # Empty password
        response = client.post("/login", data={"username": "testuser", "password": ""})
        assert response.status_code == 400

    def test_login_malicious_credentials(self, client, test_settings):
        """Test login with malicious input."""
        malicious_inputs = [
            {"username": "<script>alert('xss')</script>", "password": "test"},
            {"username": "'; DROP TABLE users; --", "password": "test"},
            {"username": "admin", "password": "<script>alert('xss')</script>"},
        ]

        for malicious in malicious_inputs:
            response = client.post("/login", data=malicious)
            # Should either return 400 (validation error) or 401 (auth failed)
            assert response.status_code in [400, 401]

    def test_token_endpoint_success(self, client, test_settings):
        """Test OAuth2 token endpoint success."""
        response = client.post(
            "/token",
            data={
                "username": test_settings.auth_username,
                "password": test_settings.auth_password,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_token_endpoint_invalid_credentials(self, client):
        """Test OAuth2 token endpoint with invalid credentials."""
        response = client.post(
            "/token", data={"username": "wrong_user", "password": "wrong_pass"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "error_code" in data or "detail" in data

    def test_logout(self, authenticated_client):
        """Test logout functionality."""
        response = authenticated_client.get("/logout", follow_redirects=False)

        # Should redirect to login
        assert response.status_code == 303
        assert "/login" in response.headers["location"]

        # Should clear the access token cookie
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "access_token" in set_cookie_header


class TestProtectedAPIEndpoints:
    """Test protected API endpoints that require authentication."""

    def test_test_status_unauthenticated(self, client):
        """Test accessing test status without authentication."""
        response = client.get("/api/tests/status")

        assert response.status_code == 401
        data = response.json()
        assert "Not authenticated" in data["detail"]

    def test_test_status_authenticated(self, authenticated_client):
        """Test accessing test status with authentication."""
        with patch("app.main.test_runner.get_test_status") as mock_status:
            mock_status.return_value = {
                "tests": {},
                "available_tests": ["test1", "test2"],
                "timestamp": "2023-01-01T00:00:00",
            }

            response = authenticated_client.get("/api/tests/status")

            assert response.status_code == 200
            data = response.json()
            assert "tests" in data
            assert "available_tests" in data
            assert "timestamp" in data

    def test_test_summary_authenticated(self, authenticated_client):
        """Test test summary endpoint."""
        with patch("app.main.test_runner.get_test_summary") as mock_summary:
            mock_summary.return_value = {
                "total_tests": 5,
                "passed_count": 3,
                "failed_count": 2,
                "overall_status": "failed",
            }

            response = authenticated_client.get("/api/tests/summary")

            assert response.status_code == 200
            data = response.json()
            assert data["total_tests"] == 5
            assert data["passed_count"] == 3
            assert data["failed_count"] == 2

    def test_run_all_tests_authenticated(self, authenticated_client):
        """Test running all tests endpoint."""
        with patch("app.main.test_runner.run_all_tests") as mock_run_all:
            mock_run_all.return_value = {
                "overall_status": "passed",
                "test_count": 3,
                "passed_count": 3,
                "failed_count": 0,
                "results": {},
            }

            response = authenticated_client.post("/api/tests/run-all")

            assert response.status_code == 200
            data = response.json()
            assert data["overall_status"] == "passed"
            assert data["test_count"] == 3

    def test_run_single_test_success(self, authenticated_client):
        """Test running a specific test successfully."""
        with patch("app.main.test_runner.run_test") as mock_run_test:
            mock_run_test.return_value = {
                "name": "PostgreSQL Test",
                "status": "passed",
                "message": "Test completed successfully",
            }

            response = authenticated_client.post("/api/tests/postgresql")

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "PostgreSQL Test"
            assert data["status"] == "passed"

    def test_run_single_test_not_found(self, authenticated_client):
        """Test running a non-existent test."""
        with patch("app.main.test_runner.run_test") as mock_run_test:
            mock_run_test.return_value = None  # Test not found

            response = authenticated_client.post("/api/tests/nonexistent")

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["message"].lower()

    def test_get_test_logs(self, authenticated_client):
        """Test getting test logs."""
        with patch("app.main.test_runner.get_test_logs") as mock_logs:
            mock_logs.return_value = [
                {"level": "INFO", "message": "Test started"},
                {"level": "ERROR", "message": "Connection failed"},
            ]

            response = authenticated_client.get("/api/tests/postgresql/logs")

            assert response.status_code == 200
            data = response.json()
            assert data["test_id"] == "postgresql"
            assert len(data["logs"]) == 2

    def test_get_test_remediation(self, authenticated_client):
        """Test getting test remediation suggestions."""
        with patch(
            "app.main.test_runner.get_remediation_suggestions"
        ) as mock_remediation:
            mock_remediation.return_value = [
                "Check database connection settings",
                "Verify credentials are correct",
            ]

            response = authenticated_client.get("/api/tests/postgresql/remediation")

            assert response.status_code == 200
            data = response.json()
            assert data["test_id"] == "postgresql"
            assert len(data["suggestions"]) == 2

    def test_clear_test_results(self, authenticated_client):
        """Test clearing all test results."""
        with patch("app.main.test_runner.clear_results") as mock_clear:
            response = authenticated_client.delete("/api/tests/results")

            assert response.status_code == 200
            data = response.json()
            assert "cleared" in data["message"].lower()
            mock_clear.assert_called_once()


class TestCustomAITestEndpoints:
    """Test custom AI model testing endpoints."""

    @pytest.mark.asyncio
    async def test_openai_custom_success(self, authenticated_client):
        """Test successful OpenAI custom test."""
        with patch("app.tests.openai_test.OpenAITest") as MockOpenAITest:
            # Mock OpenAI test instance
            mock_instance = Mock()
            mock_instance.is_configured.return_value = True
            mock_instance.test_with_custom_input.return_value = {
                "status": "passed",
                "response": "AI response here",
            }
            MockOpenAITest.return_value = mock_instance

            response = authenticated_client.post(
                "/api/tests/openai/custom", data={"prompt": "Explain machine learning"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "passed"

    def test_openai_custom_not_configured(self, authenticated_client):
        """Test OpenAI custom test when not configured."""
        with patch("app.tests.openai_test.OpenAITest") as MockOpenAITest:
            mock_instance = Mock()
            mock_instance.is_configured.return_value = False
            MockOpenAITest.return_value = mock_instance

            response = authenticated_client.post(
                "/api/tests/openai/custom", data={"prompt": "Test prompt"}
            )

            assert response.status_code == 500
            data = response.json()
            assert "not configured" in data["message"].lower()

    def test_openai_custom_malicious_prompt(self, authenticated_client):
        """Test OpenAI custom test with malicious prompt."""
        malicious_prompts = [
            "<script>alert('xss')</script>",
            "",  # Empty prompt
            "Hi",  # Too short
        ]

        for prompt in malicious_prompts:
            response = authenticated_client.post(
                "/api/tests/openai/custom", data={"prompt": prompt}
            )
            # Should return 400 for validation errors
            assert response.status_code == 400

    def test_llama_custom_not_implemented(self, authenticated_client):
        """Test Llama custom test when method not implemented."""
        with patch("app.tests.llama_test.LlamaTest") as MockLlamaTest:
            mock_instance = Mock()
            mock_instance.is_configured.return_value = True
            # Don't add test_with_custom_input method to simulate not implemented
            MockLlamaTest.return_value = mock_instance

            response = authenticated_client.post(
                "/api/tests/llama/custom", data={"prompt": "Test prompt"}
            )

            assert response.status_code == 500
            data = response.json()
            assert "not yet implemented" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_docintel_custom_no_file(self, authenticated_client):
        """Test Document Intelligence custom test without file."""
        response = authenticated_client.post("/api/tests/docintel/custom")

        # Should require a file
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_embeddings_custom_success(self, authenticated_client):
        """Test successful embeddings custom test."""
        with patch("app.tests.embedding_test.EmbeddingTest") as MockEmbeddingTest:
            mock_instance = Mock()
            mock_instance.is_configured.return_value = True
            mock_instance.test_with_custom_input.return_value = {
                "status": "passed",
                "embedding": [0.1, 0.2, 0.3],
            }
            MockEmbeddingTest.return_value = mock_instance

            response = authenticated_client.post(
                "/api/tests/embeddings/custom",
                data={"text": "Sample text for embedding"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "passed"


class TestSecurityHeaders:
    """Test security headers middleware."""

    def test_security_headers_present(self, client):
        """Test that security headers are added to responses."""
        response = client.get("/health")

        assert response.status_code == 200

        # Check security headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_security_headers_on_all_endpoints(self, client):
        """Test that security headers are present on all endpoints."""
        endpoints = ["/health", "/version", "/login"]

        for endpoint in endpoints:
            response = client.get(endpoint)

            # Check that security headers are present
            assert "X-Content-Type-Options" in response.headers
            assert "X-Frame-Options" in response.headers
            assert "X-XSS-Protection" in response.headers
            assert "Referrer-Policy" in response.headers


@pytest.mark.api
class TestAPIErrorHandling:
    """Test API error handling and responses."""

    def test_404_handling(self, client):
        """Test 404 error handling."""
        response = client.get("/api/nonexistent/endpoint")

        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test 405 method not allowed handling."""
        # Try POST to GET-only endpoint
        response = client.post("/health")

        assert response.status_code == 405

    def test_validation_error_handling(self, authenticated_client):
        """Test validation error responses."""
        # Send malformed JSON to API endpoint
        response = authenticated_client.post(
            "/api/tests/openai/custom",
            json={"invalid": "data"},  # Missing required 'prompt'
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_internal_server_error_handling(self, authenticated_client):
        """Test internal server error handling."""
        with patch("app.main.test_runner.get_test_status") as mock_status:
            # Simulate an internal error
            mock_status.side_effect = Exception("Database connection failed")

            response = authenticated_client.get("/api/tests/status")

            # Should return 500 with error details
            assert response.status_code == 500
            data = response.json()
            assert "error_code" in data or "detail" in data


class TestLegacyEndpoints:
    """Test legacy endpoint compatibility."""

    def test_postgres_legacy_endpoint(self, authenticated_client):
        """Test legacy PostgreSQL test endpoint."""
        with patch("app.main.test_runner.run_test") as mock_run_test:
            mock_run_test.return_value = {
                "result": {
                    "status": "passed",
                    "message": "PostgreSQL connection successful",
                }
            }

            response = authenticated_client.post("/api/tests/postgres")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "passed"

    def test_postgres_legacy_endpoint_not_found(self, authenticated_client):
        """Test legacy PostgreSQL test endpoint when test not found."""
        with patch("app.main.test_runner.run_test") as mock_run_test:
            mock_run_test.return_value = None

            response = authenticated_client.post("/api/tests/postgres")

            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]
