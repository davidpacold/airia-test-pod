"""
Base repository class with common data access functionality.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class BaseRepository(ABC):
    """Base class for all repository implementations."""

    def __init__(self):
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        self.initialized = False
        self.connection = None

    @property
    @abstractmethod
    def repository_name(self) -> str:
        """Name of the repository for logging."""
        pass

    @property
    def supports_transactions(self) -> bool:
        """Whether this repository supports database transactions."""
        return False

    async def initialize(self) -> None:
        """
        Initialize the repository connection.
        Override in subclasses to implement specific initialization.
        """
        self.logger.info(f"Initializing {self.repository_name} repository")
        self.initialized = True

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the repository.
        Override in subclasses for specific health checks.
        """
        return {
            "repository": self.repository_name,
            "status": "healthy" if self.initialized else "not_initialized",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "connection_status": "connected" if self.connection else "disconnected",
        }

    async def close(self) -> None:
        """
        Close repository connections and cleanup.
        Override in subclasses to implement cleanup.
        """
        if self.connection:
            self.logger.info(f"Closing {self.repository_name} repository connection")
            # Subclasses should implement actual connection cleanup
            self.connection = None

        self.initialized = False

    def log_operation(self, operation: str, details: Dict[str, Any] = None) -> None:
        """Log a repository operation with structured data."""
        log_data = {
            "repository": self.repository_name,
            "operation": operation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if details:
            log_data.update(details)

        self.logger.debug(f"Repository operation", extra=log_data)

    async def __aenter__(self):
        """Async context manager entry."""
        if not self.initialized:
            await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if exc_type is not None:
            self.logger.error(
                f"Exception in {self.repository_name} repository: {exc_val}"
            )
        return False


class InMemoryRepository(BaseRepository):
    """In-memory repository implementation for testing and simple use cases."""

    def __init__(self):
        super().__init__()
        self.data: Dict[str, Any] = {}

    @property
    def repository_name(self) -> str:
        return "InMemoryRepository"

    async def initialize(self) -> None:
        """Initialize the in-memory storage."""
        await super().initialize()
        self.connection = "memory"  # Mock connection

    async def store_data(self, key: str, data: Any) -> None:
        """Store data by key."""
        self.data[key] = {
            "value": data,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        self.log_operation("store_data", {"key": key})

    async def get_data(self, key: str) -> Optional[Any]:
        """Retrieve data by key."""
        self.log_operation("get_data", {"key": key})
        item = self.data.get(key)
        return item["value"] if item else None

    async def delete_data(self, key: str) -> bool:
        """Delete data by key."""
        existed = key in self.data
        if existed:
            del self.data[key]
        self.log_operation("delete_data", {"key": key, "existed": existed})
        return existed

    async def list_keys(self, prefix: str = None) -> List[str]:
        """List all keys, optionally filtered by prefix."""
        if prefix:
            keys = [k for k in self.data.keys() if k.startswith(prefix)]
        else:
            keys = list(self.data.keys())

        self.log_operation("list_keys", {"prefix": prefix, "count": len(keys)})
        return keys

    async def update_data(self, key: str, data: Any) -> bool:
        """Update existing data by key."""
        if key not in self.data:
            return False

        self.data[key]["value"] = data
        self.data[key]["updated_at"] = datetime.now(timezone.utc)
        self.log_operation("update_data", {"key": key})
        return True

    async def clear_all(self) -> int:
        """Clear all data and return count of deleted items."""
        count = len(self.data)
        self.data.clear()
        self.log_operation("clear_all", {"deleted_count": count})
        return count
