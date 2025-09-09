"""
Unit tests for health checking system.

Tests comprehensive health checks, endpoints, and monitoring functionality.
"""

import pytest
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime, timedelta

from app.health import HealthChecker, HealthStatus, HealthCheck, health_checker


class TestHealthCheck:
    """Test individual HealthCheck class."""
    
    def test_health_check_creation(self):
        """Test HealthCheck instance creation."""
        async def dummy_check():
            return {"status": "healthy"}
        
        check = HealthCheck(
            name="test_check",
            check_function=dummy_check,
            critical=True,
            timeout=10,
            description="Test check"
        )
        
        assert check.name == "test_check"
        assert check.critical is True
        assert check.timeout == 10
        assert check.description == "Test check"
        assert check.last_run is None
        assert check.last_result is None
        assert check.consecutive_failures == 0


class TestHealthChecker:
    """Test HealthChecker main class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.health_checker = HealthChecker()
    
    def test_health_checker_initialization(self):
        """Test HealthChecker initialization."""
        assert isinstance(self.health_checker.checks, dict)
        assert len(self.health_checker.checks) > 0
        assert self.health_checker.startup_time is not None
        assert isinstance(self.health_checker.startup_time, datetime)
    
    def test_default_checks_registered(self):
        """Test that default health checks are registered."""
        expected_checks = [
            "application_startup",
            "configuration",
            "memory_usage",
            "disk_space",
            "database_connectivity",
            "external_dependencies"
        ]
        
        for check_name in expected_checks:
            assert check_name in self.health_checker.checks
            assert isinstance(self.health_checker.checks[check_name], HealthCheck)
    
    def test_register_custom_check(self):
        """Test registering custom health check."""
        async def custom_check():
            return {"status": HealthStatus.HEALTHY.value}
        
        self.health_checker.register_check(
            "custom_test",
            custom_check,
            critical=True,
            timeout=5,
            description="Custom test check"
        )
        
        assert "custom_test" in self.health_checker.checks
        check = self.health_checker.checks["custom_test"]
        assert check.name == "custom_test"
        assert check.critical is True
        assert check.timeout == 5
        assert check.description == "Custom test check"
    
    @pytest.mark.asyncio
    async def test_run_successful_check(self):
        """Test running a successful health check."""
        async def success_check():
            return {"status": HealthStatus.HEALTHY.value, "test": "passed"}
        
        self.health_checker.register_check("success_test", success_check)
        result = await self.health_checker.run_check("success_test")
        
        assert result["status"] == HealthStatus.HEALTHY.value
        assert result["test"] == "passed"
        assert "timestamp" in result
        assert "duration_seconds" in result
        assert result["check_name"] == "success_test"
        assert result["critical"] is False
    
    @pytest.mark.asyncio
    async def test_run_failing_check(self):
        """Test running a failing health check."""
        async def failing_check():
            raise Exception("Test failure")
        
        self.health_checker.register_check("failing_test", failing_check)
        result = await self.health_checker.run_check("failing_test")
        
        assert result["status"] == HealthStatus.UNHEALTHY.value
        assert "Test failure" in result["error"]
        assert result["error_type"] == "Exception"
        assert result["check_name"] == "failing_test"
        assert "timestamp" in result
        assert "duration_seconds" in result
    
    @pytest.mark.asyncio
    async def test_run_timeout_check(self):
        """Test health check timeout handling."""
        async def timeout_check():
            await asyncio.sleep(10)  # Will timeout
            return {"status": HealthStatus.HEALTHY.value}
        
        self.health_checker.register_check("timeout_test", timeout_check, timeout=1)
        result = await self.health_checker.run_check("timeout_test")
        
        assert result["status"] == HealthStatus.UNHEALTHY.value
        assert "timed out" in result["error"].lower()
        assert result["duration_seconds"] == 1
        assert result["check_name"] == "timeout_test"
    
    @pytest.mark.asyncio
    async def test_run_unknown_check(self):
        """Test running non-existent health check."""
        result = await self.health_checker.run_check("nonexistent")
        
        assert result["status"] == HealthStatus.UNKNOWN.value
        assert "Unknown health check" in result["error"]
    
    @pytest.mark.asyncio
    async def test_run_all_checks(self):
        """Test running all health checks."""
        # Add a custom check
        async def custom_check():
            return {"status": HealthStatus.HEALTHY.value}
        
        self.health_checker.register_check("all_test", custom_check)
        result = await self.health_checker.run_all_checks()
        
        assert "status" in result
        assert result["status"] in [s.value for s in HealthStatus]
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert "checks_run" in result
        assert "checks" in result
        assert isinstance(result["checks"], dict)
        assert len(result["checks"]) > 0
        
        # Should include our custom check
        assert "all_test" in result["checks"]
    
    @pytest.mark.asyncio
    async def test_run_critical_checks_only(self):
        """Test running only critical health checks."""
        # Add a non-critical check
        async def non_critical_check():
            return {"status": HealthStatus.HEALTHY.value}
        
        self.health_checker.register_check("non_critical", non_critical_check, critical=False)
        
        result = await self.health_checker.run_all_checks(include_non_critical=False)
        
        # Should only include critical checks
        critical_checks = [
            name for name, check in result["checks"].items()
            if check.get("critical", False)
        ]
        
        assert len(critical_checks) > 0
        assert "non_critical" not in result["checks"]
    
    @pytest.mark.asyncio
    async def test_readiness_status(self):
        """Test readiness status check."""
        result = await self.health_checker.get_readiness_status()
        
        assert "ready" in result
        assert isinstance(result["ready"], bool)
        assert "status" in result
        assert "timestamp" in result
        assert "critical_checks" in result
    
    @pytest.mark.asyncio
    async def test_liveness_status(self):
        """Test liveness status check."""
        result = await self.health_checker.get_liveness_status()
        
        assert "alive" in result
        assert isinstance(result["alive"], bool)
        assert "status" in result
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert "version" in result


class TestDefaultHealthChecks:
    """Test default health check implementations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.health_checker = HealthChecker()
    
    @pytest.mark.asyncio
    async def test_application_startup_check(self):
        """Test application startup health check."""
        result = await self.health_checker._check_application_startup()
        
        assert result["status"] == HealthStatus.HEALTHY.value
        assert "uptime_seconds" in result
        assert result["uptime_seconds"] >= 0
    
    @pytest.mark.asyncio
    async def test_configuration_check_default(self):
        """Test configuration health check with default settings."""
        result = await self.health_checker._check_configuration()
        
        assert "status" in result
        # Default configuration might have issues, so could be DEGRADED
        assert result["status"] in [HealthStatus.HEALTHY.value, HealthStatus.DEGRADED.value]
    
    @pytest.mark.asyncio
    async def test_configuration_check_secure(self):
        """Test configuration check with secure settings."""
        with patch('app.health.get_settings') as mock_settings:
            mock_settings.return_value.secret_key = "very-secure-secret-key-for-production"
            mock_settings.return_value.auth_username = "secure_admin"
            mock_settings.return_value.auth_password = "secure_password"
            
            result = await self.health_checker._check_configuration()
            
            assert result["status"] == HealthStatus.HEALTHY.value
            assert result["configuration_validated"] is True
    
    @pytest.mark.asyncio
    async def test_configuration_check_insecure(self):
        """Test configuration check with insecure settings."""
        with patch('app.health.get_settings') as mock_settings:
            mock_settings.return_value.secret_key = "change-in-production"
            mock_settings.return_value.auth_username = "admin"
            mock_settings.return_value.auth_password = "changeme"
            
            result = await self.health_checker._check_configuration()
            
            assert result["status"] == HealthStatus.DEGRADED.value
            assert "issues" in result
            assert len(result["issues"]) > 0
    
    @pytest.mark.asyncio
    async def test_memory_usage_check(self):
        """Test memory usage health check."""
        result = await self.health_checker._check_memory_usage()
        
        assert "status" in result
        assert result["status"] in [s.value for s in HealthStatus]
        
        if result["status"] != HealthStatus.UNKNOWN.value:
            assert "system_memory_percent" in result
            assert "process_memory_mb" in result
            assert "available_memory_mb" in result
            assert isinstance(result["system_memory_percent"], (int, float))
            assert isinstance(result["process_memory_mb"], (int, float))
    
    @pytest.mark.asyncio
    async def test_disk_space_check(self):
        """Test disk space health check."""
        result = await self.health_checker._check_disk_space()
        
        assert "status" in result
        assert result["status"] in [s.value for s in HealthStatus]
        
        if result["status"] != HealthStatus.UNKNOWN.value:
            assert "disk_used_percent" in result
            assert "available_gb" in result
            assert isinstance(result["disk_used_percent"], (int, float))
            assert isinstance(result["available_gb"], (int, float))
    
    @pytest.mark.asyncio
    async def test_database_connectivity_not_configured(self):
        """Test database connectivity when not configured."""
        with patch('app.health.get_settings') as mock_settings:
            mock_settings.return_value.postgres_host = "localhost"
            
            result = await self.health_checker._check_database_connectivity()
            
            assert result["status"] == HealthStatus.HEALTHY.value
            assert result["skipped"] is True
            assert "not configured" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_database_connectivity_configured(self):
        """Test database connectivity when configured."""
        with patch('app.health.get_settings') as mock_settings:
            mock_settings.return_value.postgres_host = "db.example.com"
            mock_settings.return_value.postgres_user = "user"
            mock_settings.return_value.postgres_password = "pass"
            
            with patch('app.tests.postgres_test_v2.PostgreSQLTestV2') as MockPostgresTest:
                mock_instance = Mock()
                mock_instance.is_configured.return_value = True
                mock_instance.get_connection_params.return_value = {
                    "host": "db.example.com",
                    "user": "user",
                    "password": "pass",
                    "connect_timeout": 5
                }
                MockPostgresTest.return_value = mock_instance
                
                # Mock psycopg2 connection failure
                with patch('psycopg2.connect') as mock_connect:
                    mock_connect.side_effect = Exception("Connection failed")
                    
                    result = await self.health_checker._check_database_connectivity()
                    
                    assert result["status"] == HealthStatus.DEGRADED.value
                    assert result["database_connected"] is False
                    assert "error" in result
    
    @pytest.mark.asyncio
    async def test_external_dependencies_check(self):
        """Test external dependencies health check."""
        result = await self.health_checker._check_external_dependencies()
        
        assert "status" in result
        assert result["status"] in [s.value for s in HealthStatus]
        assert "dependencies" in result
        assert "total_dependencies" in result
        assert "configured_dependencies" in result
        
        # Should check for blob storage and cassandra
        assert "azure_blob" in result["dependencies"]
        assert "cassandra" in result["dependencies"]


class TestHealthCheckEndpoints:
    """Test health check API endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_integration(self, client):
        """Test /health endpoint integration."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "checks" in data
        assert "version" in data
        assert "application" in data
    
    @pytest.mark.asyncio
    async def test_liveness_endpoint(self, client):
        """Test /health/live endpoint."""
        response = client.get("/health/live")
        assert response.status_code in [200, 503]  # Could be unhealthy
        
        data = response.json()
        assert "alive" in data
        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "version" in data
        
        if response.status_code == 200:
            assert data["alive"] is True
        else:
            assert data["alive"] is False
    
    @pytest.mark.asyncio
    async def test_readiness_endpoint(self, client):
        """Test /health/ready endpoint."""
        response = client.get("/health/ready")
        assert response.status_code in [200, 503]  # Could be not ready
        
        data = response.json()
        assert "ready" in data
        assert "status" in data
        assert "timestamp" in data
        assert "critical_checks" in data
        
        if response.status_code == 200:
            assert data["ready"] is True
        else:
            assert data["ready"] is False


class TestHealthCheckConsistency:
    """Test health check consistency and reliability."""
    
    def setup_method(self):
        """Set up test environment."""
        self.health_checker = HealthChecker()
    
    @pytest.mark.asyncio
    async def test_consecutive_failure_tracking(self):
        """Test that consecutive failures are tracked."""
        async def intermittent_check():
            # This will fail
            raise Exception("Intermittent failure")
        
        self.health_checker.register_check("intermittent", intermittent_check)
        
        # First failure
        result1 = await self.health_checker.run_check("intermittent")
        assert result1["consecutive_failures"] == 1
        
        # Second failure
        result2 = await self.health_checker.run_check("intermittent")
        assert result2["consecutive_failures"] == 2
    
    @pytest.mark.asyncio
    async def test_failure_reset_on_success(self):
        """Test that consecutive failures reset on success."""
        call_count = 0
        
        async def flaky_check():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Flaky failure")
            return {"status": HealthStatus.HEALTHY.value}
        
        self.health_checker.register_check("flaky", flaky_check)
        
        # First two calls fail
        await self.health_checker.run_check("flaky")
        await self.health_checker.run_check("flaky")
        
        # Third call succeeds
        result = await self.health_checker.run_check("flaky")
        assert result["status"] == HealthStatus.HEALTHY.value
        
        # Consecutive failures should be reset
        check = self.health_checker.checks["flaky"]
        assert check.consecutive_failures == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Test running health checks concurrently."""
        async def slow_check():
            await asyncio.sleep(0.1)
            return {"status": HealthStatus.HEALTHY.value}
        
        # Register multiple slow checks
        for i in range(5):
            self.health_checker.register_check(f"slow_{i}", slow_check)
        
        # Run all checks concurrently
        start_time = asyncio.get_event_loop().time()
        result = await self.health_checker.run_all_checks()
        end_time = asyncio.get_event_loop().time()
        
        # Should complete in reasonable time (concurrent execution)
        total_time = end_time - start_time
        assert total_time < 1.0  # Much faster than sequential execution
        
        # All checks should have completed
        assert len(result["checks"]) >= 5


@pytest.mark.integration
class TestHealthCheckIntegration:
    """Integration tests for health checking system."""
    
    @pytest.mark.asyncio
    async def test_global_health_checker_instance(self):
        """Test global health checker instance."""
        from app.health import health_checker
        
        assert isinstance(health_checker, HealthChecker)
        assert len(health_checker.checks) > 0
        
        # Should be able to run checks
        result = await health_checker.get_liveness_status()
        assert "alive" in result
    
    @pytest.mark.asyncio
    async def test_health_check_with_real_config(self):
        """Test health checks with real configuration."""
        result = await health_checker.run_all_checks()
        
        # Should have all expected checks
        expected_checks = [
            "application_startup",
            "configuration", 
            "memory_usage",
            "disk_space",
            "database_connectivity",
            "external_dependencies"
        ]
        
        for check_name in expected_checks:
            assert check_name in result["checks"]
        
        # Overall status should be valid
        assert result["status"] in [s.value for s in HealthStatus]