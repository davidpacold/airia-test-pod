"""
Authentication service for managing user authentication and authorization.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from ..exceptions import ErrorCode, ServiceUnavailableError, ValidationError
from ..repositories.auth_repository import AuthRepository
from ..utils.sanitization import InputSanitizer
from .base_service import BaseService


class AuthService(BaseService):
    """Service for handling authentication and authorization."""

    def __init__(self, auth_repository: Optional[AuthRepository] = None):
        super().__init__()
        self.repository = auth_repository or AuthRepository()
        self.jwt_secret = self._generate_jwt_secret()
        self.jwt_algorithm = "HS256"
        self.token_expiry_minutes = 60  # 1 hour default

    @property
    def service_name(self) -> str:
        return "AuthService"

    def _generate_jwt_secret(self) -> str:
        """Generate a secure JWT secret key."""
        import os

        secret = os.getenv("JWT_SECRET")
        if not secret:
            # Generate a random secret if not provided
            secret = secrets.token_urlsafe(32)
            self.logger.warning(
                "JWT_SECRET not set, using generated secret (not persistent)"
            )
        return secret

    async def initialize(self) -> None:
        """Initialize the auth service."""
        await super().initialize()
        await self.repository.initialize()

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on auth service."""
        base_health = await super().health_check()

        base_health.update(
            {
                "repository_status": (
                    "connected" if self.repository.initialized else "disconnected"
                ),
                "jwt_configured": bool(self.jwt_secret),
                "token_expiry_minutes": self.token_expiry_minutes,
            }
        )

        return base_health

    def _hash_password(self, password: str, salt: str = None) -> tuple[str, str]:
        """
        Hash a password with salt.

        Args:
            password: Plain text password
            salt: Optional salt (generates new one if not provided)

        Returns:
            Tuple of (hashed_password, salt)
        """
        if not salt:
            salt = secrets.token_hex(16)

        # Use PBKDF2 for password hashing
        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,  # 100,000 iterations
        )

        return hashed.hex(), salt

    def _verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password to verify
            hashed_password: Stored hash
            salt: Salt used in hashing

        Returns:
            True if password matches, False otherwise
        """
        test_hash, _ = self._hash_password(password, salt)
        return secrets.compare_digest(test_hash, hashed_password)

    def _generate_token(self, user_data: Dict[str, Any]) -> str:
        """
        Generate a JWT token for authenticated user.

        Args:
            user_data: User information to encode in token

        Returns:
            JWT token string
        """
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "role": user_data.get("role", "user"),
            "iat": now,
            "exp": now + timedelta(minutes=self.token_expiry_minutes),
        }

        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def _decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            ValidationError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValidationError(
                message="Token has expired",
                error_code=ErrorCode.AUTH_TOKEN_EXPIRED,
                field_name="token",
                remediation="Please log in again to get a new token",
            )
        except jwt.InvalidTokenError:
            raise ValidationError(
                message="Invalid token",
                error_code=ErrorCode.AUTH_TOKEN_INVALID,
                field_name="token",
                remediation="Please provide a valid authentication token",
            )

    async def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user with username/password.

        Args:
            username: User's username
            password: User's password

        Returns:
            Dictionary with authentication result and token

        Raises:
            ValidationError: If credentials are invalid
        """
        await self.ensure_initialized()

        # Sanitize credentials
        try:
            sanitized_username, sanitized_password = (
                InputSanitizer.sanitize_credentials(username, password)
            )
        except Exception as e:
            raise ValidationError(
                message="Invalid credentials format",
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                field_name="credentials",
                remediation="Please provide valid username and password",
            )

        self.log_operation("authenticate_attempt", {"username": sanitized_username})

        try:
            # Get user from repository
            user_data = await self.repository.get_user_by_username(sanitized_username)

            if not user_data:
                self.log_operation(
                    "authenticate_failed",
                    {"username": sanitized_username, "reason": "user_not_found"},
                )
                raise ValidationError(
                    message="Invalid username or password",
                    error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                    field_name="credentials",
                    remediation="Please check your username and password",
                )

            # Verify password
            if not self._verify_password(
                sanitized_password, user_data["password_hash"], user_data["salt"]
            ):
                self.log_operation(
                    "authenticate_failed",
                    {"username": sanitized_username, "reason": "invalid_password"},
                )
                raise ValidationError(
                    message="Invalid username or password",
                    error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                    field_name="credentials",
                    remediation="Please check your username and password",
                )

            # Generate token
            token = self._generate_token(user_data)

            # Update last login
            await self.repository.update_last_login(user_data["user_id"])

            self.log_operation("authenticate_success", {"username": sanitized_username})

            return {
                "success": True,
                "token": token,
                "user": {
                    "user_id": user_data["user_id"],
                    "username": user_data["username"],
                    "role": user_data.get("role", "user"),
                    "last_login": datetime.now(timezone.utc).isoformat(),
                },
                "expires_at": (
                    datetime.now(timezone.utc)
                    + timedelta(minutes=self.token_expiry_minutes)
                ).isoformat(),
            }

        except Exception as e:
            if isinstance(e, ValidationError):
                raise

            raise self.handle_service_error(
                "authenticate_user", e, username=sanitized_username
            )

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate a JWT token and return user information.

        Args:
            token: JWT token to validate

        Returns:
            Dictionary with user information

        Raises:
            ValidationError: If token is invalid
        """
        await self.ensure_initialized()

        payload = self._decode_token(token)

        # Verify user still exists
        user_data = await self.repository.get_user_by_id(payload["user_id"])
        if not user_data:
            raise ValidationError(
                message="User no longer exists",
                error_code=ErrorCode.AUTH_USER_NOT_FOUND,
                field_name="token",
                remediation="Please log in again",
            )

        return {
            "user_id": payload["user_id"],
            "username": payload["username"],
            "role": payload.get("role", "user"),
            "token_expires_at": datetime.fromtimestamp(payload["exp"]).isoformat(),
        }

    async def refresh_token(self, token: str) -> Dict[str, Any]:
        """
        Refresh an existing JWT token.

        Args:
            token: Current JWT token

        Returns:
            Dictionary with new token information

        Raises:
            ValidationError: If token is invalid
        """
        await self.ensure_initialized()

        # Validate current token
        user_info = await self.validate_token(token)

        # Generate new token
        user_data = await self.repository.get_user_by_id(user_info["user_id"])
        new_token = self._generate_token(user_data)

        self.log_operation("token_refreshed", {"user_id": user_info["user_id"]})

        return {
            "success": True,
            "token": new_token,
            "expires_at": (
                datetime.now(timezone.utc)
                + timedelta(minutes=self.token_expiry_minutes)
            ).isoformat(),
        }

    async def create_user(
        self,
        username: str,
        password: str,
        role: str = "user",
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new user account.

        Args:
            username: Username for new user
            password: Password for new user
            role: User role (default: "user")
            created_by: User ID of admin creating this user

        Returns:
            Dictionary with created user information

        Raises:
            ValidationError: If user creation fails
        """
        await self.ensure_initialized()

        # Sanitize inputs
        sanitized_username, sanitized_password = InputSanitizer.sanitize_credentials(
            username, password
        )

        # Additional password validation
        if len(sanitized_password) < 8:
            raise ValidationError(
                message="Password must be at least 8 characters long",
                error_code=ErrorCode.AUTH_WEAK_PASSWORD,
                field_name="password",
                remediation="Please choose a stronger password",
            )

        # Check if username already exists
        existing_user = await self.repository.get_user_by_username(sanitized_username)
        if existing_user:
            raise ValidationError(
                message="Username already exists",
                error_code=ErrorCode.AUTH_USERNAME_EXISTS,
                field_name="username",
                provided_value=sanitized_username,
                remediation="Please choose a different username",
            )

        # Hash password
        password_hash, salt = self._hash_password(sanitized_password)

        try:
            # Create user
            user_id = await self.repository.create_user(
                username=sanitized_username,
                password_hash=password_hash,
                salt=salt,
                role=role,
                created_by=created_by,
            )

            self.log_operation(
                "user_created",
                {
                    "user_id": user_id,
                    "username": sanitized_username,
                    "role": role,
                    "created_by": created_by,
                },
            )

            return {
                "success": True,
                "user_id": user_id,
                "username": sanitized_username,
                "role": role,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            raise self.handle_service_error(
                "create_user", e, username=sanitized_username
            )

    async def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> Dict[str, Any]:
        """
        Change a user's password.

        Args:
            user_id: ID of user changing password
            old_password: Current password
            new_password: New password

        Returns:
            Dictionary with success status

        Raises:
            ValidationError: If password change fails
        """
        await self.ensure_initialized()

        # Get user data
        user_data = await self.repository.get_user_by_id(user_id)
        if not user_data:
            raise ValidationError(
                message="User not found",
                error_code=ErrorCode.AUTH_USER_NOT_FOUND,
                field_name="user_id",
                remediation="Please provide a valid user ID",
            )

        # Verify old password
        if not self._verify_password(
            old_password, user_data["password_hash"], user_data["salt"]
        ):
            raise ValidationError(
                message="Current password is incorrect",
                error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                field_name="old_password",
                remediation="Please enter your current password correctly",
            )

        # Validate new password
        if len(new_password) < 8:
            raise ValidationError(
                message="New password must be at least 8 characters long",
                error_code=ErrorCode.AUTH_WEAK_PASSWORD,
                field_name="new_password",
                remediation="Please choose a stronger password",
            )

        # Hash new password
        new_hash, new_salt = self._hash_password(new_password)

        try:
            # Update password
            await self.repository.update_password(user_id, new_hash, new_salt)

            self.log_operation("password_changed", {"user_id": user_id})

            return {"success": True, "message": "Password updated successfully"}

        except Exception as e:
            raise self.handle_service_error("change_password", e, user_id=user_id)
