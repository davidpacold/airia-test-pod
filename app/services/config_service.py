"""
Configuration service for managing application configuration and environment settings.
"""

import os
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from ..exceptions import ConfigurationError, ErrorCode, ValidationError
from ..repositories.config_repository import ConfigRepository
from .base_service import BaseService


class ConfigType(Enum):
    """Configuration value types."""

    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    URL = "url"
    JSON = "json"


@dataclass
class ConfigItem:
    """Configuration item with metadata."""

    key: str
    value: Any
    config_type: ConfigType
    description: str
    is_required: bool = False
    is_secret: bool = False
    default_value: Any = None
    validation_pattern: Optional[str] = None


class ConfigService(BaseService):
    """Service for managing application configuration."""

    def __init__(self, config_repository: Optional[ConfigRepository] = None):
        super().__init__()
        self.repository = config_repository or ConfigRepository()
        self.config_schema = self._define_config_schema()
        self._config_cache: Dict[str, Any] = {}
        self._cache_valid = False

    @property
    def service_name(self) -> str:
        return "ConfigService"

    def _define_config_schema(self) -> Dict[str, ConfigItem]:
        """Define the complete configuration schema for the application."""
        return {
            # Database configurations
            "POSTGRES_HOST": ConfigItem(
                key="POSTGRES_HOST",
                value=None,
                config_type=ConfigType.STRING,
                description="PostgreSQL server hostname",
                is_required=False,
                default_value="localhost",
            ),
            "POSTGRES_PORT": ConfigItem(
                key="POSTGRES_PORT",
                value=None,
                config_type=ConfigType.INTEGER,
                description="PostgreSQL server port",
                is_required=False,
                default_value=5432,
            ),
            "POSTGRES_USER": ConfigItem(
                key="POSTGRES_USER",
                value=None,
                config_type=ConfigType.STRING,
                description="PostgreSQL username",
                is_required=False,
                default_value="postgres",
            ),
            "POSTGRES_PASSWORD": ConfigItem(
                key="POSTGRES_PASSWORD",
                value=None,
                config_type=ConfigType.STRING,
                description="PostgreSQL password",
                is_required=False,
                is_secret=True,
            ),
            "POSTGRES_DATABASE": ConfigItem(
                key="POSTGRES_DATABASE",
                value=None,
                config_type=ConfigType.STRING,
                description="PostgreSQL database name",
                is_required=False,
                default_value="testdb",
            ),
            # Cassandra configurations
            "CASSANDRA_HOSTS": ConfigItem(
                key="CASSANDRA_HOSTS",
                value=None,
                config_type=ConfigType.STRING,
                description="Comma-separated list of Cassandra hosts",
                is_required=False,
            ),
            "CASSANDRA_PORT": ConfigItem(
                key="CASSANDRA_PORT",
                value=None,
                config_type=ConfigType.INTEGER,
                description="Cassandra port",
                is_required=False,
                default_value=9042,
            ),
            "CASSANDRA_USERNAME": ConfigItem(
                key="CASSANDRA_USERNAME",
                value=None,
                config_type=ConfigType.STRING,
                description="Cassandra username",
                is_required=False,
            ),
            "CASSANDRA_PASSWORD": ConfigItem(
                key="CASSANDRA_PASSWORD",
                value=None,
                config_type=ConfigType.STRING,
                description="Cassandra password",
                is_required=False,
                is_secret=True,
            ),
            # Storage configurations
            "AZURE_STORAGE_ACCOUNT_NAME": ConfigItem(
                key="AZURE_STORAGE_ACCOUNT_NAME",
                value=None,
                config_type=ConfigType.STRING,
                description="Azure Storage account name",
                is_required=False,
            ),
            "AZURE_STORAGE_ACCOUNT_KEY": ConfigItem(
                key="AZURE_STORAGE_ACCOUNT_KEY",
                value=None,
                config_type=ConfigType.STRING,
                description="Azure Storage account key",
                is_required=False,
                is_secret=True,
            ),
            "AWS_ACCESS_KEY_ID": ConfigItem(
                key="AWS_ACCESS_KEY_ID",
                value=None,
                config_type=ConfigType.STRING,
                description="AWS access key ID",
                is_required=False,
                is_secret=True,
            ),
            "AWS_SECRET_ACCESS_KEY": ConfigItem(
                key="AWS_SECRET_ACCESS_KEY",
                value=None,
                config_type=ConfigType.STRING,
                description="AWS secret access key",
                is_required=False,
                is_secret=True,
            ),
            "S3_BUCKET_NAME": ConfigItem(
                key="S3_BUCKET_NAME",
                value=None,
                config_type=ConfigType.STRING,
                description="S3 bucket name for testing",
                is_required=False,
            ),
            "S3C_ENDPOINT": ConfigItem(
                key="S3C_ENDPOINT",
                value=None,
                config_type=ConfigType.URL,
                description="S3-compatible storage endpoint URL",
                is_required=False,
            ),
            "S3C_ACCESS_KEY": ConfigItem(
                key="S3C_ACCESS_KEY",
                value=None,
                config_type=ConfigType.STRING,
                description="S3-compatible storage access key",
                is_required=False,
                is_secret=True,
            ),
            "S3C_SECRET_KEY": ConfigItem(
                key="S3C_SECRET_KEY",
                value=None,
                config_type=ConfigType.STRING,
                description="S3-compatible storage secret key",
                is_required=False,
                is_secret=True,
            ),
            # AI/ML configurations
            "OPENAI_API_KEY": ConfigItem(
                key="OPENAI_API_KEY",
                value=None,
                config_type=ConfigType.STRING,
                description="OpenAI API key",
                is_required=False,
                is_secret=True,
            ),
            "LLAMA_API_ENDPOINT": ConfigItem(
                key="LLAMA_API_ENDPOINT",
                value=None,
                config_type=ConfigType.URL,
                description="Llama API endpoint URL",
                is_required=False,
            ),
            "AZURE_OPENAI_ENDPOINT": ConfigItem(
                key="AZURE_OPENAI_ENDPOINT",
                value=None,
                config_type=ConfigType.URL,
                description="Azure OpenAI service endpoint",
                is_required=False,
            ),
            "AZURE_OPENAI_API_KEY": ConfigItem(
                key="AZURE_OPENAI_API_KEY",
                value=None,
                config_type=ConfigType.STRING,
                description="Azure OpenAI API key",
                is_required=False,
                is_secret=True,
            ),
            "DOCUMENT_INTELLIGENCE_ENDPOINT": ConfigItem(
                key="DOCUMENT_INTELLIGENCE_ENDPOINT",
                value=None,
                config_type=ConfigType.URL,
                description="Azure Document Intelligence endpoint",
                is_required=False,
            ),
            "DOCUMENT_INTELLIGENCE_KEY": ConfigItem(
                key="DOCUMENT_INTELLIGENCE_KEY",
                value=None,
                config_type=ConfigType.STRING,
                description="Azure Document Intelligence API key",
                is_required=False,
                is_secret=True,
            ),
            # Dedicated Embedding configurations
            "DEDICATED_EMBEDDING_BASE_URL": ConfigItem(
                key="DEDICATED_EMBEDDING_BASE_URL",
                value=None,
                config_type=ConfigType.URL,
                description="Dedicated embedding endpoint base URL",
                is_required=False,
            ),
            "DEDICATED_EMBEDDING_API_KEY": ConfigItem(
                key="DEDICATED_EMBEDDING_API_KEY",
                value=None,
                config_type=ConfigType.STRING,
                description="Dedicated embedding API key",
                is_required=False,
                is_secret=True,
            ),
            "DEDICATED_EMBEDDING_MODEL": ConfigItem(
                key="DEDICATED_EMBEDDING_MODEL",
                value=None,
                config_type=ConfigType.STRING,
                description="Dedicated embedding model name",
                is_required=False,
            ),
            # Application configurations
            "JWT_SECRET": ConfigItem(
                key="JWT_SECRET",
                value=None,
                config_type=ConfigType.STRING,
                description="Secret key for JWT token signing",
                is_required=True,
                is_secret=True,
            ),
            "LOG_LEVEL": ConfigItem(
                key="LOG_LEVEL",
                value=None,
                config_type=ConfigType.STRING,
                description="Application log level (DEBUG, INFO, WARNING, ERROR)",
                is_required=False,
                default_value="INFO",
            ),
            "API_RATE_LIMIT": ConfigItem(
                key="API_RATE_LIMIT",
                value=None,
                config_type=ConfigType.INTEGER,
                description="API requests per minute limit",
                is_required=False,
                default_value=100,
            ),
        }

    async def initialize(self) -> None:
        """Initialize the config service."""
        await super().initialize()
        await self.repository.initialize()
        await self._load_configuration()

    async def _load_configuration(self) -> None:
        """Load configuration from environment and repository."""
        self._config_cache = {}

        for key, schema_item in self.config_schema.items():
            # First try environment variable
            env_value = os.getenv(key)
            if env_value is not None:
                try:
                    parsed_value = self._parse_config_value(
                        env_value, schema_item.config_type
                    )
                    self._config_cache[key] = parsed_value
                    continue
                except ValueError as e:
                    self.logger.warning(f"Invalid environment value for {key}: {e}")

            # Then try repository (for dynamic config)
            try:
                repo_value = await self.repository.get_config(key)
                if repo_value is not None:
                    self._config_cache[key] = repo_value
                    continue
            except Exception as e:
                self.logger.warning(f"Failed to load {key} from repository: {e}")

            # Finally use default value
            if schema_item.default_value is not None:
                self._config_cache[key] = schema_item.default_value
            elif schema_item.is_required:
                raise ConfigurationError(
                    message=f"Required configuration missing: {key}",
                    error_code=ErrorCode.CONFIG_REQUIRED,
                    service_name=self.service_name,
                    details={
                        "missing_key": key,
                        "description": schema_item.description,
                    },
                    remediation=f"Please set the {key} environment variable or configure it via the API",
                )

        self._cache_valid = True

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on config service."""
        base_health = await super().health_check()

        # Check configuration completeness
        missing_required = []
        configured_optional = 0
        total_optional = 0

        for key, schema_item in self.config_schema.items():
            if schema_item.is_required and key not in self._config_cache:
                missing_required.append(key)
            elif not schema_item.is_required:
                total_optional += 1
                if key in self._config_cache:
                    configured_optional += 1

        base_health.update(
            {
                "cache_valid": self._cache_valid,
                "total_config_items": len(self.config_schema),
                "configured_items": len(self._config_cache),
                "missing_required": len(missing_required),
                "optional_configured": f"{configured_optional}/{total_optional}",
                "repository_status": (
                    "connected" if self.repository.initialized else "disconnected"
                ),
            }
        )

        if missing_required:
            base_health["status"] = "degraded"
            base_health["missing_required_config"] = missing_required

        return base_health

    def _parse_config_value(self, value: str, config_type: ConfigType) -> Any:
        """Parse a configuration value based on its expected type."""
        if config_type == ConfigType.STRING:
            return value
        elif config_type == ConfigType.INTEGER:
            return int(value)
        elif config_type == ConfigType.BOOLEAN:
            return value.lower() in ("true", "1", "yes", "on")
        elif config_type == ConfigType.URL:
            # Basic URL validation
            if not (value.startswith("http://") or value.startswith("https://")):
                raise ValueError("URL must start with http:// or https://")
            return value
        elif config_type == ConfigType.JSON:
            import json

            return json.loads(value)
        else:
            return value

    async def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value
        """
        await self.ensure_initialized()

        if not self._cache_valid:
            await self._load_configuration()

        return self._config_cache.get(key, default)

    async def get_config_schema(self) -> List[Dict[str, Any]]:
        """
        Get the configuration schema for documentation/UI purposes.

        Returns:
            List of configuration items with metadata
        """
        schema_list = []

        for key, schema_item in self.config_schema.items():
            item_dict = asdict(schema_item)
            # Don't expose actual values for security
            item_dict["value"] = (
                "***" if schema_item.is_secret else bool(self._config_cache.get(key))
            )
            item_dict["is_configured"] = key in self._config_cache
            schema_list.append(item_dict)

        return sorted(schema_list, key=lambda x: (not x["is_required"], x["key"]))

    async def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the current configuration and return status.

        Returns:
            Dictionary with validation results
        """
        await self.ensure_initialized()

        results = {
            "valid": True,
            "missing_required": [],
            "invalid_values": [],
            "configured_services": [],
            "missing_optional": [],
        }

        for key, schema_item in self.config_schema.items():
            if schema_item.is_required and key not in self._config_cache:
                results["missing_required"].append(
                    {"key": key, "description": schema_item.description}
                )
                results["valid"] = False
            elif key not in self._config_cache and not schema_item.is_required:
                results["missing_optional"].append(
                    {"key": key, "description": schema_item.description}
                )

        # Categorize configured services
        service_categories = {
            "database": ["POSTGRES_", "CASSANDRA_"],
            "storage": ["AZURE_STORAGE_", "AWS_", "S3_", "S3C_"],
            "ai_ml": ["OPENAI_", "LLAMA_", "AZURE_OPENAI", "DOCUMENT_INTELLIGENCE"],
            "application": ["JWT_", "LOG_", "API_"],
        }

        for category, prefixes in service_categories.items():
            configured_keys = [
                key
                for key in self._config_cache.keys()
                if any(key.startswith(prefix) for prefix in prefixes)
            ]
            if configured_keys:
                results["configured_services"].append(
                    {"category": category, "configured_keys": configured_keys}
                )

        return results

    async def set_config(
        self, key: str, value: Any, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set a configuration value dynamically.

        Args:
            key: Configuration key
            value: Configuration value
            user_id: User making the change

        Returns:
            Dictionary with operation result

        Raises:
            ValidationError: If key is invalid or value is wrong type
        """
        await self.ensure_initialized()

        # Validate key exists in schema
        if key not in self.config_schema:
            raise ValidationError(
                message=f"Unknown configuration key: {key}",
                error_code=ErrorCode.CONFIG_INVALID_KEY,
                field_name="key",
                provided_value=key,
                remediation="Use /api/config/schema to see available configuration keys",
            )

        schema_item = self.config_schema[key]

        # Validate value type
        try:
            parsed_value = self._parse_config_value(str(value), schema_item.config_type)
        except ValueError as e:
            raise ValidationError(
                message=f"Invalid value for {key}: {str(e)}",
                error_code=ErrorCode.CONFIG_INVALID_VALUE,
                field_name="value",
                provided_value=str(value),
                remediation=f"Please provide a valid {schema_item.config_type.value} value",
            )

        try:
            # Store in repository
            await self.repository.set_config(key, parsed_value, user_id)

            # Update cache
            self._config_cache[key] = parsed_value

            self.log_operation(
                "config_updated",
                {"key": key, "user_id": user_id, "is_secret": schema_item.is_secret},
            )

            return {
                "success": True,
                "key": key,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": user_id,
            }

        except Exception as e:
            raise self.handle_service_error("set_config", e, key=key)

    async def delete_config(
        self, key: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete a configuration value (reset to default if required).

        Args:
            key: Configuration key to delete
            user_id: User making the change

        Returns:
            Dictionary with operation result
        """
        await self.ensure_initialized()

        if key not in self.config_schema:
            raise ValidationError(
                message=f"Unknown configuration key: {key}",
                error_code=ErrorCode.CONFIG_INVALID_KEY,
                field_name="key",
                provided_value=key,
                remediation="Use /api/config/schema to see available configuration keys",
            )

        schema_item = self.config_schema[key]

        if schema_item.is_required:
            raise ValidationError(
                message=f"Cannot delete required configuration: {key}",
                error_code=ErrorCode.CONFIG_REQUIRED,
                field_name="key",
                provided_value=key,
                remediation="Required configurations cannot be deleted, only updated",
            )

        try:
            # Remove from repository
            await self.repository.delete_config(key, user_id)

            # Update cache (use default if available)
            if schema_item.default_value is not None:
                self._config_cache[key] = schema_item.default_value
            else:
                self._config_cache.pop(key, None)

            self.log_operation("config_deleted", {"key": key, "user_id": user_id})

            return {
                "success": True,
                "key": key,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "deleted_by": user_id,
                "reverted_to_default": schema_item.default_value is not None,
            }

        except Exception as e:
            raise self.handle_service_error("delete_config", e, key=key)

    async def reload_configuration(self) -> Dict[str, Any]:
        """
        Reload configuration from all sources.

        Returns:
            Dictionary with reload results
        """
        try:
            old_count = len(self._config_cache)
            await self._load_configuration()
            new_count = len(self._config_cache)

            self.log_operation(
                "config_reloaded", {"old_count": old_count, "new_count": new_count}
            )

            return {
                "success": True,
                "reloaded_at": datetime.now(timezone.utc).isoformat(),
                "config_items_before": old_count,
                "config_items_after": new_count,
            }

        except Exception as e:
            raise self.handle_service_error("reload_configuration", e)
