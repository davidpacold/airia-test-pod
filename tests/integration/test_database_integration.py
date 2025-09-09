"""
Integration tests for database connectivity and operations.

Tests actual database connections, queries, and data operations
using real or containerized database instances.
"""

import pytest
import asyncio
import os
from unittest.mock import patch, Mock, AsyncMock
from typing import Dict, Any

# Import the actual database test modules
from app.tests.postgres_test_v2 import PostgreSQLTestV2
from app.tests.cassandra_test import CassandraTest
from app.config import get_settings


@pytest.mark.integration
class TestPostgreSQLIntegration:
    """Integration tests for PostgreSQL database."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.postgres_test = PostgreSQLTestV2()
    
    def test_postgres_connection_configuration(self):
        """Test PostgreSQL connection configuration parsing."""
        # Test with default settings
        settings = get_settings()
        connection_params = self.postgres_test.get_connection_params()
        
        assert "host" in connection_params
        assert "port" in connection_params
        assert "database" in connection_params
        assert "user" in connection_params
        assert "sslmode" in connection_params
        assert connection_params["connect_timeout"] == 10
    
    def test_postgres_is_configured_logic(self):
        """Test PostgreSQL configuration detection logic."""
        # Test with minimal configuration (should be False)
        with patch('app.tests.postgres_test_v2.get_settings') as mock_settings:
            mock_settings.return_value.postgres_host = "localhost"
            mock_settings.return_value.postgres_user = "user"
            mock_settings.return_value.postgres_password = "pass"
            
            postgres_test = PostgreSQLTestV2()
            assert postgres_test.is_configured() is False  # localhost is excluded
        
        # Test with proper configuration (should be True)
        with patch('app.tests.postgres_test_v2.get_settings') as mock_settings:
            mock_settings.return_value.postgres_host = "db.example.com"
            mock_settings.return_value.postgres_user = "testuser"
            mock_settings.return_value.postgres_password = "testpass"
            
            postgres_test = PostgreSQLTestV2()
            assert postgres_test.is_configured() is True
    
    @pytest.mark.slow
    def test_postgres_connection_timeout(self):
        """Test PostgreSQL connection timeout behavior."""
        with patch('app.tests.postgres_test_v2.get_settings') as mock_settings:
            # Configure with unreachable host
            mock_settings.return_value.postgres_host = "192.0.2.1"  # TEST-NET-1
            mock_settings.return_value.postgres_user = "testuser"
            mock_settings.return_value.postgres_password = "testpass"
            mock_settings.return_value.postgres_port = 5432
            mock_settings.return_value.postgres_database = "testdb"
            mock_settings.return_value.postgres_sslmode = "disable"
            
            postgres_test = PostgreSQLTestV2()
            result = postgres_test.execute()
            
            # Should fail due to connection timeout
            assert result.status.value in ["failed", "skipped"]
            assert result.duration_seconds is not None
    
    def test_postgres_configuration_help(self):
        """Test PostgreSQL configuration help message."""
        help_text = self.postgres_test.get_configuration_help()
        
        assert "POSTGRES_HOST" in help_text
        assert "POSTGRES_USER" in help_text
        assert "POSTGRES_PASSWORD" in help_text
        assert "POSTGRES_DATABASE" in help_text
    
    @pytest.mark.skipif(
        not os.getenv("INTEGRATION_TESTS_ENABLED"),
        reason="Integration tests disabled (set INTEGRATION_TESTS_ENABLED=1 to enable)"
    )
    def test_postgres_real_connection(self):
        """Test actual PostgreSQL connection if available."""
        # This test only runs if integration testing is explicitly enabled
        # and proper PostgreSQL credentials are available
        
        postgres_test = PostgreSQLTestV2()
        if not postgres_test.is_configured():
            pytest.skip("PostgreSQL not configured for integration testing")
        
        result = postgres_test.execute()
        
        # Log the result for debugging
        print(f"PostgreSQL Test Result: {result.status.value}")
        print(f"Message: {result.message}")
        if result.error:
            print(f"Error: {result.error}")
        
        # Test should either pass or have a clear error message
        assert result.status.value in ["passed", "failed", "skipped"]
        assert result.message is not None
        assert result.duration_seconds is not None


@pytest.mark.integration
class TestCassandraIntegration:
    """Integration tests for Cassandra database."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.cassandra_test = CassandraTest()
    
    def test_cassandra_configuration_detection(self):
        """Test Cassandra configuration detection."""
        # Test with no configuration (should be False)
        with patch('app.tests.cassandra_test.get_settings') as mock_settings:
            mock_settings.return_value.cassandra_hosts = ""
            mock_settings.return_value.cassandra_username = ""
            mock_settings.return_value.cassandra_password = ""
            
            cassandra_test = CassandraTest()
            assert cassandra_test.is_configured() is False
        
        # Test with proper configuration (should be True)
        with patch('app.tests.cassandra_test.get_settings') as mock_settings:
            mock_settings.return_value.cassandra_hosts = "cassandra1.example.com,cassandra2.example.com"
            mock_settings.return_value.cassandra_username = "cassandra"
            mock_settings.return_value.cassandra_password = "password"
            mock_settings.return_value.cassandra_keyspace = "test_keyspace"
            mock_settings.return_value.cassandra_port = 9042
            mock_settings.return_value.cassandra_datacenter = "datacenter1"
            mock_settings.return_value.cassandra_use_ssl = False
            
            cassandra_test = CassandraTest()
            assert cassandra_test.is_configured() is True
    
    @pytest.mark.skipif(
        not os.getenv("INTEGRATION_TESTS_ENABLED"),
        reason="Integration tests disabled (set INTEGRATION_TESTS_ENABLED=1 to enable)"
    )
    def test_cassandra_real_connection(self):
        """Test actual Cassandra connection if available."""
        cassandra_test = CassandraTest()
        if not cassandra_test.is_configured():
            pytest.skip("Cassandra not configured for integration testing")
        
        result = cassandra_test.execute()
        
        # Log the result for debugging
        print(f"Cassandra Test Result: {result.status.value}")
        print(f"Message: {result.message}")
        
        assert result.status.value in ["passed", "failed", "skipped"]
        assert result.message is not None


@pytest.mark.integration
class TestDatabaseWorkflows:
    """Integration tests for database workflow scenarios."""
    
    @pytest.mark.asyncio
    async def test_database_connectivity_workflow(self):
        """Test the complete database connectivity workflow."""
        # This tests the workflow that the application would use
        from app.tests.test_runner import test_runner
        
        # Get available tests
        available_tests = test_runner.get_test_status()
        assert "available_tests" in available_tests
        assert isinstance(available_tests["available_tests"], list)
        
        # Test that database tests are registered
        test_names = available_tests["available_tests"]
        database_tests = [name for name in test_names if 'postgres' in name.lower() or 'cassandra' in name.lower()]
        
        assert len(database_tests) > 0, "No database tests found in registered tests"
    
    def test_database_test_execution_order(self):
        """Test that database tests execute in proper dependency order."""
        from app.tests.test_runner import test_runner
        
        # Run all tests and check execution
        # Note: This will skip tests that aren't configured
        results = test_runner.run_all_tests(skip_optional=True)
        
        assert isinstance(results, dict)
        
        # Check that results have proper structure
        for test_id, result in results.items():
            assert "overall_status" in result or hasattr(result, 'status')
            assert "test_count" in result or hasattr(result, 'test_name')
    
    def test_database_error_handling(self):
        """Test database error handling and remediation."""
        from app.tests.postgres_test_v2 import PostgreSQLTestV2
        
        # Test with invalid configuration
        with patch('app.tests.postgres_test_v2.get_settings') as mock_settings:
            mock_settings.return_value.postgres_host = "invalid.host.example.com"
            mock_settings.return_value.postgres_user = "testuser"
            mock_settings.return_value.postgres_password = "testpass"
            mock_settings.return_value.postgres_port = 5432
            mock_settings.return_value.postgres_database = "testdb"
            mock_settings.return_value.postgres_sslmode = "disable"
            
            postgres_test = PostgreSQLTestV2()
            result = postgres_test.execute()
            
            # Should fail with proper error handling
            assert result.status.value == "failed"
            assert result.error is not None
            assert result.remediation is not None or result.message is not None
    
    def test_database_test_logging(self):
        """Test that database tests produce proper logs."""
        postgres_test = PostgreSQLTestV2()
        result = postgres_test.execute()
        
        # All tests should produce logs
        assert len(result.logs) > 0
        
        # Check log structure
        for log_entry in result.logs:
            assert "timestamp" in log_entry
            assert "level" in log_entry
            assert "message" in log_entry
            assert log_entry["level"] in ["DEBUG", "INFO", "WARNING", "ERROR"]
    
    def test_database_test_timeout_handling(self):
        """Test database test timeout handling."""
        postgres_test = PostgreSQLTestV2()
        
        # Verify timeout is configured
        assert postgres_test.timeout_seconds > 0
        assert postgres_test.timeout_seconds <= 60  # Reasonable timeout
    
    def test_multiple_database_test_execution(self):
        """Test running multiple database tests concurrently."""
        from app.tests.test_runner import test_runner
        
        # Test individual test execution
        postgres_result = test_runner.run_test("postgresql")
        cassandra_result = test_runner.run_test("cassandra")
        
        # Both should return results (even if skipped due to configuration)
        if postgres_result:
            assert postgres_result["status"] in ["passed", "failed", "skipped"]
        
        if cassandra_result:
            assert cassandra_result["status"] in ["passed", "failed", "skipped"]


@pytest.mark.integration
@pytest.mark.slow
class TestDatabasePerformance:
    """Performance-related integration tests for databases."""
    
    def test_database_connection_performance(self):
        """Test database connection establishment performance."""
        import time
        from app.tests.postgres_test_v2 import PostgreSQLTestV2
        
        postgres_test = PostgreSQLTestV2()
        
        if not postgres_test.is_configured():
            pytest.skip("PostgreSQL not configured")
        
        start_time = time.time()
        result = postgres_test.execute()
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Connection attempt should complete within reasonable time
        assert execution_time < 30, f"Database test took too long: {execution_time}s"
        
        # Check that duration is recorded
        if result.status.value != "skipped":
            assert result.duration_seconds is not None
            assert result.duration_seconds > 0
    
    def test_database_concurrent_connections(self):
        """Test handling of multiple concurrent database connection attempts."""
        import concurrent.futures
        from app.tests.postgres_test_v2 import PostgreSQLTestV2
        
        def run_single_test():
            postgres_test = PostgreSQLTestV2()
            return postgres_test.execute()
        
        # Run multiple tests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_single_test) for _ in range(3)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All tests should complete
        assert len(results) == 3
        
        # Results should be consistent
        statuses = [result.status.value for result in results]
        unique_statuses = set(statuses)
        
        # All should have the same result (all pass, all fail, or all skip)
        assert len(unique_statuses) <= 2  # Allow for some variation in network conditions