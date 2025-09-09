"""
Repository for managing user authentication data.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base_repository import InMemoryRepository


class AuthRepository(InMemoryRepository):
    """Repository for managing user authentication and authorization data."""

    @property
    def repository_name(self) -> str:
        return "AuthRepository"

    async def initialize(self) -> None:
        """Initialize the auth repository with default admin user."""
        await super().initialize()

        # Initialize data structures
        if "users" not in self.data:
            await self.store_data("users", {})
        if "user_sessions" not in self.data:
            await self.store_data("user_sessions", {})
        if "user_activity" not in self.data:
            await self.store_data("user_activity", [])

        # Create default admin user if no users exist
        await self._create_default_admin()

    async def _create_default_admin(self) -> None:
        """Create a default admin user if no users exist."""
        users = await self.get_data("users") or {}

        if not users:
            # Create default admin with a simple password (should be changed)
            import hashlib
            import secrets

            password = "admin123"  # Default password
            salt = secrets.token_hex(16)
            password_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
            ).hex()

            admin_id = str(uuid.uuid4())
            admin_user = {
                "user_id": admin_id,
                "username": "admin",
                "password_hash": password_hash,
                "salt": salt,
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": "system",
                "last_login": None,
                "is_active": True,
            }

            users[admin_id] = admin_user
            await self.store_data("users", users)

            self.logger.info(
                "Created default admin user (username: admin, password: admin123)"
            )

    async def create_user(
        self,
        username: str,
        password_hash: str,
        salt: str,
        role: str = "user",
        created_by: Optional[str] = None,
    ) -> str:
        """
        Create a new user.

        Args:
            username: Unique username
            password_hash: Hashed password
            salt: Password salt
            role: User role
            created_by: User ID who created this user

        Returns:
            New user ID

        Raises:
            ValueError: If username already exists
        """
        users = await self.get_data("users") or {}

        # Check if username already exists
        for user in users.values():
            if user["username"] == username:
                raise ValueError(f"Username '{username}' already exists")

        user_id = str(uuid.uuid4())
        user_data = {
            "user_id": user_id,
            "username": username,
            "password_hash": password_hash,
            "salt": salt,
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": created_by,
            "last_login": None,
            "is_active": True,
        }

        users[user_id] = user_data
        await self.store_data("users", users)

        self.log_operation(
            "create_user",
            {
                "user_id": user_id,
                "username": username,
                "role": role,
                "created_by": created_by,
            },
        )

        return user_id

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID.

        Args:
            user_id: User identifier

        Returns:
            User dictionary or None if not found
        """
        users = await self.get_data("users") or {}
        user = users.get(user_id)

        if user and user.get("is_active", True):
            return user.copy()  # Return copy to prevent modification

        return None

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user by username.

        Args:
            username: Username to search for

        Returns:
            User dictionary or None if not found
        """
        users = await self.get_data("users") or {}

        for user in users.values():
            if user["username"] == username and user.get("is_active", True):
                return user.copy()  # Return copy to prevent modification

        return None

    async def update_last_login(self, user_id: str) -> bool:
        """
        Update user's last login timestamp.

        Args:
            user_id: User identifier

        Returns:
            True if updated, False if user not found
        """
        users = await self.get_data("users") or {}

        if user_id in users:
            users[user_id]["last_login"] = datetime.now(timezone.utc).isoformat()
            await self.store_data("users", users)

            self.log_operation("update_last_login", {"user_id": user_id})
            return True

        return False

    async def update_password(
        self, user_id: str, password_hash: str, salt: str
    ) -> bool:
        """
        Update user's password.

        Args:
            user_id: User identifier
            password_hash: New hashed password
            salt: New password salt

        Returns:
            True if updated, False if user not found
        """
        users = await self.get_data("users") or {}

        if user_id in users:
            users[user_id]["password_hash"] = password_hash
            users[user_id]["salt"] = salt
            users[user_id]["password_updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()
            await self.store_data("users", users)

            self.log_operation("update_password", {"user_id": user_id})
            return True

        return False

    async def update_user_role(self, user_id: str, role: str, updated_by: str) -> bool:
        """
        Update user's role.

        Args:
            user_id: User identifier
            role: New user role
            updated_by: User ID making the change

        Returns:
            True if updated, False if user not found
        """
        users = await self.get_data("users") or {}

        if user_id in users:
            old_role = users[user_id].get("role")
            users[user_id]["role"] = role
            users[user_id]["role_updated_at"] = datetime.now(timezone.utc).isoformat()
            users[user_id]["role_updated_by"] = updated_by
            await self.store_data("users", users)

            self.log_operation(
                "update_user_role",
                {
                    "user_id": user_id,
                    "old_role": old_role,
                    "new_role": role,
                    "updated_by": updated_by,
                },
            )
            return True

        return False

    async def deactivate_user(self, user_id: str, deactivated_by: str) -> bool:
        """
        Deactivate a user account.

        Args:
            user_id: User identifier
            deactivated_by: User ID making the change

        Returns:
            True if deactivated, False if user not found
        """
        users = await self.get_data("users") or {}

        if user_id in users and users[user_id].get("is_active", True):
            users[user_id]["is_active"] = False
            users[user_id]["deactivated_at"] = datetime.now(timezone.utc).isoformat()
            users[user_id]["deactivated_by"] = deactivated_by
            await self.store_data("users", users)

            # Also clear any active sessions
            await self._clear_user_sessions(user_id)

            self.log_operation(
                "deactivate_user",
                {"user_id": user_id, "deactivated_by": deactivated_by},
            )
            return True

        return False

    async def list_users(
        self, include_inactive: bool = False, role_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all users with optional filtering.

        Args:
            include_inactive: Whether to include deactivated users
            role_filter: Filter by specific role

        Returns:
            List of user dictionaries (without password data)
        """
        users = await self.get_data("users") or {}
        user_list = []

        for user in users.values():
            # Filter inactive users
            if not include_inactive and not user.get("is_active", True):
                continue

            # Filter by role
            if role_filter and user.get("role") != role_filter:
                continue

            # Remove sensitive data
            safe_user = {
                "user_id": user["user_id"],
                "username": user["username"],
                "role": user.get("role", "user"),
                "created_at": user["created_at"],
                "last_login": user.get("last_login"),
                "is_active": user.get("is_active", True),
            }

            user_list.append(safe_user)

        # Sort by creation date (newest first)
        user_list.sort(key=lambda x: x["created_at"], reverse=True)

        self.log_operation(
            "list_users",
            {
                "include_inactive": include_inactive,
                "role_filter": role_filter,
                "user_count": len(user_list),
            },
        )

        return user_list

    async def record_user_activity(
        self, user_id: str, activity_type: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record user activity for auditing.

        Args:
            user_id: User identifier
            activity_type: Type of activity (login, logout, test_run, etc.)
            details: Additional activity details
        """
        activity = await self.get_data("user_activity") or []

        activity_record = {
            "user_id": user_id,
            "activity_type": activity_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        }

        activity.append(activity_record)

        # Keep only last 10000 activity records to prevent memory issues
        if len(activity) > 10000:
            activity = activity[-10000:]

        await self.store_data("user_activity", activity)

        self.log_operation(
            "record_user_activity", {"user_id": user_id, "activity_type": activity_type}
        )

    async def get_user_activity(
        self,
        user_id: Optional[str] = None,
        activity_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get user activity records with optional filtering.

        Args:
            user_id: Filter by specific user
            activity_type: Filter by specific activity type
            limit: Maximum number of records to return

        Returns:
            List of activity records
        """
        activity = await self.get_data("user_activity") or []

        # Apply filters
        filtered_activity = []
        for record in activity:
            if user_id and record.get("user_id") != user_id:
                continue
            if activity_type and record.get("activity_type") != activity_type:
                continue

            filtered_activity.append(record)

        # Sort by timestamp (newest first) and limit
        filtered_activity.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return filtered_activity[:limit]

    async def _clear_user_sessions(self, user_id: str) -> None:
        """Clear all sessions for a user."""
        sessions = await self.get_data("user_sessions") or {}

        # Remove sessions for the user
        sessions_to_remove = [
            session_id
            for session_id, session_data in sessions.items()
            if session_data.get("user_id") == user_id
        ]

        for session_id in sessions_to_remove:
            sessions.pop(session_id, None)

        if sessions_to_remove:
            await self.store_data("user_sessions", sessions)

        self.log_operation(
            "clear_user_sessions",
            {"user_id": user_id, "cleared_sessions": len(sessions_to_remove)},
        )

    async def cleanup_old_activity(self, days_to_keep: int = 90) -> int:
        """
        Clean up old activity records.

        Args:
            days_to_keep: Number of days of activity to keep

        Returns:
            Number of records deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        activity = await self.get_data("user_activity") or []

        # Filter out old activity
        kept_activity = []
        deleted_count = 0

        for record in activity:
            timestamp_str = record.get("timestamp", "")
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if timestamp >= cutoff_date:
                    kept_activity.append(record)
                else:
                    deleted_count += 1
            except ValueError:
                # Keep records with invalid timestamps
                kept_activity.append(record)

        if deleted_count > 0:
            await self.store_data("user_activity", kept_activity)

        self.log_operation(
            "cleanup_old_activity",
            {
                "days_to_keep": days_to_keep,
                "deleted_count": deleted_count,
                "kept_count": len(kept_activity),
            },
        )

        return deleted_count
