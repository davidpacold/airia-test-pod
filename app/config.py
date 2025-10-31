import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application settings
    app_name: str = "Airia Infrastructure Test Pod"
    version: str = os.getenv("APP_VERSION", "1.0.163")

    # Authentication settings  
    auth_username: str = os.getenv("AUTH_USERNAME") or "admin"
    auth_password: str = os.getenv("AUTH_PASSWORD") or "changeme"
    secret_key: str = os.getenv(
        "SECRET_KEY", "your-secret-key-here-change-in-production"
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Server settings
    port: int = int(os.getenv("PORT", "8080"))

    # PostgreSQL settings
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_database: str = os.getenv("POSTGRES_DATABASE", "postgres")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")
    postgres_sslmode: str = os.getenv("POSTGRES_SSLMODE", "require")

    # Azure Blob Storage settings
    blob_account_name: str = os.getenv("BLOB_ACCOUNT_NAME", "")
    blob_account_key: str = os.getenv("BLOB_ACCOUNT_KEY", "")
    blob_container_name: str = os.getenv("BLOB_CONTAINER_NAME", "test-container")
    blob_endpoint_suffix: str = os.getenv("BLOB_ENDPOINT_SUFFIX", "core.windows.net")

    # Cassandra settings
    cassandra_hosts: str = os.getenv(
        "CASSANDRA_HOSTS", ""
    )  # Comma-separated list of hosts
    cassandra_port: int = int(os.getenv("CASSANDRA_PORT", "9042"))
    cassandra_username: str = os.getenv("CASSANDRA_USERNAME", "")
    cassandra_password: str = os.getenv("CASSANDRA_PASSWORD", "")
    cassandra_keyspace: str = os.getenv("CASSANDRA_KEYSPACE", "")
    cassandra_datacenter: str = os.getenv("CASSANDRA_DATACENTER", "datacenter1")
    cassandra_use_ssl: bool = (os.getenv("CASSANDRA_USE_SSL", "false") or "false").lower() in ("true", "1", "yes", "on")

    # GPU settings
    gpu_required: bool = os.getenv("GPU_REQUIRED", "false").lower() == "true"
    gpu_min_memory_gb: int = int(os.getenv("GPU_MIN_MEMORY_GB", "0"))
    gpu_max_temp_celsius: int = int(os.getenv("GPU_MAX_TEMP_CELSIUS", "85"))

    class Config:
        env_file = ".env"


def get_settings():
    return Settings()
