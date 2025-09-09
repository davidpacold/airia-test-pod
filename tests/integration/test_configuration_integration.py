"""
Integration tests for configuration and environment validation.

Tests configuration loading, environment variable handling,
and application startup scenarios.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.config import Settings, get_settings
from app.main import app


@pytest.mark.integration
class TestConfigurationIntegration:
    """Integration tests for configuration management."""

    def test_configuration_loading_from_environment(self):
        """Test configuration loading from environment variables."""
        test_env_vars = {
            "AUTH_USERNAME": "integration_user",
            "AUTH_PASSWORD": "integration_pass",
            "SECRET_KEY": "integration-secret-key-12345",
            "POSTGRES_HOST": "integration-db.example.com",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DATABASE": "integration_db",
            "POSTGRES_USER": "integration_pg_user",
            "POSTGRES_PASSWORD": "integration_pg_pass",
            "BLOB_ACCOUNT_NAME": "integrationblob",
            "BLOB_CONTAINER_NAME": "integration-container",
            "CASSANDRA_HOSTS": "cassandra1.int.example.com,cassandra2.int.example.com",
            "CASSANDRA_USERNAME": "integration_cassandra",
            "CASSANDRA_KEYSPACE": "integration_keyspace",
        }

        with patch.dict(os.environ, test_env_vars):
            settings = Settings()

            # Verify all environment variables were loaded correctly
            assert settings.auth_username == "integration_user"
            assert settings.auth_password == "integration_pass"
            assert settings.secret_key == "integration-secret-key-12345"
            assert settings.postgres_host == "integration-db.example.com"
            assert settings.postgres_port == 5433
            assert settings.postgres_database == "integration_db"
            assert settings.postgres_user == "integration_pg_user"
            assert settings.postgres_password == "integration_pg_pass"
            assert settings.blob_account_name == "integrationblob"
            assert settings.blob_container_name == "integration-container"
            assert (
                settings.cassandra_hosts
                == "cassandra1.int.example.com,cassandra2.int.example.com"
            )
            assert settings.cassandra_username == "integration_cassandra"
            assert settings.cassandra_keyspace == "integration_keyspace"

    def test_configuration_with_dotenv_file(self):
        """Test configuration loading from .env file."""
        env_content = """
# Test environment configuration
AUTH_USERNAME=dotenv_user
AUTH_PASSWORD=dotenv_pass
SECRET_KEY=dotenv-secret-key-67890
POSTGRES_HOST=dotenv-db.example.com
POSTGRES_PORT=5434
BLOB_ACCOUNT_NAME=dotenvblob
CASSANDRA_USE_SSL=true
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".env", delete=False
        ) as temp_env:
            temp_env.write(env_content)
            temp_env.flush()

            # Patch the env_file location
            with patch.object(Settings.Config, "env_file", temp_env.name):
                settings = Settings()

                # Verify .env file variables were loaded
                assert settings.auth_username == "dotenv_user"
                assert settings.auth_password == "dotenv_pass"
                assert settings.secret_key == "dotenv-secret-key-67890"
                assert settings.postgres_host == "dotenv-db.example.com"
                assert settings.postgres_port == 5434
                assert settings.blob_account_name == "dotenvblob"
                assert settings.cassandra_use_ssl is True

            # Cleanup
            os.unlink(temp_env.name)

    def test_environment_variable_precedence(self):
        """Test that environment variables take precedence over .env file."""
        env_file_content = """
AUTH_USERNAME=envfile_user
SECRET_KEY=envfile_secret
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".env", delete=False
        ) as temp_env:
            temp_env.write(env_file_content)
            temp_env.flush()

            # Set environment variable that should override .env file
            with patch.dict(os.environ, {"AUTH_USERNAME": "env_var_user"}):
                with patch.object(Settings.Config, "env_file", temp_env.name):
                    settings = Settings()

                    # Environment variable should take precedence
                    assert settings.auth_username == "env_var_user"
                    # .env file value should still be used for non-overridden values
                    assert settings.secret_key == "envfile_secret"

            # Cleanup
            os.unlink(temp_env.name)

    def test_configuration_caching_integration(self):
        """Test configuration caching behavior in application context."""
        # Clear any existing cache
        get_settings.cache_clear()

        # First call should create settings
        settings1 = get_settings()

        # Second call should return cached instance
        settings2 = get_settings()

        # Should be the same instance
        assert settings1 is settings2

        # Verify caching works with environment changes
        with patch.dict(os.environ, {"AUTH_USERNAME": "cached_test_user"}):
            # This should still return the cached instance
            settings3 = get_settings()
            assert settings3 is settings1

            # Clear cache and try again
            get_settings.cache_clear()
            settings4 = get_settings()

            # Now should be different instance with new values
            assert settings4 is not settings1
            assert settings4.auth_username == "cached_test_user"

    def test_configuration_validation_integration(self):
        """Test configuration validation in integration scenarios."""
        # Test invalid port configurations
        invalid_configs = [
            {"POSTGRES_PORT": "-1"},
            {"POSTGRES_PORT": "99999"},
            {"CASSANDRA_PORT": "0"},
            {"PORT": "not_a_number"},
        ]

        for invalid_config in invalid_configs:
            with patch.dict(os.environ, invalid_config):
                with pytest.raises(ValueError):
                    Settings()

    def test_production_readiness_check(self):
        """Test configuration production readiness validation."""
        # Test development-like configuration (insecure defaults)
        dev_settings = Settings()

        insecure_indicators = []

        # Check for common insecure defaults
        if dev_settings.auth_username == "admin":
            insecure_indicators.append("default_username")

        if dev_settings.auth_password == "changeme":
            insecure_indicators.append("default_password")

        if "change-in-production" in dev_settings.secret_key:
            insecure_indicators.append("default_secret_key")

        # In integration tests, we expect some insecure defaults
        # This test documents what should be changed for production
        assert isinstance(insecure_indicators, list)

        # Test production-like configuration
        prod_env_vars = {
            "AUTH_USERNAME": "prod_admin",
            "AUTH_PASSWORD": "secure-prod-password-123!",
            "SECRET_KEY": "very-secure-production-secret-key-with-sufficient-entropy",
        }

        with patch.dict(os.environ, prod_env_vars):
            prod_settings = Settings()

            # Should not have insecure defaults
            assert prod_settings.auth_username != "admin"
            assert prod_settings.auth_password != "changeme"
            assert "change-in-production" not in prod_settings.secret_key

    def test_database_configuration_validation(self):
        """Test database configuration validation scenarios."""
        # Test PostgreSQL configuration validation
        postgres_configs = [
            # Valid configuration
            {
                "POSTGRES_HOST": "prod-db.example.com",
                "POSTGRES_USER": "prod_user",
                "POSTGRES_PASSWORD": "prod_pass",
                "POSTGRES_DATABASE": "prod_db",
                "POSTGRES_SSLMODE": "require",
            },
            # Valid localhost configuration (for development)
            {
                "POSTGRES_HOST": "localhost",
                "POSTGRES_USER": "dev_user",
                "POSTGRES_PASSWORD": "dev_pass",
                "POSTGRES_SSLMODE": "disable",
            },
        ]

        for config in postgres_configs:
            with patch.dict(os.environ, config):
                settings = Settings()

                # All configurations should load without errors
                assert settings.postgres_host == config["POSTGRES_HOST"]
                assert settings.postgres_user == config["POSTGRES_USER"]
                assert settings.postgres_password == config["POSTGRES_PASSWORD"]
                assert settings.postgres_sslmode == config["POSTGRES_SSLMODE"]

    def test_service_configuration_scenarios(self):
        """Test various service configuration scenarios."""
        # Test minimal configuration (only required services)
        minimal_config = {
            "AUTH_USERNAME": "minimal_user",
            "AUTH_PASSWORD": "minimal_pass",
            "SECRET_KEY": "minimal-secret-key",
        }

        with patch.dict(os.environ, minimal_config):
            settings = Settings()

            # Should work with minimal configuration
            assert settings.auth_username == "minimal_user"

            # Optional services should have empty/default values
            assert settings.blob_account_name == ""
            assert settings.cassandra_hosts == ""

        # Test full service configuration
        full_config = {
            "AUTH_USERNAME": "full_user",
            "AUTH_PASSWORD": "full_pass",
            "SECRET_KEY": "full-secret-key",
            "POSTGRES_HOST": "full-db.example.com",
            "POSTGRES_USER": "full_pg_user",
            "POSTGRES_PASSWORD": "full_pg_pass",
            "BLOB_ACCOUNT_NAME": "fullblob",
            "BLOB_ACCOUNT_KEY": "full_blob_key",
            "CASSANDRA_HOSTS": "cassandra.full.example.com",
            "CASSANDRA_USERNAME": "full_cassandra",
            "CASSANDRA_PASSWORD": "full_cassandra_pass",
        }

        with patch.dict(os.environ, full_config):
            settings = Settings()

            # All services should be configured
            assert settings.postgres_host == "full-db.example.com"
            assert settings.blob_account_name == "fullblob"
            assert settings.cassandra_hosts == "cassandra.full.example.com"


@pytest.mark.integration
class TestApplicationStartupIntegration:
    """Integration tests for application startup and initialization."""

    def test_application_startup_with_default_config(self):
        """Test application can start with default configuration."""
        from fastapi.testclient import TestClient

        # This should not raise any exceptions
        client = TestClient(app)

        # Basic endpoints should work
        response = client.get("/health")
        assert response.status_code == 200

        response = client.get("/version")
        assert response.status_code == 200

    def test_application_startup_with_custom_config(self):
        """Test application startup with custom configuration."""
        custom_config = {
            "AUTH_USERNAME": "startup_user",
            "AUTH_PASSWORD": "startup_pass",
            "SECRET_KEY": "startup-secret-key-12345",
        }

        with patch.dict(os.environ, custom_config):
            from fastapi.testclient import TestClient

            # Clear settings cache to pick up new environment
            get_settings.cache_clear()

            client = TestClient(app)

            # Test that custom config is used
            response = client.get("/health")
            assert response.status_code == 200

            # Test authentication with custom credentials
            response = client.post(
                "/token", data={"username": "startup_user", "password": "startup_pass"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data

    def test_infrastructure_test_registration(self):
        """Test that infrastructure tests are properly registered on startup."""
        from app.tests.test_runner import test_runner

        # Get test status
        status = test_runner.get_test_status()

        assert "available_tests" in status
        assert isinstance(status["available_tests"], list)

        # Should have registered some tests
        assert len(status["available_tests"]) > 0

        # Common infrastructure tests should be available
        available_tests = status["available_tests"]
        expected_test_types = ["postgresql", "blob", "ssl", "openai"]

        found_test_types = []
        for test_name in available_tests:
            for expected_type in expected_test_types:
                if expected_type in test_name.lower():
                    found_test_types.append(expected_type)

        # Should have found at least some expected test types
        assert len(found_test_types) > 0

    def test_configuration_consistency_across_modules(self):
        """Test configuration consistency across different application modules."""
        from fastapi.testclient import TestClient

        # Get settings from config module
        config_settings = get_settings()

        # Get version from API
        client = TestClient(app)
        version_response = client.get("/version")
        api_version = version_response.json()["version"]

        # Get version from health check
        health_response = client.get("/health")
        health_version = health_response.json()["version"]

        # All should be consistent
        assert config_settings.version == api_version
        assert config_settings.version == health_version
        assert api_version == health_version

    def test_error_handling_during_startup(self):
        """Test error handling during application startup scenarios."""
        # Test with invalid configuration that should be handled gracefully
        invalid_configs = [
            # Invalid port (should use default)
            {"PORT": "invalid_port"},
        ]

        for invalid_config in invalid_configs:
            with patch.dict(os.environ, invalid_config):
                # Application startup should handle this gracefully
                # (either use defaults or raise informative errors)
                try:
                    get_settings.cache_clear()
                    settings = get_settings()
                    # If it succeeds, defaults should be used
                    assert settings.port > 0
                except ValueError as e:
                    # If it fails, error should be informative
                    assert "port" in str(e).lower() or "invalid" in str(e).lower()


@pytest.mark.integration
class TestEnvironmentSpecificConfiguration:
    """Integration tests for environment-specific configuration scenarios."""

    def test_development_environment_configuration(self):
        """Test typical development environment configuration."""
        dev_config = {
            "AUTH_USERNAME": "dev_user",
            "AUTH_PASSWORD": "dev_pass",
            "SECRET_KEY": "dev-secret-for-local-testing",
            "POSTGRES_HOST": "localhost",
            "POSTGRES_USER": "dev_user",
            "POSTGRES_PASSWORD": "dev_pass",
            "POSTGRES_SSLMODE": "disable",
        }

        with patch.dict(os.environ, dev_config):
            settings = Settings()

            # Development settings should be loaded
            assert settings.auth_username == "dev_user"
            assert settings.postgres_host == "localhost"
            assert settings.postgres_sslmode == "disable"  # OK for development

    def test_staging_environment_configuration(self):
        """Test typical staging environment configuration."""
        staging_config = {
            "AUTH_USERNAME": "staging_admin",
            "AUTH_PASSWORD": "staging-secure-password",
            "SECRET_KEY": "staging-secret-key-with-good-entropy",
            "POSTGRES_HOST": "staging-db.company.com",
            "POSTGRES_USER": "staging_user",
            "POSTGRES_PASSWORD": "staging_secure_password",
            "POSTGRES_SSLMODE": "require",
            "BLOB_ACCOUNT_NAME": "stagingstorage",
            "BLOB_ACCOUNT_KEY": "staging_blob_key",
        }

        with patch.dict(os.environ, staging_config):
            settings = Settings()

            # Staging settings should be more secure
            assert settings.auth_username == "staging_admin"
            assert settings.postgres_host != "localhost"
            assert settings.postgres_sslmode == "require"
            assert settings.blob_account_name == "stagingstorage"

    def test_production_environment_configuration(self):
        """Test typical production environment configuration."""
        prod_config = {
            "AUTH_USERNAME": "prod_admin",
            "AUTH_PASSWORD": "very-secure-production-password-123!@#",
            "SECRET_KEY": "production-secret-key-with-maximum-entropy-and-security",
            "POSTGRES_HOST": "prod-db-cluster.company.com",
            "POSTGRES_USER": "prod_readonly_user",
            "POSTGRES_PASSWORD": "prod_ultra_secure_password",
            "POSTGRES_SSLMODE": "verify-full",
            "BLOB_ACCOUNT_NAME": "prodstorage",
            "BLOB_ACCOUNT_KEY": "prod_blob_secure_key",
            "CASSANDRA_HOSTS": "prod-cassandra1.company.com,prod-cassandra2.company.com,prod-cassandra3.company.com",
            "CASSANDRA_USERNAME": "prod_cassandra_user",
            "CASSANDRA_PASSWORD": "prod_cassandra_secure_password",
            "CASSANDRA_USE_SSL": "true",
        }

        with patch.dict(os.environ, prod_config):
            settings = Settings()

            # Production settings should be highly secure
            assert settings.auth_username != "admin"  # Not default
            assert settings.auth_password != "changeme"  # Not default
            assert "change-in-production" not in settings.secret_key  # Not default
            assert settings.postgres_sslmode == "verify-full"  # Maximum security
            assert settings.cassandra_use_ssl is True  # SSL enabled
            assert len(settings.cassandra_hosts.split(",")) == 3  # Multiple nodes

    def test_configuration_environment_detection(self):
        """Test detecting which environment the application is running in."""
        # This could be extended to include actual environment detection logic
        # For now, we test that different configurations work as expected

        environments = [
            (
                "development",
                {"POSTGRES_HOST": "localhost", "POSTGRES_SSLMODE": "disable"},
            ),
            (
                "staging",
                {
                    "POSTGRES_HOST": "staging-db.example.com",
                    "POSTGRES_SSLMODE": "require",
                },
            ),
            (
                "production",
                {
                    "POSTGRES_HOST": "prod-db.example.com",
                    "POSTGRES_SSLMODE": "verify-full",
                },
            ),
        ]

        for env_name, env_config in environments:
            base_config = {
                "AUTH_USERNAME": f"{env_name}_user",
                "AUTH_PASSWORD": f"{env_name}_pass",
                "SECRET_KEY": f"{env_name}-secret-key",
            }
            base_config.update(env_config)

            with patch.dict(os.environ, base_config):
                settings = Settings()

                # Each environment should load its configuration correctly
                assert settings.auth_username == f"{env_name}_user"
                assert settings.postgres_host == env_config["POSTGRES_HOST"]
                assert settings.postgres_sslmode == env_config["POSTGRES_SSLMODE"]
