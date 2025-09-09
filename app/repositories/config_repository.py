"""
Repository for managing configuration data persistence.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base_repository import InMemoryRepository


class ConfigRepository(InMemoryRepository):
    """Repository for managing configuration data."""

    @property
    def repository_name(self) -> str:
        return "ConfigRepository"

    async def initialize(self) -> None:
        """Initialize the config repository."""
        await super().initialize()

        # Initialize data structures
        if "configurations" not in self.data:
            await self.store_data("configurations", {})
        if "config_history" not in self.data:
            await self.store_data("config_history", [])

    async def get_config(self, key: str) -> Optional[Any]:
        """
        Get a configuration value by key.

        Args:
            key: Configuration key

        Returns:
            Configuration value or None if not found
        """
        configurations = await self.get_data("configurations") or {}
        config_item = configurations.get(key)

        if config_item:
            return config_item.get("value")

        return None

    async def set_config(
        self,
        key: str,
        value: Any,
        user_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
            user_id: User making the change
            description: Optional description of the change
        """
        configurations = await self.get_data("configurations") or {}

        # Store old value for history
        old_value = configurations.get(key, {}).get("value")

        # Update configuration
        config_item = {
            "key": key,
            "value": value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user_id,
            "description": description,
        }

        configurations[key] = config_item
        await self.store_data("configurations", configurations)

        # Record in history
        await self._record_config_change(key, old_value, value, user_id, "set")

        self.log_operation(
            "set_config",
            {"key": key, "user_id": user_id, "has_old_value": old_value is not None},
        )

    async def delete_config(self, key: str, user_id: Optional[str] = None) -> bool:
        """
        Delete a configuration value.

        Args:
            key: Configuration key to delete
            user_id: User making the change

        Returns:
            True if configuration was deleted, False if not found
        """
        configurations = await self.get_data("configurations") or {}

        if key in configurations:
            old_value = configurations[key].get("value")
            del configurations[key]
            await self.store_data("configurations", configurations)

            # Record in history
            await self._record_config_change(key, old_value, None, user_id, "delete")

            self.log_operation("delete_config", {"key": key, "user_id": user_id})
            return True

        return False

    async def list_configurations(
        self, prefix: Optional[str] = None, include_values: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List all configurations with optional filtering.

        Args:
            prefix: Filter by key prefix
            include_values: Whether to include actual values

        Returns:
            List of configuration dictionaries
        """
        configurations = await self.get_data("configurations") or {}
        config_list = []

        for key, config_item in configurations.items():
            if prefix and not key.startswith(prefix):
                continue

            config_dict = {
                "key": key,
                "updated_at": config_item.get("updated_at"),
                "updated_by": config_item.get("updated_by"),
                "description": config_item.get("description"),
            }

            if include_values:
                config_dict["value"] = config_item.get("value")

            config_list.append(config_dict)

        # Sort by key name
        config_list.sort(key=lambda x: x["key"])

        self.log_operation(
            "list_configurations",
            {
                "prefix": prefix,
                "include_values": include_values,
                "count": len(config_list),
            },
        )

        return config_list

    async def get_config_history(
        self, key: Optional[str] = None, user_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get configuration change history.

        Args:
            key: Filter by specific configuration key
            user_id: Filter by specific user
            limit: Maximum number of records to return

        Returns:
            List of configuration change records
        """
        history = await self.get_data("config_history") or []

        # Apply filters
        filtered_history = []
        for record in history:
            if key and record.get("key") != key:
                continue
            if user_id and record.get("user_id") != user_id:
                continue

            filtered_history.append(record)

        # Sort by timestamp (newest first) and limit
        filtered_history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        self.log_operation(
            "get_config_history",
            {
                "key": key,
                "user_id": user_id,
                "limit": limit,
                "results_count": len(filtered_history[:limit]),
            },
        )

        return filtered_history[:limit]

    async def backup_configurations(self) -> Dict[str, Any]:
        """
        Create a backup of all configurations.

        Returns:
            Dictionary with backup data and metadata
        """
        configurations = await self.get_data("configurations") or {}

        backup = {
            "backup_timestamp": datetime.now(timezone.utc).isoformat(),
            "configuration_count": len(configurations),
            "configurations": configurations.copy(),
        }

        self.log_operation(
            "backup_configurations", {"configuration_count": len(configurations)}
        )

        return backup

    async def restore_configurations(
        self,
        backup_data: Dict[str, Any],
        user_id: Optional[str] = None,
        overwrite_existing: bool = False,
    ) -> Dict[str, Any]:
        """
        Restore configurations from backup.

        Args:
            backup_data: Backup data to restore
            user_id: User performing the restore
            overwrite_existing: Whether to overwrite existing configurations

        Returns:
            Dictionary with restore results
        """
        if "configurations" not in backup_data:
            raise ValueError("Invalid backup data: missing 'configurations' key")

        current_configurations = await self.get_data("configurations") or {}
        backup_configurations = backup_data["configurations"]

        restored_count = 0
        skipped_count = 0
        overwritten_count = 0

        for key, config_item in backup_configurations.items():
            if key in current_configurations:
                if overwrite_existing:
                    # Record the change in history
                    old_value = current_configurations[key].get("value")
                    new_value = config_item.get("value")
                    await self._record_config_change(
                        key, old_value, new_value, user_id, "restore"
                    )

                    current_configurations[key] = config_item.copy()
                    current_configurations[key]["updated_by"] = user_id
                    current_configurations[key]["updated_at"] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    overwritten_count += 1
                else:
                    skipped_count += 1
                    continue
            else:
                # Record as new configuration
                await self._record_config_change(
                    key, None, config_item.get("value"), user_id, "restore"
                )

                current_configurations[key] = config_item.copy()
                current_configurations[key]["updated_by"] = user_id
                current_configurations[key]["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()
                restored_count += 1

        await self.store_data("configurations", current_configurations)

        result = {
            "restored_count": restored_count,
            "overwritten_count": overwritten_count,
            "skipped_count": skipped_count,
            "total_processed": len(backup_configurations),
            "restore_timestamp": datetime.now(timezone.utc).isoformat(),
            "restored_by": user_id,
        }

        self.log_operation("restore_configurations", result)

        return result

    async def _record_config_change(
        self,
        key: str,
        old_value: Any,
        new_value: Any,
        user_id: Optional[str],
        change_type: str,
    ) -> None:
        """Record a configuration change in history."""
        history = await self.get_data("config_history") or []

        change_record = {
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "user_id": user_id,
            "change_type": change_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        history.append(change_record)

        # Keep only last 1000 history records to prevent memory issues
        if len(history) > 1000:
            history = history[-1000:]

        await self.store_data("config_history", history)

    async def get_config_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about configuration usage.

        Returns:
            Dictionary with configuration statistics
        """
        configurations = await self.get_data("configurations") or {}
        history = await self.get_data("config_history") or []

        # Count configurations by prefix (service categories)
        category_counts = {}
        for key in configurations.keys():
            category = key.split("_")[0] if "_" in key else "other"
            category_counts[category] = category_counts.get(category, 0) + 1

        # Count changes by user
        user_changes = {}
        for record in history:
            user = record.get("user_id", "system")
            user_changes[user] = user_changes.get(user, 0) + 1

        # Recent activity (last 24 hours)
        from datetime import timedelta

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_changes = 0

        for record in history:
            try:
                change_time = datetime.fromisoformat(record.get("timestamp", ""))
                if change_time >= cutoff_time:
                    recent_changes += 1
            except ValueError:
                continue

        stats = {
            "total_configurations": len(configurations),
            "total_changes": len(history),
            "recent_changes_24h": recent_changes,
            "category_breakdown": category_counts,
            "user_activity": user_changes,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        self.log_operation(
            "get_config_statistics",
            {
                "total_configurations": len(configurations),
                "total_changes": len(history),
            },
        )

        return stats

    async def cleanup_old_history(self, days_to_keep: int = 90) -> int:
        """
        Clean up old configuration history.

        Args:
            days_to_keep: Number of days of history to keep

        Returns:
            Number of history records deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        history = await self.get_data("config_history") or []

        # Filter out old history
        kept_history = []
        deleted_count = 0

        for record in history:
            timestamp_str = record.get("timestamp", "")
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if timestamp >= cutoff_date:
                    kept_history.append(record)
                else:
                    deleted_count += 1
            except ValueError:
                # Keep records with invalid timestamps
                kept_history.append(record)

        if deleted_count > 0:
            await self.store_data("config_history", kept_history)

        self.log_operation(
            "cleanup_old_history",
            {
                "days_to_keep": days_to_keep,
                "deleted_count": deleted_count,
                "kept_count": len(kept_history),
            },
        )

        return deleted_count
