from typing import Dict, Any, Optional
import os
import uuid
from datetime import datetime, timezone
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from .base_test import BaseTest, TestResult
from ..models import TestStatus


class PVCTest(BaseTest):
    """Test Kubernetes Persistent Volume Claims functionality"""

    def __init__(self):
        super().__init__()
        self.namespace = os.getenv("KUBERNETES_NAMESPACE", "default")
        self.storage_class = os.getenv("STORAGE_CLASS", "default")
        self.test_pvc_size = os.getenv("TEST_PVC_SIZE", "1Gi")

    @property
    def test_name(self) -> str:
        return "Kubernetes PVC"

    @property
    def test_description(self) -> str:
        return "Tests Persistent Volume Claims creation and storage classes"

    @property
    def test_id(self) -> str:
        return "pvc"

    @property
    def timeout_seconds(self) -> int:
        return 60  # PVC operations can take longer

    def is_configured(self) -> bool:
        """Check if Kubernetes is accessible"""
        try:
            # Try to load in-cluster config first (when running in pod)
            config.load_incluster_config()
            return True
        except config.ConfigException:
            try:
                # Fall back to kubeconfig (for local testing)
                config.load_kube_config()
                return True
            except (config.ConfigException, FileNotFoundError):
                return False

    def get_configuration_help(self) -> str:
        return (
            "Kubernetes client configuration required. "
            "Ensure pod has proper RBAC permissions or kubeconfig is available. "
            "Environment variables: KUBERNETES_NAMESPACE (default: 'default'), "
            "STORAGE_CLASS (default: 'default'), TEST_PVC_SIZE (default: '1Gi')"
        )

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        try:
            # Load Kubernetes config
            try:
                config.load_incluster_config()
                result.add_log("INFO", "Using in-cluster Kubernetes config")
            except config.ConfigException:
                config.load_kube_config()
                result.add_log("INFO", "Using kubeconfig file")

            # Create API client
            v1 = client.CoreV1Api()
            storage_v1 = client.StorageV1Api()

            # Test 1: List available storage classes
            self._test_storage_classes(storage_v1, result)

            # Test 2: Check namespace exists
            self._test_namespace_access(v1, result)

            # Test 3: Create test PVC
            test_pvc_name = f"airia-test-pvc-{uuid.uuid4().hex[:8]}"
            pvc_created = self._test_pvc_creation(v1, test_pvc_name, result)

            # Test 4: Verify PVC status
            if pvc_created:
                self._test_pvc_status(v1, test_pvc_name, result)

                # Test 5: Cleanup - Delete test PVC
                self._test_pvc_deletion(v1, test_pvc_name, result)

            # Determine overall status
            failed_tests = [
                name
                for name, test_result in result.sub_tests.items()
                if not test_result.get("success", False)
            ]

            if not failed_tests:
                result.complete(True, "All PVC tests passed successfully")
            else:
                result.fail(
                    f"Failed sub-tests: {', '.join(failed_tests)}",
                    remediation="Check RBAC permissions, storage classes, and cluster configuration",
                )

        except Exception as e:
            result.fail(
                f"PVC test failed: {str(e)}",
                error=e,
                remediation="Ensure pod has proper Kubernetes RBAC permissions and storage is available",
            )

        return result

    def _test_storage_classes(
        self, storage_v1: client.StorageV1Api, result: TestResult
    ):
        """Test listing storage classes"""
        try:
            storage_classes = storage_v1.list_storage_class()
            class_names = [sc.metadata.name for sc in storage_classes.items]

            if not class_names:
                result.add_sub_test(
                    "List Storage Classes",
                    {
                        "success": False,
                        "message": "No storage classes found in cluster",
                        "remediation": "Ensure cluster has at least one storage class configured",
                    },
                )
                return

            # Check if our configured storage class exists
            if self.storage_class not in class_names:
                result.add_sub_test(
                    "List Storage Classes",
                    {
                        "success": False,
                        "message": f"Configured storage class '{self.storage_class}' not found",
                        "available_classes": class_names,
                        "remediation": f"Use one of the available storage classes: {', '.join(class_names)}",
                    },
                )
                return

            result.add_sub_test(
                "List Storage Classes",
                {
                    "success": True,
                    "message": f"Found {len(class_names)} storage classes",
                    "storage_classes": class_names,
                    "configured_class": self.storage_class,
                },
            )

        except ApiException as e:
            result.add_sub_test(
                "List Storage Classes",
                {
                    "success": False,
                    "message": f"Failed to list storage classes: {e.reason}",
                    "remediation": "Check RBAC permissions for storage class access",
                },
            )

    def _test_namespace_access(self, v1: client.CoreV1Api, result: TestResult):
        """Test namespace access"""
        try:
            namespace = v1.read_namespace(name=self.namespace)
            result.add_sub_test(
                "Namespace Access",
                {
                    "success": True,
                    "message": f"Successfully accessed namespace '{self.namespace}'",
                    "namespace": self.namespace,
                    "created": namespace.metadata.creation_timestamp.isoformat(),
                },
            )

        except ApiException as e:
            result.add_sub_test(
                "Namespace Access",
                {
                    "success": False,
                    "message": f"Failed to access namespace '{self.namespace}': {e.reason}",
                    "remediation": f"Ensure namespace '{self.namespace}' exists and pod has access",
                },
            )

    def _test_pvc_creation(
        self, v1: client.CoreV1Api, pvc_name: str, result: TestResult
    ) -> bool:
        """Test PVC creation"""
        try:
            # Create PVC manifest
            pvc_manifest = client.V1PersistentVolumeClaim(
                metadata=client.V1ObjectMeta(
                    name=pvc_name, labels={"app": "airia-test-pod", "test": "pvc"}
                ),
                spec=client.V1PersistentVolumeClaimSpec(
                    access_modes=["ReadWriteOnce"],
                    storage_class_name=self.storage_class,
                    resources=client.V1ResourceRequirements(
                        requests={"storage": self.test_pvc_size}
                    ),
                ),
            )

            # Create the PVC
            created_pvc = v1.create_namespaced_persistent_volume_claim(
                namespace=self.namespace, body=pvc_manifest
            )

            result.add_sub_test(
                "PVC Creation",
                {
                    "success": True,
                    "message": f"Successfully created PVC '{pvc_name}'",
                    "pvc_name": pvc_name,
                    "storage_class": self.storage_class,
                    "size": self.test_pvc_size,
                    "created_time": created_pvc.metadata.creation_timestamp.isoformat(),
                },
            )

            return True

        except ApiException as e:
            result.add_sub_test(
                "PVC Creation",
                {
                    "success": False,
                    "message": f"Failed to create PVC: {e.reason}",
                    "remediation": "Check RBAC permissions for PVC creation and storage class availability",
                },
            )
            return False

    def _test_pvc_status(self, v1: client.CoreV1Api, pvc_name: str, result: TestResult):
        """Test PVC status and binding"""
        try:
            # Wait a moment for PVC to potentially bind
            import time

            time.sleep(2)

            pvc = v1.read_namespaced_persistent_volume_claim(
                name=pvc_name, namespace=self.namespace
            )

            phase = pvc.status.phase
            capacity = pvc.status.capacity
            bound_volume = pvc.spec.volume_name

            result.add_sub_test(
                "PVC Status",
                {
                    "success": True,
                    "message": f"PVC status: {phase}",
                    "phase": phase,
                    "capacity": dict(capacity) if capacity else None,
                    "bound_volume": bound_volume,
                    "storage_class": pvc.spec.storage_class_name,
                },
            )

        except ApiException as e:
            result.add_sub_test(
                "PVC Status",
                {
                    "success": False,
                    "message": f"Failed to read PVC status: {e.reason}",
                    "remediation": "Check if PVC was created successfully",
                },
            )

    def _test_pvc_deletion(
        self, v1: client.CoreV1Api, pvc_name: str, result: TestResult
    ):
        """Test PVC deletion (cleanup)"""
        try:
            v1.delete_namespaced_persistent_volume_claim(
                name=pvc_name, namespace=self.namespace
            )

            result.add_sub_test(
                "PVC Cleanup",
                {
                    "success": True,
                    "message": f"Successfully deleted test PVC '{pvc_name}'",
                    "pvc_name": pvc_name,
                },
            )

        except ApiException as e:
            result.add_sub_test(
                "PVC Cleanup",
                {
                    "success": False,
                    "message": f"Failed to delete PVC: {e.reason}",
                    "remediation": f"Manually clean up PVC '{pvc_name}' in namespace '{self.namespace}'",
                },
            )
