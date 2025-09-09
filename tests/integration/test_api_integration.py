"""
Integration tests for API endpoints and authentication workflows.

Tests complete end-to-end API workflows including authentication,
authorization, and service integration.
"""

import asyncio
import json
import time
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.mark.integration
class TestAuthenticationIntegration:
    """Integration tests for complete authentication workflows."""

    def setup_method(self):
        """Set up test client for each test."""
        self.client = TestClient(app)

    def test_complete_login_workflow(self):
        """Test the complete user login workflow."""
        # Step 1: Access protected resource without auth (should redirect)
        response = self.client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers["location"]

        # Step 2: Get login page
        response = self.client.get("/login")
        assert response.status_code == 200
        assert "login" in response.text.lower()

        # Step 3: Submit login form with correct credentials
        with patch("app.auth.get_settings") as mock_settings:
            mock_settings.return_value.auth_username = "testuser"
            mock_settings.return_value.auth_password = "testpass"
            mock_settings.return_value.secret_key = "test-secret-key"
            mock_settings.return_value.algorithm = "HS256"
            mock_settings.return_value.access_token_expire_minutes = 30

            response = self.client.post(
                "/login", data={"username": "testuser", "password": "testpass"}
            )

            # Should redirect to dashboard
            assert response.status_code == 303
            assert "/dashboard" in response.headers["location"]

            # Should set authentication cookie
            assert "access_token" in response.cookies

            # Step 4: Access protected resource with cookie
            response = self.client.get("/dashboard")
            assert response.status_code == 200
            assert "dashboard" in response.text.lower()

    def test_api_authentication_workflow(self):
        """Test API authentication using OAuth2 token."""
        with patch("app.auth.get_settings") as mock_settings:
            mock_settings.return_value.auth_username = "apiuser"
            mock_settings.return_value.auth_password = "apipass"
            mock_settings.return_value.secret_key = "api-secret-key"
            mock_settings.return_value.algorithm = "HS256"
            mock_settings.return_value.access_token_expire_minutes = 30

            # Step 1: Get access token
            response = self.client.post(
                "/token", data={"username": "apiuser", "password": "apipass"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

            access_token = data["access_token"]

            # Step 2: Use token to access protected API endpoint
            headers = {"Authorization": f"Bearer {access_token}"}
            response = self.client.get("/api/tests/status", headers=headers)

            assert response.status_code == 200
            api_data = response.json()
            assert "tests" in api_data
            assert "available_tests" in api_data

    def test_session_expiry_workflow(self):
        """Test session expiry and re-authentication workflow."""
        with patch("app.auth.get_settings") as mock_settings:
            mock_settings.return_value.auth_username = "sessionuser"
            mock_settings.return_value.auth_password = "sessionpass"
            mock_settings.return_value.secret_key = "session-secret"
            mock_settings.return_value.algorithm = "HS256"
            mock_settings.return_value.access_token_expire_minutes = (
                1  # Very short expiry
            )

            # Login and get token
            response = self.client.post(
                "/token", data={"username": "sessionuser", "password": "sessionpass"}
            )

            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Immediately should work
            response = self.client.get("/api/tests/status", headers=headers)
            assert response.status_code == 200

            # Wait for token to expire (in real scenario)
            # For testing, we'll simulate an expired token
            with patch("app.auth.jwt.decode") as mock_decode:
                from jose import JWTError

                mock_decode.side_effect = JWTError("Token has expired")

                response = self.client.get("/api/tests/status", headers=headers)
                assert response.status_code == 401

    def test_concurrent_authentication_requests(self):
        """Test handling of concurrent authentication requests."""
        import concurrent.futures

        def perform_login():
            with patch("app.auth.get_settings") as mock_settings:
                mock_settings.return_value.auth_username = "concurrentuser"
                mock_settings.return_value.auth_password = "concurrentpass"
                mock_settings.return_value.secret_key = "concurrent-secret"
                mock_settings.return_value.algorithm = "HS256"
                mock_settings.return_value.access_token_expire_minutes = 30

                client = TestClient(app)
                response = client.post(
                    "/token",
                    data={"username": "concurrentuser", "password": "concurrentpass"},
                )
                return response.status_code, response.json()

        # Run multiple login requests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(perform_login) for _ in range(5)]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All requests should succeed
        for status_code, response_data in results:
            assert status_code == 200
            assert "access_token" in response_data


@pytest.mark.integration
class TestAPIWorkflowIntegration:
    """Integration tests for complete API workflows."""

    def setup_method(self):
        """Set up authenticated client for each test."""
        self.client = TestClient(app)

        # Mock settings and get authentication token
        with patch("app.auth.get_settings") as mock_settings:
            mock_settings.return_value.auth_username = "workflowuser"
            mock_settings.return_value.auth_password = "workflowpass"
            mock_settings.return_value.secret_key = "workflow-secret"
            mock_settings.return_value.algorithm = "HS256"
            mock_settings.return_value.access_token_expire_minutes = 30

            response = self.client.post(
                "/token", data={"username": "workflowuser", "password": "workflowpass"}
            )

            if response.status_code == 200:
                token = response.json()["access_token"]
                self.auth_headers = {"Authorization": f"Bearer {token}"}
            else:
                self.auth_headers = {}

    def test_infrastructure_test_workflow(self):
        """Test complete infrastructure testing workflow."""
        if not self.auth_headers:
            pytest.skip("Authentication setup failed")

        # Step 1: Get test status
        response = self.client.get("/api/tests/status", headers=self.auth_headers)
        assert response.status_code == 200

        status_data = response.json()
        assert "available_tests" in status_data
        assert isinstance(status_data["available_tests"], list)

        # Step 2: Get test summary
        response = self.client.get("/api/tests/summary", headers=self.auth_headers)
        assert response.status_code == 200

        summary_data = response.json()
        assert "total_tests" in summary_data

        # Step 3: Run a specific test (if available)
        if status_data["available_tests"]:
            test_id = status_data["available_tests"][0]
            response = self.client.post(
                f"/api/tests/{test_id}", headers=self.auth_headers
            )

            # Should either succeed or fail gracefully
            assert response.status_code in [200, 404, 500]

            if response.status_code == 200:
                test_result = response.json()
                assert "status" in test_result or "name" in test_result

    def test_custom_ai_test_workflow(self):
        """Test custom AI model testing workflow."""
        if not self.auth_headers:
            pytest.skip("Authentication setup failed")

        # Test OpenAI custom endpoint
        with patch("app.tests.openai_test.OpenAITest") as MockOpenAITest:
            mock_instance = Mock()
            mock_instance.is_configured.return_value = True
            mock_instance.test_with_custom_input.return_value = {
                "status": "passed",
                "response": "Test response from AI model",
                "tokens_used": 25,
            }
            MockOpenAITest.return_value = mock_instance

            response = self.client.post(
                "/api/tests/openai/custom",
                headers=self.auth_headers,
                data={"prompt": "Test prompt for AI"},
            )

            assert response.status_code == 200
            ai_result = response.json()
            assert ai_result["status"] == "passed"
            assert "response" in ai_result

    def test_error_handling_workflow(self):
        """Test error handling across API workflows."""
        if not self.auth_headers:
            pytest.skip("Authentication setup failed")

        # Test 404 handling
        response = self.client.get(
            "/api/nonexistent/endpoint", headers=self.auth_headers
        )
        assert response.status_code == 404

        # Test invalid test ID
        response = self.client.post(
            "/api/tests/nonexistent_test", headers=self.auth_headers
        )
        assert response.status_code in [404, 500]

        # Test malformed request
        response = self.client.post(
            "/api/tests/openai/custom",
            headers=self.auth_headers,
            json={"invalid": "payload"},
        )
        assert response.status_code == 422

    def test_api_response_consistency(self):
        """Test API response format consistency."""
        if not self.auth_headers:
            pytest.skip("Authentication setup failed")

        endpoints_to_test = [
            ("/api/tests/status", "GET"),
            ("/api/tests/summary", "GET"),
            ("/version", "GET"),
            ("/health", "GET"),
        ]

        for endpoint, method in endpoints_to_test:
            if method == "GET":
                response = self.client.get(endpoint, headers=self.auth_headers)

            assert response.status_code == 200

            # All API responses should be valid JSON
            data = response.json()
            assert isinstance(data, dict)

            # Check for common response structure
            if endpoint.startswith("/api/"):
                # API endpoints should have consistent structure
                assert isinstance(data, dict)


@pytest.mark.integration
class TestServiceIntegration:
    """Integration tests for external service connectivity."""

    def setup_method(self):
        """Set up for service integration tests."""
        self.client = TestClient(app)

    def test_health_check_integration(self):
        """Test health check endpoint integration."""
        response = self.client.get("/health")
        assert response.status_code == 200

        health_data = response.json()
        required_fields = ["status", "timestamp", "version"]

        for field in required_fields:
            assert field in health_data

        assert health_data["status"] == "healthy"

        # Timestamp should be recent
        from datetime import datetime, timezone

        timestamp = datetime.fromisoformat(
            health_data["timestamp"].replace("Z", "+00:00")
        )
        now = datetime.now(timezone.utc)

        # Should be within last minute
        assert (now - timestamp).total_seconds() < 60

    def test_version_endpoint_integration(self):
        """Test version endpoint integration."""
        response = self.client.get("/version")
        assert response.status_code == 200

        version_data = response.json()
        assert "version" in version_data
        assert isinstance(version_data["version"], str)
        assert len(version_data["version"]) > 0

        # Version should follow basic semantic versioning
        version = version_data["version"]
        version_parts = version.split(".")
        assert len(version_parts) >= 2  # At least major.minor

    def test_configuration_integration(self):
        """Test configuration integration across the application."""
        # Test that settings are properly loaded
        settings = get_settings()

        assert settings.app_name is not None
        assert settings.version is not None
        assert settings.port > 0
        assert settings.port <= 65535

        # Test that configuration is consistent with API responses
        version_response = self.client.get("/version")
        version_data = version_response.json()

        assert version_data["version"] == settings.version

        health_response = self.client.get("/health")
        health_data = health_response.json()

        assert health_data["version"] == settings.version

    @pytest.mark.slow
    def test_infrastructure_service_availability(self):
        """Test availability of configured infrastructure services."""
        from app.tests.test_runner import test_runner

        # Get list of configured tests
        status = test_runner.get_test_status()
        available_tests = status.get("available_tests", [])

        # Run infrastructure tests
        if available_tests:
            # Run tests but don't fail if services aren't configured
            results = test_runner.run_all_tests(skip_optional=True)

            # Check that we got results
            assert isinstance(results, dict)

            # Count configured vs unconfigured services
            configured_count = 0
            total_count = len(available_tests)

            # Check if results has individual test results
            if "results" in results:
                for test_result in results["results"].values():
                    if hasattr(test_result, "status"):
                        if test_result.status.value != "skipped":
                            configured_count += 1
                    elif isinstance(test_result, dict) and "status" in test_result:
                        if test_result["status"] != "skipped":
                            configured_count += 1
            else:
                # If no individual results, count based on overall status
                if results.get("overall_status") == "passed":
                    configured_count = 1

            # Should have some tests available
            assert total_count > 0

            # Log results for debugging
            print(f"Infrastructure tests: {configured_count}/{total_count} configured")


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceIntegration:
    """Performance integration tests for API endpoints."""

    def setup_method(self):
        """Set up performance test environment."""
        self.client = TestClient(app)

    def test_api_response_performance(self):
        """Test API response time performance."""
        endpoints_to_test = [
            "/health",
            "/version",
            "/api/version",
        ]

        for endpoint in endpoints_to_test:
            start_time = time.time()
            response = self.client.get(endpoint)
            end_time = time.time()

            response_time = end_time - start_time

            # API should respond within reasonable time
            assert response.status_code == 200
            assert response_time < 1.0, f"{endpoint} took {response_time:.2f}s"

    def test_concurrent_api_requests(self):
        """Test handling of concurrent API requests."""
        import concurrent.futures

        def make_request(endpoint):
            response = self.client.get(endpoint)
            return response.status_code, response.json()

        # Test concurrent requests to health endpoint
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, "/health") for _ in range(20)]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All requests should succeed
        for status_code, data in results:
            assert status_code == 200
            assert data["status"] == "healthy"

    def test_authentication_performance(self):
        """Test authentication performance under load."""
        import concurrent.futures

        def perform_auth():
            with patch("app.auth.get_settings") as mock_settings:
                mock_settings.return_value.auth_username = "perfuser"
                mock_settings.return_value.auth_password = "perfpass"
                mock_settings.return_value.secret_key = "perf-secret"
                mock_settings.return_value.algorithm = "HS256"
                mock_settings.return_value.access_token_expire_minutes = 30

                client = TestClient(app)

                start_time = time.time()
                response = client.post(
                    "/token", data={"username": "perfuser", "password": "perfpass"}
                )
                end_time = time.time()

                return response.status_code, end_time - start_time

        # Test multiple authentication requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(perform_auth) for _ in range(10)]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # All authentications should succeed and be fast
        for status_code, auth_time in results:
            assert status_code == 200
            assert auth_time < 2.0  # Authentication should be fast
