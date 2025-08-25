from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Application settings
    app_name: str = "Airia Infrastructure Test Pod"
    version: str = "1.0.29"
    
    # Authentication settings
    auth_username: str = os.getenv("AUTH_USERNAME", "admin")
    auth_password: str = os.getenv("AUTH_PASSWORD", "changeme")
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
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
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()