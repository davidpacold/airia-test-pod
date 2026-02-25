from typing import Any, Dict, List

import psycopg2
from psycopg2 import sql

from ..config import get_settings
from .base_test import BaseTest, TestResult


class PostgreSQLTestV2(BaseTest):
    """PostgreSQL connectivity test using the new framework"""

    def __init__(self):
        super().__init__()
        self.settings = get_settings()

    @property
    def test_name(self) -> str:
        return "PostgreSQL Database"

    @property
    def test_description(self) -> str:
        return "Tests connection, databases, and extensions"

    @property
    def timeout_seconds(self) -> int:
        return 30

    def is_configured(self) -> bool:
        """Check if PostgreSQL is configured"""
        return bool(
            self.settings.postgres_host
            and self.settings.postgres_host != "localhost"
            and self.settings.postgres_user
            and self.settings.postgres_password
        )

    def get_configuration_help(self) -> str:
        """Return configuration help"""
        return (
            "Configure PostgreSQL connection using environment variables: "
            "POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DATABASE"
        )

    def get_connection_params(self) -> Dict[str, Any]:
        """Get PostgreSQL connection parameters"""
        return {
            "host": self.settings.postgres_host,
            "port": self.settings.postgres_port,
            "database": self.settings.postgres_database,
            "user": self.settings.postgres_user,
            "password": self.settings.postgres_password,
            "sslmode": self.settings.postgres_sslmode,
            "connect_timeout": 10,
        }

    def run_test(self) -> TestResult:
        """Run the PostgreSQL test"""
        result = TestResult(self.test_name)
        result.start()

        conn = None
        try:
            # Test 1: Connection (also establishes shared connection)
            connection_result = self._test_connection()
            conn = connection_result.pop("_conn", None)
            result.add_sub_test("connection", connection_result)

            if not connection_result["success"]:
                result.fail(
                    "Failed to connect to PostgreSQL",
                    remediation="Check host, credentials, and network connectivity",
                )
                return result

            # Test 2: List databases
            databases_result = self._test_list_databases(conn)
            result.add_sub_test("databases", databases_result)

            # Test 3: List extensions
            extensions_result = self._test_list_extensions(conn)
            result.add_sub_test("extensions", extensions_result)

            # Determine overall success
            all_critical_passed = (
                connection_result["success"]
                and databases_result["success"]
                and extensions_result["success"]
            )

            if all_critical_passed:
                result.complete(
                    True,
                    "PostgreSQL tests completed successfully",
                    {
                        "version": connection_result.get("details", {}).get("version"),
                        "host": self.settings.postgres_host,
                        "port": self.settings.postgres_port,
                        "database": self.settings.postgres_database,
                        "database_count": len(databases_result.get("databases", [])),
                        "extension_count": len(
                            extensions_result.get("installed_extensions", [])
                        ),
                    },
                )
            else:
                result.fail("Some PostgreSQL tests failed")

        except Exception as e:
            result.fail(f"PostgreSQL test failed: {str(e)}", error=e)
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        return result

    def _test_connection(self) -> Dict[str, Any]:
        """Test basic connection and return connection for reuse"""
        try:
            conn_params = self.get_connection_params()
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()

            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]

            cursor.close()

            return {
                "success": True,
                "message": "Successfully connected to PostgreSQL",
                "details": {
                    "version": version,
                    "connection_params": {
                        k: v for k, v in conn_params.items() if k != "password"
                    },
                },
                "_conn": conn,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _test_list_databases(self, conn) -> Dict[str, Any]:
        """Test listing databases"""
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT datname, pg_database_size(datname) as size
                FROM pg_database
                WHERE datistemplate = false
                ORDER BY datname;
            """
            )

            databases = []
            for db_name, size in cursor.fetchall():
                databases.append(
                    {
                        "name": db_name,
                        "size": size,
                        "size_human": self._format_bytes(size),
                    }
                )

            cursor.close()

            return {
                "success": True,
                "message": f"Found {len(databases)} database(s)",
                "databases": databases,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list databases: {str(e)}",
                "error": str(e),
            }

    def _test_list_extensions(self, conn) -> Dict[str, Any]:
        """Test listing extensions"""
        try:
            cursor = conn.cursor()

            # Get installed extensions
            cursor.execute(
                """
                SELECT extname, extversion
                FROM pg_extension
                ORDER BY extname;
            """
            )

            installed_extensions = []
            for ext_name, ext_version in cursor.fetchall():
                installed_extensions.append({"name": ext_name, "version": ext_version})

            # Get all available extensions
            cursor.execute(
                """
                SELECT name, default_version, installed_version
                FROM pg_available_extensions
                ORDER BY name;
            """
            )

            available_extensions = []
            for name, default_version, installed_version in cursor.fetchall():
                available_extensions.append(
                    {
                        "name": name,
                        "version": default_version,
                        "installed": installed_version is not None,
                    }
                )

            cursor.close()

            return {
                "success": True,
                "message": f"Found {len(installed_extensions)} installed extension(s), showing {len(available_extensions)} total available extensions",
                "installed_extensions": installed_extensions,
                "available_extensions": available_extensions,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list extensions: {str(e)}",
                "error": str(e),
            }

    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
