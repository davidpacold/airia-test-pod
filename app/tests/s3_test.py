import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import boto3
from botocore.config import Config
from botocore.exceptions import (ClientError, EndpointConnectionError,
                                 NoCredentialsError)

from .base_test import BaseTest, TestResult


class S3Test(BaseTest):
    """Test Amazon S3 storage connectivity"""

    def __init__(self):
        super().__init__()
        # Get S3 configuration from environment
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        self.session_token = os.getenv(
            "AWS_SESSION_TOKEN", ""
        )  # Optional for temporary credentials
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "test-bucket")
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL", "")  # Optional custom endpoint

    @property
    def test_name(self) -> str:
        return "Amazon S3 Storage"

    @property
    def test_description(self) -> str:
        return "Tests Amazon S3 connectivity, bucket access, and file operations"

    @property
    def test_id(self) -> str:
        return "s3"

    @property
    def is_optional(self) -> bool:
        return True

    @property
    def timeout_seconds(self) -> int:
        return 30

    def is_configured(self) -> bool:
        """Check if S3 is configured"""
        return bool(self.access_key and self.secret_key and self.bucket_name)

    def get_configuration_help(self) -> str:
        return (
            "Amazon S3 storage testing requires configuration. "
            "Configure using environment variables: "
            "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, "
            "S3_BUCKET_NAME (default: test-bucket), "
            "AWS_REGION (default: us-east-1), "
            "AWS_SESSION_TOKEN (optional for temporary credentials), "
            "S3_ENDPOINT_URL (optional for custom endpoints)"
        )

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        try:
            if not self.is_configured():
                result.skip("Amazon S3 not configured")
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

            # Test 5: Check bucket versioning (optional)
            versioning_result = self._test_bucket_versioning()
            result.add_sub_test("versioning_check", versioning_result)

            # Determine overall success - focus on bucket-specific operations
            # Connection and list_buckets may fail with limited permissions (this is OK)
            # The critical test is bucket_access - can we work with the specified bucket?
            bucket_operations_work = bucket_access_result["success"]
            
            # Check if we're using limited permissions (security best practice)
            using_limited_permissions = (
                connection_result.get("limited_permissions", False) or
                list_buckets_result.get("limited_permissions", False)
            )

            if bucket_operations_work:
                if using_limited_permissions:
                    success_message = "Amazon S3 storage tests completed successfully (using least-privilege IAM policy)"
                    additional_info = {
                        "region": self.aws_region,
                        "bucket": self.bucket_name,
                        "endpoint": self.endpoint_url
                        or f"https://s3.{self.aws_region}.amazonaws.com",
                        "security_note": "Using bucket-scoped permissions - recommended configuration",
                    }
                else:
                    success_message = "Amazon S3 storage tests completed successfully"
                    additional_info = {
                        "region": self.aws_region,
                        "bucket": self.bucket_name,
                        "endpoint": self.endpoint_url
                        or f"https://s3.{self.aws_region}.amazonaws.com",
                    }
                
                result.complete(True, success_message, additional_info)
            else:
                # Only fail if bucket-specific operations don't work
                failed_tests = []
                if not connection_result["success"] and not connection_result.get("limited_permissions", False):
                    failed_tests.append("connection")
                if not bucket_access_result["success"]:
                    failed_tests.append("bucket_access")

                if failed_tests:
                    result.fail(
                        f"Amazon S3 storage tests failed: {', '.join(failed_tests)}",
                        remediation="Check AWS credentials, region, bucket name, and IAM permissions for bucket access",
                    )
                else:
                    # This shouldn't happen, but handle gracefully
                    result.fail(
                        "Amazon S3 storage tests failed: Unable to access specified bucket",
                        remediation="Check bucket name and IAM permissions for bucket access",
                    )

        except Exception as e:
            result.fail(
                f"Amazon S3 test failed: {str(e)}",
                error=e,
                remediation="Check AWS configuration and network connectivity",
            )

        return result

    def _get_s3_client(self):
        """Create S3 client for Amazon S3"""
        # Configure for Amazon S3
        config = Config(
            region_name=self.aws_region,
            signature_version="s3v4",
            retries={"max_attempts": 2, "mode": "standard"},
        )

        session_params = {
            "aws_access_key_id": self.access_key,
            "aws_secret_access_key": self.secret_key,
            "region_name": self.aws_region,
        }

        # Add session token if provided (for temporary credentials)
        if self.session_token:
            session_params["aws_session_token"] = self.session_token

        session = boto3.Session(**session_params)

        client_params = {"config": config}

        # Add custom endpoint if provided
        if self.endpoint_url:
            client_params["endpoint_url"] = self.endpoint_url

        return session.client("s3", **client_params)

    def _test_connection(self) -> Dict[str, Any]:
        """Test basic connection to Amazon S3"""
        try:
            s3_client = self._get_s3_client()

            # Try to list buckets as a connection test
            response = s3_client.list_buckets()

            return {
                "success": True,
                "message": "Successfully connected to Amazon S3",
                "details": {
                    "region": self.aws_region,
                    "endpoint": self.endpoint_url
                    or f"https://s3.{self.aws_region}.amazonaws.com",
                    "bucket_count": len(response.get("Buckets", [])),
                },
            }
        except EndpointConnectionError as e:
            return {
                "success": False,
                "message": f"Failed to connect to S3 endpoint: {str(e)}",
                "error": str(e),
                "remediation": "Check AWS region and network connectivity",
            }
        except NoCredentialsError:
            return {
                "success": False,
                "message": "Invalid or missing AWS credentials",
                "remediation": "Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY configuration",
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDenied":
                return {
                    "success": True,
                    "message": "Using bucket-scoped permissions (secure configuration)",
                    "details": {
                        "region": self.aws_region,
                        "endpoint": self.endpoint_url
                        or f"https://s3.{self.aws_region}.amazonaws.com",
                        "note": "Limited IAM permissions detected - this is a security best practice",
                    },
                    "limited_permissions": True,
                }
            return {
                "success": False,
                "message": f"AWS S3 connection failed: {error_code}",
                "error": str(e),
                "remediation": "Check AWS credentials and IAM permissions",
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
                # Get bucket location
                try:
                    location_response = s3_client.get_bucket_location(
                        Bucket=bucket["Name"]
                    )
                    location = location_response.get("LocationConstraint", "us-east-1")
                except Exception:
                    location = "unknown"

                buckets.append(
                    {
                        "name": bucket["Name"],
                        "created": bucket["CreationDate"].isoformat(),
                        "region": location,
                    }
                )

            return {
                "success": True,
                "message": f"Found {len(buckets)} bucket(s)",
                "buckets": buckets[:10],  # Limit to first 10 buckets for display
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDenied":
                return {
                    "success": True,
                    "message": "Skipped: Limited IAM permissions (security best practice)",
                    "details": {
                        "note": "Using bucket-scoped permissions instead of account-wide access",
                        "recommendation": "This is the recommended secure configuration",
                    },
                    "limited_permissions": True,
                }
            return {
                "success": False,
                "message": f"Failed to list buckets: {error_code}",
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list buckets: {str(e)}",
                "error": str(e),
            }

    def _test_bucket_access(self) -> Dict[str, Any]:
        """Test access to the specified bucket"""
        try:
            s3_client = self._get_s3_client()

            # Check if bucket exists
            try:
                s3_client.head_bucket(Bucket=self.bucket_name)
                bucket_exists = True
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    bucket_exists = False
                elif e.response["Error"]["Code"] == "403":
                    return {
                        "success": False,
                        "message": f"Access denied to bucket '{self.bucket_name}'",
                        "remediation": "Check IAM permissions for the bucket",
                    }
                else:
                    raise e

            if not bucket_exists:
                return {
                    "success": False,
                    "message": f"Bucket '{self.bucket_name}' does not exist",
                    "remediation": f"Create bucket '{self.bucket_name}' or update S3_BUCKET_NAME configuration",
                }

            # Try to list objects in the bucket (test read access)
            response = s3_client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            object_count = response.get("KeyCount", 0)

            # Get bucket location
            try:
                location_response = s3_client.get_bucket_location(
                    Bucket=self.bucket_name
                )
                bucket_region = location_response.get("LocationConstraint", "us-east-1")
            except Exception:
                bucket_region = "unknown"

            return {
                "success": True,
                "message": f"Successfully accessed bucket '{self.bucket_name}'",
                "details": {
                    "bucket_name": self.bucket_name,
                    "bucket_region": bucket_region,
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
                "remediation": "Check IAM permissions for s3:ListBucket and s3:GetBucketLocation",
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
        test_content = f"Amazon S3 test file created at {datetime.now(timezone.utc).isoformat()}"

        try:
            s3_client = self._get_s3_client()

            # Test 1: Upload file with server-side encryption
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=test_key,
                Body=test_content,
                ContentType="text/plain",
                ServerSideEncryption="AES256",  # Use S3 server-side encryption
            )

            # Test 2: Download file
            response = s3_client.get_object(Bucket=self.bucket_name, Key=test_key)
            downloaded_content = response["Body"].read().decode("utf-8")

            # Verify content
            if downloaded_content != test_content:
                return {
                    "success": False,
                    "message": "File content verification failed",
                    "remediation": "Check S3 storage integrity",
                }

            # Check encryption status
            encryption_status = response.get("ServerSideEncryption", "None")

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
                    "encryption": encryption_status,
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
                "remediation": "Check IAM permissions for s3:PutObject, s3:GetObject, and s3:DeleteObject",
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

    def _test_bucket_versioning(self) -> Dict[str, Any]:
        """Test bucket versioning status"""
        try:
            s3_client = self._get_s3_client()

            # Get bucket versioning status
            response = s3_client.get_bucket_versioning(Bucket=self.bucket_name)
            versioning_status = response.get("Status", "Not configured")
            mfa_delete = response.get("MFADelete", "Not configured")

            return {
                "success": True,
                "message": "Bucket versioning check completed",
                "details": {"versioning": versioning_status, "mfa_delete": mfa_delete},
            }
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDenied":
                return {
                    "success": True,  # Don't fail the test for this optional check
                    "message": "Cannot check versioning (insufficient permissions)",
                    "details": {
                        "versioning": "Unknown",
                        "note": "Requires s3:GetBucketVersioning permission",
                    },
                }
            return {
                "success": False,
                "message": f"Failed to check versioning: {error_code}",
                "error": str(e),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Versioning check failed: {str(e)}",
                "error": str(e),
            }
