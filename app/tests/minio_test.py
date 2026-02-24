import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import boto3
from botocore.config import Config
from botocore.exceptions import (ClientError, EndpointConnectionError,
                                 NoCredentialsError)

from .base_test import BaseTest, TestResult


class MinioTest(BaseTest):
    """Test Minio S3-compatible storage connectivity"""

    def __init__(self):
        super().__init__()
        # Get Minio configuration from environment
        self.endpoint_url = os.getenv("MINIO_ENDPOINT_URL", "")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "")
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "test-bucket")
        self.secure = os.getenv("MINIO_SECURE", "true").lower() == "true"

    @property
    def test_name(self) -> str:
        return "Minio Storage"

    @property
    def test_description(self) -> str:
        return "Tests S3-compatible Minio storage connectivity, bucket access, and file operations"

    @property
    def test_id(self) -> str:
        return "minio"

    @property
    def is_optional(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 30

    def is_configured(self) -> bool:
        """Check if Minio is configured"""
        return bool(
            self.endpoint_url
            and self.access_key
            and self.secret_key
            and self.bucket_name
        )

    def get_configuration_help(self) -> str:
        return (
            "Minio storage testing requires configuration. "
            "Configure using environment variables: "
            "MINIO_ENDPOINT_URL (e.g., https://minio.example.com), "
            "MINIO_ACCESS_KEY, MINIO_SECRET_KEY, "
            "MINIO_BUCKET_NAME (default: test-bucket), "
            "MINIO_SECURE (default: true)"
        )

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        try:
            if not self.is_configured():
                result.skip("Minio not configured")
                return result

            # Test 1: Connection test
            connection_result = self._test_connection()
            result.add_sub_test("connection", connection_result)

            # Test 2: List buckets
            list_buckets_result = self._test_list_buckets()
            result.add_sub_test("list_buckets", list_buckets_result)

            # Test 3: Check/create test bucket
            bucket_access_result = self._test_bucket_access()
            result.add_sub_test("bucket_access", bucket_access_result)

            # Test 4: File operations (only if bucket access works)
            if bucket_access_result["success"]:
                file_ops_result = self._test_file_operations()
                result.add_sub_test("file_operations", file_ops_result)
            else:
                result.add_sub_test(
                    "file_operations",
                    {
                        "success": False,
                        "message": "Skipped due to bucket access failure",
                        "skipped": True,
                    },
                )

            # Determine overall success
            critical_tests_passed = (
                connection_result["success"]
                and list_buckets_result["success"]
                and bucket_access_result["success"]
            )

            if critical_tests_passed:
                result.complete(
                    True,
                    "Minio storage tests completed successfully",
                    {
                        "endpoint": self.endpoint_url,
                        "bucket": self.bucket_name,
                        "secure": self.secure,
                    },
                )
            else:
                failed_tests = []
                if not connection_result["success"]:
                    failed_tests.append("connection")
                if not list_buckets_result["success"]:
                    failed_tests.append("list_buckets")
                if not bucket_access_result["success"]:
                    failed_tests.append("bucket_access")

                result.fail(
                    f"Minio storage tests failed: {', '.join(failed_tests)}",
                    remediation="Check Minio endpoint, credentials, and network connectivity",
                )

        except Exception as e:
            result.fail(
                f"Minio test failed: {str(e)}",
                error=e,
                remediation="Check Minio configuration and network connectivity",
            )

        return result

    def _get_s3_client(self):
        """Create S3 client for Minio"""
        # Configure for Minio compatibility
        config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},  # Use path-style for Minio compatibility
        )

        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=config,
            verify=True,  # Always verify SSL certificates when SSL is enabled
        )

    def _test_connection(self) -> Dict[str, Any]:
        """Test basic connection to Minio"""
        try:
            s3_client = self._get_s3_client()

            # Try to list buckets as a connection test
            response = s3_client.list_buckets()

            return {
                "success": True,
                "message": "Successfully connected to Minio",
                "details": {
                    "endpoint": self.endpoint_url,
                    "secure": self.secure,
                    "bucket_count": len(response.get("Buckets", [])),
                },
            }
        except EndpointConnectionError as e:
            return {
                "success": False,
                "message": f"Failed to connect to Minio endpoint: {str(e)}",
                "error": str(e),
                "remediation": "Check Minio endpoint URL and network connectivity",
            }
        except NoCredentialsError:
            return {
                "success": False,
                "message": "Invalid or missing Minio credentials",
                "remediation": "Check MINIO_ACCESS_KEY and MINIO_SECRET_KEY configuration",
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            return {
                "success": False,
                "message": f"Minio connection failed: {error_code}",
                "error": str(e),
                "remediation": "Check Minio credentials and permissions",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected connection error: {str(e)}",
                "error": str(e),
            }

    def _test_list_buckets(self) -> Dict[str, Any]:
        """Test listing buckets"""
        try:
            s3_client = self._get_s3_client()
            response = s3_client.list_buckets()

            buckets = []
            for bucket in response.get("Buckets", []):
                buckets.append(
                    {
                        "name": bucket["Name"],
                        "created": bucket["CreationDate"].isoformat(),
                    }
                )

            return {
                "success": True,
                "message": f"Found {len(buckets)} bucket(s)",
                "buckets": buckets,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list buckets: {str(e)}",
                "error": str(e),
            }

    def _test_bucket_access(self) -> Dict[str, Any]:
        """Test access to the specified bucket, create if doesn't exist"""
        try:
            s3_client = self._get_s3_client()

            # Check if bucket exists
            bucket_exists = False
            bucket_created = False
            try:
                s3_client.head_bucket(Bucket=self.bucket_name)
                bucket_exists = True
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    # Bucket doesn't exist, try to create it
                    try:
                        s3_client.create_bucket(Bucket=self.bucket_name)
                        bucket_created = True
                        bucket_exists = True
                    except ClientError as create_error:
                        return {
                            "success": False,
                            "message": f"Failed to create bucket '{self.bucket_name}'",
                            "error": str(create_error),
                            "remediation": "Check permissions to create buckets or manually create the bucket",
                        }
                else:
                    raise e

            # Try to list objects in the bucket (test read access)
            response = s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            object_count = response.get("KeyCount", 0)

            message = f"Successfully accessed bucket '{self.bucket_name}'"
            if bucket_created:
                message = f"Created and accessed bucket '{self.bucket_name}'"

            return {
                "success": True,
                "message": message,
                "details": {
                    "bucket_name": self.bucket_name,
                    "bucket_created": bucket_created,
                    "object_count": object_count,
                    "can_list": True,
                },
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            return {
                "success": False,
                "message": f"Bucket access failed: {error_code}",
                "error": str(e),
                "remediation": "Check bucket permissions and Minio credentials",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Bucket access test failed: {str(e)}",
                "error": str(e),
            }

    def _test_file_operations(self) -> Dict[str, Any]:
        """Test file upload, download, and delete operations"""
        test_key = f"test-file-{uuid.uuid4().hex[:8]}.txt"
        test_content = f"Minio test file created at {datetime.now(timezone.utc).isoformat()}"

        try:
            s3_client = self._get_s3_client()

            # Test 1: Upload file
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=test_key,
                Body=test_content,
                ContentType="text/plain",
            )

            # Test 2: Download file
            response = s3_client.get_object(Bucket=self.bucket_name, Key=test_key)
            downloaded_content = response["Body"].read().decode("utf-8")

            # Verify content
            if downloaded_content != test_content:
                return {
                    "success": False,
                    "message": "File content verification failed",
                    "remediation": "Check Minio storage integrity",
                }

            # Test 3: Delete file (cleanup)
            s3_client.delete_object(Bucket=self.bucket_name, Key=test_key)

            return {
                "success": True,
                "message": "File operations completed successfully",
                "details": {
                    "test_file": test_key,
                    "upload": "success",
                    "download": "success",
                    "content_verified": "success",
                    "cleanup": "success",
                },
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]

            # Try to clean up the test file if it was created
            try:
                s3_client.delete_object(Bucket=self.bucket_name, Key=test_key)
            except Exception:
                pass  # Ignore cleanup errors

            return {
                "success": False,
                "message": f"File operations failed: {error_code}",
                "error": str(e),
                "remediation": "Check bucket write permissions",
            }
        except Exception as e:
            # Try to clean up the test file if it was created
            try:
                s3_client = self._get_s3_client()
                s3_client.delete_object(Bucket=self.bucket_name, Key=test_key)
            except Exception:
                pass  # Ignore cleanup errors

            return {
                "success": False,
                "message": f"File operations failed: {str(e)}",
                "error": str(e),
            }
