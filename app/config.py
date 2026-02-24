import logging
import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_DEFAULT_SECRET_KEY = "your-secret-key-here-change-in-production"


class Settings(BaseSettings):
    app_name: str = "Airia Infrastructure Test Pod"
    app_version: str = "2.0.0"

    auth_username: str = "admin"
    auth_password: str = "changeme"
    secret_key: str = _DEFAULT_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    secure_cookies: bool = True

    debug: bool = False
    port: int = 8080

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "postgres"
    postgres_user: str = "postgres"
    postgres_password: str = ""
    postgres_sslmode: str = "require"

    blob_account_name: str = ""
    blob_account_key: str = ""
    blob_container_name: str = "test-container"
    blob_endpoint_suffix: str = "core.windows.net"

    cassandra_hosts: str = ""
    cassandra_port: int = 9042
    cassandra_username: str = ""
    cassandra_password: str = ""
    cassandra_keyspace: str = ""
    cassandra_datacenter: str = "datacenter1"
    cassandra_use_ssl: bool = False
    cassandra_verify_ssl: bool = True

    gpu_required: bool = False
    gpu_min_memory_gb: int = 0
    gpu_max_temp_celsius: int = 85

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.secret_key == _DEFAULT_SECRET_KEY:
        generated_key = secrets.token_hex(32)
        logger.warning(
            "SECRET_KEY not configured - using randomly generated key. "
            "Sessions will not persist across pod restarts. "
            "Set SECRET_KEY environment variable for persistent sessions."
        )
        settings = settings.model_copy(update={"secret_key": generated_key})
    return settings
