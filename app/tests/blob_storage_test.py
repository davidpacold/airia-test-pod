import io
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from azure.core.exceptions import (AzureError, ResourceExistsError,
                                   ResourceNotFoundError)
from azure.storage.blob import BlobClient, BlobServiceClient, ContainerClient

from ..config import get_settings
from .base_test import BaseTest, TestResult


class BlobStorageTest(BaseTest):
    """Azure Blob Storage connectivity test using the new framework"""

    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        self.test_blob_name = f"test-blob-{uuid.uuid4().hex[:8]}.txt"
        self.test_content = f"Test content from Airia Test Pod - {datetime.now(timezone.utc).isoformat()}"

    @property
    def test_name(self) -> str:
        return "Azure Blob Storage"

    @property
    def test_description(self) -> str:
        return "Tests authentication and file operations"

    @property
    def timeout_seconds(self) -> int:
        return 60  # Blob operations can take longer than DB connections

    def is_configured(self) -> bool:
        """Check if Blob Storage is configured"""
        return bool(
            self.settings.blob_account_name
            and self.settings.blob_account_key
            and self.settings.blob_container_name
        )

    def get_configuration_help(self) -> str:
        """Return configuration help"""
        return (
            "Configure Azure Blob Storage using environment variables: "
            "BLOB_ACCOUNT_NAME, BLOB_ACCOUNT_KEY, BLOB_CONTAINER_NAME"
        )

    def get_blob_service_client(self) -> BlobServiceClient:
        """Get Azure Blob Service Client"""
        account_url = f"https://{self.settings.blob_account_name}.blob.{self.settings.blob_endpoint_suffix}"
        return BlobServiceClient(
            account_url=account_url, credential=self.settings.blob_account_key
        )

    def run_test(self) -> TestResult:
        """Run the Blob Storage test"""
        result = TestResult(self.test_name)
        result.start()

        blob_service_client = None

        try:
            # Test 1: Create Blob Service Client (reuse for all subsequent tests)
            client_result = self._test_create_client()
            blob_service_client = client_result.pop("_client", None)
            result.add_sub_test("client_creation", client_result)

            if not client_result["success"]:
                result.fail(
                    "Failed to create Blob Storage client",
                    remediation="Check account name, key, and network connectivity",
                )
                return result

            blob_service_client = blob_service_client or self.get_blob_service_client()

            # Test 2: Check/Create Container
            container_result = self._test_container_operations(blob_service_client)
            result.add_sub_test("container_operations", container_result)

            # Test 3: Upload Blob
            upload_result = self._test_upload_blob(blob_service_client)
            result.add_sub_test("upload_blob", upload_result)

            # Test 4: Download Blob
            download_result = self._test_download_blob(blob_service_client)
            result.add_sub_test("download_blob", download_result)

            # Test 5: List Blobs
            list_result = self._test_list_blobs(blob_service_client)
            result.add_sub_test("list_blobs", list_result)

            # Test 6: Cleanup
            cleanup_result = self._test_cleanup_blob(blob_service_client)
            result.add_sub_test("cleanup", cleanup_result)

            # Determine overall success
            critical_tests = [
                client_result,
                container_result,
                upload_result,
                download_result,
            ]
            all_critical_passed = all(test["success"] for test in critical_tests)

            if all_critical_passed:
                result.complete(
                    True,
                    "Blob Storage tests completed successfully",
                    {
                        "account_name": self.settings.blob_account_name,
                        "container_name": self.settings.blob_container_name,
                        "endpoint_suffix": self.settings.blob_endpoint_suffix,
                        "test_blob_size": len(self.test_content.encode()),
                        "upload_speed_mbps": upload_result.get("upload_speed_mbps", 0),
                        "download_speed_mbps": download_result.get(
                            "download_speed_mbps", 0
                        ),
                    },
                )
            else:
                result.fail("Some Blob Storage tests failed")

        except Exception as e:
            result.fail(f"Blob Storage test failed: {str(e)}", error=e)

        return result

    def _test_create_client(self) -> Dict[str, Any]:
        """Test creating Blob Service Client and return it for reuse."""
        try:
            blob_service_client = self.get_blob_service_client()

            # Test basic connectivity by getting account info
            account_info = blob_service_client.get_account_information()

            return {
                "success": True,
                "message": "Successfully created Blob Storage client",
                "_client": blob_service_client,
                "details": {
                    "account_name": self.settings.blob_account_name,
                    "account_kind": account_info.get("account_kind"),
                    "sku_name": account_info.get("sku_name"),
                },
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create client: {str(e)}",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _test_container_operations(
        self, blob_service_client: BlobServiceClient
    ) -> Dict[str, Any]:
        """Test container operations"""
        try:
            container_client = blob_service_client.get_container_client(
                self.settings.blob_container_name
            )

            # Check if container exists, create if not
            try:
                properties = container_client.get_container_properties()
                container_existed = True
            except ResourceNotFoundError:
                container_client.create_container()
                properties = container_client.get_container_properties()
                container_existed = False

            return {
                "success": True,
                "message": f"Container {'found' if container_existed else 'created'} successfully",
                "details": {
                    "container_name": self.settings.blob_container_name,
                    "container_existed": container_existed,
                    "created_on": (
                        properties["creation_time"].isoformat()
                        if properties.get("creation_time")
                        else None
                    ),
                    "last_modified": (
                        properties["last_modified"].isoformat()
                        if properties.get("last_modified")
                        else None
                    ),
                },
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Container operations failed: {str(e)}",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _test_upload_blob(
        self, blob_service_client: BlobServiceClient
    ) -> Dict[str, Any]:
        """Test uploading a blob"""
        try:
            start_time = datetime.now(timezone.utc)

            blob_client = blob_service_client.get_blob_client(
                container=self.settings.blob_container_name, blob=self.test_blob_name
            )

            # Upload test content
            blob_data = self.test_content.encode()
            blob_client.upload_blob(blob_data, overwrite=True)

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            # Calculate upload speed
            size_mb = len(blob_data) / (1024 * 1024)
            upload_speed_mbps = (size_mb / duration) if duration > 0 else 0

            return {
                "success": True,
                "message": f"Successfully uploaded blob: {self.test_blob_name}",
                "details": {
                    "blob_name": self.test_blob_name,
                    "size_bytes": len(blob_data),
                    "upload_duration_seconds": duration,
                    "upload_speed_mbps": round(upload_speed_mbps, 2),
                },
                "upload_speed_mbps": upload_speed_mbps,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Blob upload failed: {str(e)}",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _test_download_blob(
        self, blob_service_client: BlobServiceClient
    ) -> Dict[str, Any]:
        """Test downloading a blob"""
        try:
            start_time = datetime.now(timezone.utc)

            blob_client = blob_service_client.get_blob_client(
                container=self.settings.blob_container_name, blob=self.test_blob_name
            )

            # Download blob content
            download_stream = blob_client.download_blob()
            downloaded_content = download_stream.readall().decode()

            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            # Verify content matches
            content_matches = downloaded_content == self.test_content

            # Calculate download speed
            size_mb = len(downloaded_content.encode()) / (1024 * 1024)
            download_speed_mbps = (size_mb / duration) if duration > 0 else 0

            if not content_matches:
                return {
                    "success": False,
                    "message": "Downloaded content does not match uploaded content",
                    "error": "Content mismatch",
                    "details": {
                        "expected_length": len(self.test_content),
                        "actual_length": len(downloaded_content),
                    },
                }

            return {
                "success": True,
                "message": f"Successfully downloaded and verified blob: {self.test_blob_name}",
                "details": {
                    "blob_name": self.test_blob_name,
                    "size_bytes": len(downloaded_content.encode()),
                    "download_duration_seconds": duration,
                    "download_speed_mbps": round(download_speed_mbps, 2),
                    "content_verified": True,
                },
                "download_speed_mbps": download_speed_mbps,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Blob download failed: {str(e)}",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _test_list_blobs(
        self, blob_service_client: BlobServiceClient
    ) -> Dict[str, Any]:
        """Test listing blobs in container"""
        try:
            container_client = blob_service_client.get_container_client(
                self.settings.blob_container_name
            )

            # List blobs (limit to first 10 for performance)
            blobs = list(container_client.list_blobs(name_starts_with="test-blob-"))

            # Find our test blob
            test_blob_found = any(blob.name == self.test_blob_name for blob in blobs)

            return {
                "success": True,
                "message": f"Found {len(blobs)} test blob(s) in container",
                "details": {
                    "container_name": self.settings.blob_container_name,
                    "test_blobs_found": len(blobs),
                    "our_test_blob_found": test_blob_found,
                    "blob_names": [blob.name for blob in blobs[:5]],  # Show first 5
                },
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Blob listing failed: {str(e)}",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def _test_cleanup_blob(
        self, blob_service_client: BlobServiceClient
    ) -> Dict[str, Any]:
        """Test cleaning up the test blob"""
        try:
            blob_client = blob_service_client.get_blob_client(
                container=self.settings.blob_container_name, blob=self.test_blob_name
            )

            # Delete the test blob
            blob_client.delete_blob()

            return {
                "success": True,
                "message": f"Successfully deleted test blob: {self.test_blob_name}",
                "details": {"blob_name": self.test_blob_name, "deleted": True},
            }
        except ResourceNotFoundError:
            return {
                "success": True,
                "message": f"Test blob not found (already deleted): {self.test_blob_name}",
                "details": {
                    "blob_name": self.test_blob_name,
                    "deleted": False,
                    "reason": "already_deleted",
                },
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Blob cleanup failed: {str(e)}",
                "error": str(e),
                "error_type": type(e).__name__,
                "remediation": f"Manually delete blob '{self.test_blob_name}' from container '{self.settings.blob_container_name}'",
            }
