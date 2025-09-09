"""
Unit tests for authentication and authorization functionality.

Tests the auth.py module including JWT token creation, validation,
password hashing, and authentication flows.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt

from app.auth import (authenticate_user, create_access_token, get_current_user,
                      get_password_hash, require_auth, verify_password)
from app.config import Settings


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_password_hash_and_verify(self):
        """Test that password hashing and verification works correctly."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        # Hash should not be the same as original password
        assert hashed != password

        # Should be able to verify correct password
        assert verify_password(password, hashed) is True

        # Should reject incorrect password
        assert verify_password("wrong_password", hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password123"
        password2 = "password456"

        hash1 = get_password_hash(password1)
        hash2 = get_password_hash(password2)

        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "same_password"

        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Should be different due to salt, but both should verify
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestAuthentication:
    """Test user authentication logic."""

    def test_authenticate_user_success(self, test_settings):
        """Test successful user authentication."""
        with patch("app.auth.get_settings", return_value=test_settings):
            result = authenticate_user(
                test_settings.auth_username, test_settings.auth_password
            )
            assert result is True

    def test_authenticate_user_wrong_username(self, test_settings):
        """Test authentication fails with wrong username."""
        with patch("app.auth.get_settings", return_value=test_settings):
            result = authenticate_user("wrong_username", test_settings.auth_password)
            assert result is False

    def test_authenticate_user_wrong_password(self, test_settings):
        """Test authentication fails with wrong password."""
        with patch("app.auth.get_settings", return_value=test_settings):
            result = authenticate_user(test_settings.auth_username, "wrong_password")
            assert result is False

    def test_authenticate_user_empty_credentials(self, test_settings):
        """Test authentication fails with empty credentials."""
        with patch("app.auth.get_settings", return_value=test_settings):
            assert authenticate_user("", test_settings.auth_password) is False
            assert authenticate_user(test_settings.auth_username, "") is False
            assert authenticate_user("", "") is False


class TestJWTTokens:
    """Test JWT token creation and validation."""

    def test_create_access_token_default_expiry(self, test_settings):
        """Test creating access token with default expiry."""
        with patch("app.auth.get_settings", return_value=test_settings):
            data = {"sub": "testuser"}
            token = create_access_token(data)

            # Decode token to verify contents
            payload = jwt.decode(
                token, test_settings.secret_key, algorithms=[test_settings.algorithm]
            )

            assert payload["sub"] == "testuser"
            assert "exp" in payload

    def test_create_access_token_custom_expiry(self, test_settings):
        """Test creating access token with custom expiry."""
        with patch("app.auth.get_settings", return_value=test_settings):
            data = {"sub": "testuser"}
            expires_delta = timedelta(hours=1)
            token = create_access_token(data, expires_delta)

            # Decode token to verify expiry
            payload = jwt.decode(
                token, test_settings.secret_key, algorithms=[test_settings.algorithm]
            )

            # Check expiry is approximately 1 hour from now
            exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            expected_time = datetime.now(timezone.utc) + expires_delta

            # Allow 10 second difference for processing time
            assert abs((exp_time - expected_time).total_seconds()) < 10

    def test_create_access_token_custom_data(self, test_settings):
        """Test creating access token with custom data."""
        with patch("app.auth.get_settings", return_value=test_settings):
            data = {
                "sub": "testuser",
                "role": "admin",
                "permissions": ["read", "write"],
            }
            token = create_access_token(data)

            payload = jwt.decode(
                token, test_settings.secret_key, algorithms=[test_settings.algorithm]
            )

            assert payload["sub"] == "testuser"
            assert payload["role"] == "admin"
            assert payload["permissions"] == ["read", "write"]


class TestGetCurrentUser:
    """Test current user extraction from requests."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_header_token(self, test_settings):
        """Test getting current user from Authorization header."""
        with patch("app.auth.get_settings", return_value=test_settings):
            # Create valid token
            token = create_access_token({"sub": "testuser"})

            # Mock request
            request = Mock(spec=Request)
            request.cookies = {}

            # Test with valid token
            result = await get_current_user(request, token)
            assert result == "testuser"

    @pytest.mark.asyncio
    async def test_get_current_user_valid_cookie_token(self, test_settings):
        """Test getting current user from cookie."""
        with patch("app.auth.get_settings", return_value=test_settings):
            # Create valid token
            token = create_access_token({"sub": "testuser"})

            # Mock request with cookie
            request = Mock(spec=Request)
            request.cookies = {"access_token": f"Bearer {token}"}

            result = await get_current_user(request, None)
            assert result == "testuser"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, test_settings):
        """Test handling invalid JWT token."""
        with patch("app.auth.get_settings", return_value=test_settings):
            request = Mock(spec=Request)
            request.cookies = {}

            # Test with invalid token
            result = await get_current_user(request, "invalid_token")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, test_settings):
        """Test handling expired JWT token."""
        with patch("app.auth.get_settings", return_value=test_settings):
            # Create expired token
            past_time = datetime.now(timezone.utc) - timedelta(hours=1)
            expired_data = {"sub": "testuser", "exp": past_time.timestamp()}
            expired_token = jwt.encode(
                expired_data,
                test_settings.secret_key,
                algorithm=test_settings.algorithm,
            )

            request = Mock(spec=Request)
            request.cookies = {}

            result = await get_current_user(request, expired_token)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, test_settings):
        """Test handling request with no token."""
        with patch("app.auth.get_settings", return_value=test_settings):
            request = Mock(spec=Request)
            request.cookies = {}

            result = await get_current_user(request, None)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_token_missing_subject(self, test_settings):
        """Test handling token without subject."""
        with patch("app.auth.get_settings", return_value=test_settings):
            # Create token without 'sub' field
            token_data = {
                "role": "admin",
                "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
            }
            token = jwt.encode(
                token_data, test_settings.secret_key, algorithm=test_settings.algorithm
            )

            request = Mock(spec=Request)
            request.cookies = {}

            result = await get_current_user(request, token)
            assert result is None


class TestRequireAuth:
    """Test authentication requirement decorator."""

    @pytest.mark.asyncio
    async def test_require_auth_authenticated_user(self):
        """Test require_auth with authenticated user."""
        request = Mock(spec=Request)
        request.url.path = "/dashboard"

        result = await require_auth(request, "testuser")
        assert result == "testuser"

    @pytest.mark.asyncio
    async def test_require_auth_api_request_no_user(self):
        """Test require_auth with API request and no user."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"

        with pytest.raises(HTTPException) as exc_info:
            await require_auth(request, None)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"

    @pytest.mark.asyncio
    async def test_require_auth_web_request_no_user(self):
        """Test require_auth with web request and no user."""
        request = Mock(spec=Request)
        request.url.path = "/dashboard"

        result = await require_auth(request, None)

        assert isinstance(result, RedirectResponse)
        assert result.status_code == 303
        assert "/login" in str(result.headers["location"])


@pytest.mark.auth
class TestAuthIntegration:
    """Integration tests for authentication flow."""

    def test_login_flow_success(self, client, test_settings):
        """Test complete successful login flow."""
        # Test login page loads
        response = client.get("/login")
        assert response.status_code == 200

        # Test successful login
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

    def test_login_flow_invalid_credentials(self, client):
        """Test login flow with invalid credentials."""
        response = client.post(
            "/login", data={"username": "wrong_user", "password": "wrong_pass"}
        )

        # Should return login page with error
        assert response.status_code == 401
        assert "Invalid username or password" in response.text

    def test_protected_endpoint_without_auth(self, client):
        """Test accessing protected endpoint without authentication."""
        response = client.get("/dashboard")

        # Should redirect to login
        assert response.status_code == 200  # TestClient follows redirects
        assert "login" in response.url.path.lower()

    def test_protected_api_without_auth(self, client):
        """Test accessing protected API endpoint without authentication."""
        response = client.get("/api/tests/status")

        # Should return 401
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_protected_endpoint_with_auth(self, authenticated_client):
        """Test accessing protected endpoint with authentication."""
        response = authenticated_client.get("/dashboard")
        assert response.status_code == 200
        assert "dashboard" in response.text.lower()

    def test_logout_flow(self, authenticated_client):
        """Test logout functionality."""
        # Access dashboard to confirm we're logged in
        response = authenticated_client.get("/dashboard")
        assert response.status_code == 200

        # Logout
        response = authenticated_client.get("/logout")
        assert response.status_code == 303
        assert "/login" in response.headers["location"]

        # Cookie should be cleared
        # Note: TestClient doesn't automatically handle cookie deletion
