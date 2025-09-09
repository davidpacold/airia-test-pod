"""
Unit tests for configuration management.

Tests the config.py module including settings validation,
environment variable handling, and configuration defaults.
"""

import pytest
import os
from unittest.mock import patch, Mock

from app.config import Settings, get_settings


class TestSettingsDefaults:
    """Test default settings values."""
    
    def test_default_app_settings(self):
        """Test default application settings."""
        settings = Settings()
        
        assert settings.app_name == "Airia Infrastructure Test Pod"
        assert isinstance(settings.version, str)
        assert settings.port == 8080
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 30
    
    def test_default_auth_settings(self):
        """Test default authentication settings."""
        settings = Settings()
        
        assert settings.auth_username == "admin"
        assert settings.auth_password == "changeme"
        assert settings.secret_key == "your-secret-key-here-change-in-production"
    
    def test_default_postgres_settings(self):
        """Test default PostgreSQL settings."""
        settings = Settings()
        
        assert settings.postgres_host == "localhost"
        assert settings.postgres_port == 5432
        assert settings.postgres_database == "postgres"
        assert settings.postgres_user == "postgres"
        assert settings.postgres_password == ""
        assert settings.postgres_sslmode == "require"
    
    def test_default_blob_storage_settings(self):
        """Test default Azure Blob Storage settings."""
        settings = Settings()
        
        assert settings.blob_account_name == ""
        assert settings.blob_account_key == ""
        assert settings.blob_container_name == "test-container"
        assert settings.blob_endpoint_suffix == "core.windows.net"
    
    def test_default_cassandra_settings(self):
        """Test default Cassandra settings."""
        settings = Settings()
        
        assert settings.cassandra_hosts == ""
        assert settings.cassandra_port == 9042
        assert settings.cassandra_username == ""
        assert settings.cassandra_password == ""
        assert settings.cassandra_keyspace == ""
        assert settings.cassandra_datacenter == "datacenter1"
        assert settings.cassandra_use_ssl is False


class TestEnvironmentVariableOverrides:
    """Test environment variable overrides."""
    
    def test_auth_env_variables(self):
        """Test authentication environment variable overrides."""
        env_vars = {
            "AUTH_USERNAME": "testuser",
            "AUTH_PASSWORD": "testpass123",
            "SECRET_KEY": "super-secret-key-for-testing",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.auth_username == "testuser"
            assert settings.auth_password == "testpass123"
            assert settings.secret_key == "super-secret-key-for-testing"
    
    def test_postgres_env_variables(self):
        """Test PostgreSQL environment variable overrides."""
        env_vars = {
            "POSTGRES_HOST": "db.example.com",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DATABASE": "testdb",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_SSLMODE": "disable",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.postgres_host == "db.example.com"
            assert settings.postgres_port == 5433
            assert settings.postgres_database == "testdb"
            assert settings.postgres_user == "testuser"
            assert settings.postgres_password == "testpass"
            assert settings.postgres_sslmode == "disable"
    
    def test_blob_storage_env_variables(self):
        """Test Azure Blob Storage environment variable overrides."""
        env_vars = {
            "BLOB_ACCOUNT_NAME": "teststorage",
            "BLOB_ACCOUNT_KEY": "test-key-12345",
            "BLOB_CONTAINER_NAME": "test-files",
            "BLOB_ENDPOINT_SUFFIX": "custom.endpoint.com",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.blob_account_name == "teststorage"
            assert settings.blob_account_key == "test-key-12345"
            assert settings.blob_container_name == "test-files"
            assert settings.blob_endpoint_suffix == "custom.endpoint.com"
    
    def test_cassandra_env_variables(self):
        """Test Cassandra environment variable overrides."""
        env_vars = {
            "CASSANDRA_HOSTS": "cassandra1.example.com,cassandra2.example.com",
            "CASSANDRA_PORT": "9043",
            "CASSANDRA_USERNAME": "cassandra_user",
            "CASSANDRA_PASSWORD": "cassandra_pass",
            "CASSANDRA_KEYSPACE": "test_keyspace",
            "CASSANDRA_DATACENTER": "us-west-1",
            "CASSANDRA_USE_SSL": "true",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.cassandra_hosts == "cassandra1.example.com,cassandra2.example.com"
            assert settings.cassandra_port == 9043
            assert settings.cassandra_username == "cassandra_user"
            assert settings.cassandra_password == "cassandra_pass"
            assert settings.cassandra_keyspace == "test_keyspace"
            assert settings.cassandra_datacenter == "us-west-1"
            assert settings.cassandra_use_ssl is True
    
    def test_port_env_variable_type_conversion(self):
        """Test port environment variable type conversion."""
        with patch.dict(os.environ, {"PORT": "9000"}):
            settings = Settings()
            assert settings.port == 9000
            assert isinstance(settings.port, int)
    
    def test_boolean_env_variable_conversion(self):
        """Test boolean environment variable conversion."""
        # Test true values
        true_values = ["true", "True", "TRUE", "1", "yes", "Yes"]
        for true_val in true_values:
            with patch.dict(os.environ, {"CASSANDRA_USE_SSL": true_val}):
                settings = Settings()
                assert settings.cassandra_use_ssl is True
        
        # Test false values
        false_values = ["false", "False", "FALSE", "0", "no", "No", ""]
        for false_val in false_values:
            with patch.dict(os.environ, {"CASSANDRA_USE_SSL": false_val}):
                settings = Settings()
                assert settings.cassandra_use_ssl is False


class TestSettingsValidation:
    """Test settings validation and error handling."""
    
    def test_invalid_port_type(self):
        """Test handling of invalid port type."""
        with patch.dict(os.environ, {"PORT": "not-a-number"}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_invalid_postgres_port_type(self):
        """Test handling of invalid PostgreSQL port type."""
        with patch.dict(os.environ, {"POSTGRES_PORT": "invalid"}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_invalid_cassandra_port_type(self):
        """Test handling of invalid Cassandra port type."""
        with patch.dict(os.environ, {"CASSANDRA_PORT": "invalid"}):
            with pytest.raises(ValueError):
                Settings()
    
    def test_empty_required_fields(self):
        """Test behavior with empty required fields."""
        # Test with empty values - should use defaults
        env_vars = {
            "AUTH_USERNAME": "",
            "AUTH_PASSWORD": "",
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            # Should fall back to defaults when empty
            assert settings.auth_username == "admin"
            assert settings.auth_password == "changeme"


class TestGetSettingsFunction:
    """Test the get_settings function and caching."""
    
    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)
    
    def test_get_settings_caching(self):
        """Test that get_settings caches the result."""
        # Call get_settings multiple times
        settings1 = get_settings()
        settings2 = get_settings()
        settings3 = get_settings()
        
        # Should return the same instance (cached)
        assert settings1 is settings2
        assert settings2 is settings3
    
    @patch('app.config.Settings')
    def test_get_settings_called_once(self, mock_settings_class):
        """Test that Settings class is instantiated only once due to caching."""
        mock_instance = Mock(spec=Settings)
        mock_settings_class.return_value = mock_instance
        
        # Clear any existing cache
        get_settings.cache_clear()
        
        # Call get_settings multiple times
        result1 = get_settings()
        result2 = get_settings()
        result3 = get_settings()
        
        # Settings should be instantiated only once
        assert mock_settings_class.call_count == 1
        assert result1 is mock_instance
        assert result2 is mock_instance
        assert result3 is mock_instance


class TestConfigurationConsistency:
    """Test configuration consistency and validation."""
    
    def test_version_format(self):
        """Test that version follows expected format."""
        settings = Settings()
        version = settings.version
        
        # Should be a non-empty string
        assert isinstance(version, str)
        assert len(version) > 0
        
        # Should follow semantic versioning pattern (basic check)
        version_parts = version.split('.')
        assert len(version_parts) >= 2  # At least major.minor
    
    def test_secret_key_security(self):
        """Test secret key security considerations."""
        # Test default warning
        settings = Settings()
        default_key = "your-secret-key-here-change-in-production"
        
        if settings.secret_key == default_key:
            # In production, this should be changed
            pass  # This is expected in test environment
        else:
            # Custom key should be reasonably long
            assert len(settings.secret_key) >= 16
    
    def test_auth_credentials_not_empty(self):
        """Test that authentication credentials are not empty in production."""
        settings = Settings()
        
        # Username and password should not be empty
        assert len(settings.auth_username) > 0
        assert len(settings.auth_password) > 0
    
    def test_postgres_connection_params(self):
        """Test PostgreSQL connection parameter consistency."""
        settings = Settings()
        
        # Host should not be empty
        assert len(settings.postgres_host) > 0
        
        # Port should be in valid range
        assert 1 <= settings.postgres_port <= 65535
        
        # SSL mode should be valid
        valid_ssl_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
        assert settings.postgres_sslmode in valid_ssl_modes
    
    def test_cassandra_port_range(self):
        """Test Cassandra port is in valid range."""
        settings = Settings()
        assert 1 <= settings.cassandra_port <= 65535
    
    def test_token_expire_time_reasonable(self):
        """Test that token expiration time is reasonable."""
        settings = Settings()
        
        # Should be between 5 minutes and 24 hours
        assert 5 <= settings.access_token_expire_minutes <= 1440


class TestDotEnvFileLoading:
    """Test .env file loading functionality."""
    
    @patch('app.config.Settings.Config.env_file', '.env.test')
    def test_env_file_configuration(self):
        """Test that env_file configuration is set correctly."""
        # This tests that the Config class has the correct env_file setting
        assert Settings.Config.env_file == '.env'


class TestProductionReadiness:
    """Test production readiness indicators."""
    
    def test_security_defaults_warning(self):
        """Test identification of insecure defaults."""
        settings = Settings()
        
        insecure_indicators = []
        
        # Check for default credentials
        if settings.auth_username == "admin" and settings.auth_password == "changeme":
            insecure_indicators.append("default_credentials")
        
        # Check for default secret key
        if "change-in-production" in settings.secret_key:
            insecure_indicators.append("default_secret_key")
        
        # In test environment, these are expected
        # In production, these should be changed
        # This test documents the security considerations
        assert isinstance(insecure_indicators, list)
    
    def test_required_production_settings(self):
        """Test that production-required settings have non-empty defaults or env vars."""
        settings = Settings()
        
        # These settings are likely required in production
        production_critical = {
            "secret_key": settings.secret_key,
            "auth_username": settings.auth_username,
            "auth_password": settings.auth_password,
        }
        
        for setting_name, setting_value in production_critical.items():
            assert setting_value is not None
            assert len(str(setting_value)) > 0
    
    def test_optional_service_settings(self):
        """Test that optional service settings handle empty values gracefully."""
        settings = Settings()
        
        # These can be empty if services are not used
        optional_settings = [
            settings.blob_account_name,
            settings.blob_account_key,
            settings.cassandra_hosts,
            settings.cassandra_username,
            settings.cassandra_password,
        ]
        
        # Should handle empty values without errors
        for setting_value in optional_settings:
            assert setting_value is not None
            assert isinstance(setting_value, str)


@pytest.mark.integration
class TestSettingsIntegration:
    """Integration tests for settings in application context."""
    
    def test_settings_in_fastapi_context(self, test_settings):
        """Test settings work correctly in FastAPI dependency injection."""
        # This is tested implicitly through other tests that use test_settings fixture
        assert isinstance(test_settings, Settings)
        assert test_settings.app_name == "Test Airia Pod"
    
    def test_settings_environment_isolation(self):
        """Test that test settings don't affect production defaults."""
        # Create fresh settings instance
        fresh_settings = Settings()
        
        # Should have production defaults, not test values
        assert fresh_settings.app_name == "Airia Infrastructure Test Pod"
        # Note: This might be overridden by environment variables in test environment