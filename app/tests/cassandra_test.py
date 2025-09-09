import ssl
import time
from typing import Any, Dict, List

from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster
from cassandra.policies import DCAwareRoundRobinPolicy

from ..config import get_settings
from .base_test import BaseTest, TestResult


class CassandraTest(BaseTest):
    """Cassandra connectivity and health test"""

    def __init__(self):
        super().__init__()
        self.settings = get_settings()

    @property
    def test_name(self) -> str:
        return "Apache Cassandra"

    @property
    def test_description(self) -> str:
        return "Tests Cassandra connectivity, keyspaces, and cluster health"

    @property
    def timeout_seconds(self) -> int:
        return 45  # Cassandra connections can be slower

    def is_configured(self) -> bool:
        """Check if Cassandra is configured"""
        return bool(
            self.settings.cassandra_hosts and self.settings.cassandra_hosts != ""
        )

    def get_configuration_help(self) -> str:
        """Return configuration help"""
        return (
            "Configure Cassandra connection using environment variables: "
            "CASSANDRA_HOSTS (comma-separated), CASSANDRA_PORT, CASSANDRA_USERNAME, "
            "CASSANDRA_PASSWORD, CASSANDRA_KEYSPACE, CASSANDRA_DATACENTER, CASSANDRA_USE_SSL"
        )

    def get_cluster_config(self) -> Dict[str, Any]:
        """Get Cassandra cluster configuration"""
        config = {
            "contact_points": [
                h.strip() for h in self.settings.cassandra_hosts.split(",")
            ],
            "port": self.settings.cassandra_port,
        }

        # Add datacenter-aware load balancing if datacenter is specified
        if self.settings.cassandra_datacenter:
            config["load_balancing_policy"] = DCAwareRoundRobinPolicy(
                local_dc=self.settings.cassandra_datacenter
            )
        # Otherwise, use the default RoundRobinPolicy (will be set automatically)

        # Add authentication if configured
        if self.settings.cassandra_username:
            auth_provider = PlainTextAuthProvider(
                username=self.settings.cassandra_username,
                password=self.settings.cassandra_password,
            )
            config["auth_provider"] = auth_provider

        # Add SSL if configured
        if self.settings.cassandra_use_ssl:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            config["ssl_context"] = ssl_context

        return config

    def run_test(self) -> TestResult:
        """Run the Cassandra test"""
        result = TestResult(self.test_name)
        result.start()

        cluster = None
        session = None

        try:
            # Test 1: Connection
            connection_result = self._test_connection()
            result.add_sub_test("connection", connection_result)

            if not connection_result["success"]:
                result.fail(
                    "Failed to connect to Cassandra cluster",
                    remediation="Check hosts, credentials, SSL settings, and network connectivity",
                )
                return result

            cluster = connection_result["cluster"]
            session = connection_result["session"]

            # Test 2: Cluster health
            health_result = self._test_cluster_health(cluster)
            result.add_sub_test("cluster_health", health_result)

            # Test 3: List keyspaces
            keyspaces_result = self._test_list_keyspaces(session)
            result.add_sub_test("keyspaces", keyspaces_result)

            # Test 4: Basic query execution
            query_result = self._test_query_execution(session)
            result.add_sub_test("query_execution", query_result)

            # Test 5: Replication settings
            replication_result = self._test_replication_settings(session)
            result.add_sub_test("replication", replication_result)

            # Determine overall success
            all_critical_passed = (
                connection_result["success"]
                and health_result["success"]
                and keyspaces_result["success"]
                and query_result["success"]
            )

            if all_critical_passed:
                result.complete(
                    True,
                    "Cassandra tests completed successfully",
                    {
                        "cluster_name": health_result.get("cluster_name", "Unknown"),
                        "nodes": len(health_result.get("nodes", [])),
                        "keyspace_count": len(keyspaces_result.get("keyspaces", [])),
                        "datacenter": self.settings.cassandra_datacenter,
                        "hosts": self.settings.cassandra_hosts,
                    },
                )
            else:
                result.fail("Some Cassandra tests failed")

        except Exception as e:
            result.fail(
                f"Cassandra test failed: {str(e)}",
                error=e,
                remediation=self._get_cassandra_error_remediation(e),
            )
        finally:
            # Clean up connections
            if session:
                try:
                    session.shutdown()
                except:
                    pass
            if cluster:
                try:
                    cluster.shutdown()
                except:
                    pass

        return result

    def _test_connection(self) -> Dict[str, Any]:
        """Test basic connection to Cassandra"""
        try:
            result = {"success": False, "message": "", "details": {}}

            # Create cluster connection
            cluster_config = self.get_cluster_config()
            result["details"]["hosts"] = cluster_config["contact_points"]
            result["details"]["port"] = cluster_config["port"]

            cluster = Cluster(**cluster_config)

            # Connect to cluster
            session = cluster.connect()

            result["success"] = True
            result["message"] = "Successfully connected to Cassandra cluster"
            result["cluster"] = cluster
            result["session"] = session

            self.logger.info("Cassandra connection successful")
            return result

        except Exception as e:
            self.logger.error(f"Cassandra connection failed: {str(e)}")
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "error": str(e),
            }

    def _test_cluster_health(self, cluster) -> Dict[str, Any]:
        """Test cluster health and node status"""
        try:
            result = {"success": False, "message": "", "details": {}}

            # Get cluster metadata
            metadata = cluster.metadata
            result["cluster_name"] = metadata.cluster_name

            # Get node information
            nodes = []
            for host in metadata.all_hosts():
                node_info = {
                    "address": host.address,
                    "datacenter": host.datacenter,
                    "rack": host.rack,
                    "is_up": host.is_up,
                    "release_version": host.release_version,
                }
                nodes.append(node_info)

            result["nodes"] = nodes
            result["details"]["total_nodes"] = len(nodes)
            result["details"]["up_nodes"] = sum(1 for n in nodes if n["is_up"])
            result["details"]["down_nodes"] = sum(1 for n in nodes if not n["is_up"])

            # Check if enough nodes are up
            if result["details"]["up_nodes"] == 0:
                result["success"] = False
                result["message"] = "No Cassandra nodes are up"
            else:
                result["success"] = True
                result["message"] = (
                    f"Cluster '{result['cluster_name']}' has {result['details']['up_nodes']} nodes up"
                )

            return result

        except Exception as e:
            self.logger.error(f"Cluster health check failed: {str(e)}")
            return {
                "success": False,
                "message": f"Health check failed: {str(e)}",
                "error": str(e),
            }

    def _test_list_keyspaces(self, session) -> Dict[str, Any]:
        """Test listing keyspaces"""
        try:
            result = {"success": False, "message": "", "keyspaces": []}

            # Query system keyspaces
            rows = session.execute(
                """
                SELECT keyspace_name 
                FROM system_schema.keyspaces 
                WHERE keyspace_name NOT IN ('system', 'system_schema', 'system_auth', 'system_distributed', 'system_traces')
            """
            )

            keyspaces = [row.keyspace_name for row in rows]
            result["keyspaces"] = keyspaces
            result["details"] = {"user_keyspace_count": len(keyspaces)}

            # If specific keyspace configured, check if it exists
            if self.settings.cassandra_keyspace:
                if self.settings.cassandra_keyspace in keyspaces:
                    result["message"] = (
                        f"Found configured keyspace: {self.settings.cassandra_keyspace}"
                    )
                    result["details"]["configured_keyspace_exists"] = True
                else:
                    result["message"] = (
                        f"Configured keyspace '{self.settings.cassandra_keyspace}' not found"
                    )
                    result["details"]["configured_keyspace_exists"] = False
            else:
                result["message"] = f"Found {len(keyspaces)} user keyspaces"

            result["success"] = True
            return result

        except Exception as e:
            self.logger.error(f"Failed to list keyspaces: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to list keyspaces: {str(e)}",
                "error": str(e),
            }

    def _test_query_execution(self, session) -> Dict[str, Any]:
        """Test basic query execution"""
        try:
            result = {"success": False, "message": "", "details": {}}

            # Execute a simple system query
            start_time = time.time()
            row = session.execute(
                "SELECT cluster_name, release_version FROM system.local"
            ).one()
            execution_time = time.time() - start_time

            result["success"] = True
            result["message"] = "Query execution successful"
            result["details"] = {
                "cluster_name": row.cluster_name,
                "release_version": row.release_version,
                "execution_time_ms": round(execution_time * 1000, 2),
            }

            return result

        except Exception as e:
            self.logger.error(f"Query execution failed: {str(e)}")
            return {
                "success": False,
                "message": f"Query execution failed: {str(e)}",
                "error": str(e),
            }

    def _test_replication_settings(self, session) -> Dict[str, Any]:
        """Test replication settings for keyspaces"""
        try:
            result = {"success": True, "message": "", "details": {}}

            # Get replication settings for user keyspaces
            rows = session.execute(
                """
                SELECT keyspace_name, replication 
                FROM system_schema.keyspaces 
                WHERE keyspace_name NOT IN ('system', 'system_schema', 'system_auth', 'system_distributed', 'system_traces')
            """
            )

            replication_info = {}
            for row in rows:
                replication_info[row.keyspace_name] = row.replication

            result["replication_settings"] = replication_info
            result["message"] = (
                f"Retrieved replication settings for {len(replication_info)} keyspaces"
            )

            # Check specific keyspace if configured
            if (
                self.settings.cassandra_keyspace
                and self.settings.cassandra_keyspace in replication_info
            ):
                result["details"]["configured_keyspace_replication"] = replication_info[
                    self.settings.cassandra_keyspace
                ]

            return result

        except Exception as e:
            self.logger.error(f"Failed to check replication settings: {str(e)}")
            # This is not critical, so we don't fail the entire test
            return {
                "success": True,
                "message": f"Could not retrieve replication settings: {str(e)}",
                "error": str(e),
            }

    def _get_cassandra_error_remediation(self, error: Exception) -> str:
        """Get Cassandra-specific error remediation"""
        error_msg = str(error).lower()

        if "authentication" in error_msg:
            return "Verify CASSANDRA_USERNAME and CASSANDRA_PASSWORD are correct"
        elif "connection" in error_msg or "cannot connect" in error_msg:
            return "Check CASSANDRA_HOSTS are reachable, port is correct, and firewall rules allow connection"
        elif "ssl" in error_msg or "tls" in error_msg:
            return "Verify CASSANDRA_USE_SSL setting matches your cluster configuration"
        elif "keyspace" in error_msg:
            return "Ensure the keyspace exists or remove CASSANDRA_KEYSPACE environment variable"
        elif "timeout" in error_msg:
            return "Increase timeout or check network latency to Cassandra cluster"
        else:
            return "Check Cassandra cluster status and configuration"
