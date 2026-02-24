import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from .base_test import BaseTest, TestResult


class PVCTest(BaseTest):
    """Test Kubernetes Persistent Volume Claims functionality"""

    def __init__(self):
        super().__init__()
        self.namespace = os.getenv("KUBERNETES_NAMESPACE", "default")
        self.storage_class = os.getenv("STORAGE_CLASS", "default")
        self.test_pvc_size = os.getenv("TEST_PVC_SIZE", "1Gi")
        self._k8s_configured: Optional[bool] = None

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

    def _load_k8s_config(self) -> bool:
        """Load Kubernetes config once and cache the result."""
        if self._k8s_configured is not None:
            return self._k8s_configured
        try:
            config.load_incluster_config()
            self._k8s_configured = True
        except config.ConfigException:
            try:
                config.load_kube_config()
                self._k8s_configured = True
            except (config.ConfigException, FileNotFoundError):
                self._k8s_configured = False
        return self._k8s_configured

    def is_configured(self) -> bool:
        """Check if Kubernetes is accessible"""
        return self._load_k8s_config()

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
            # Kubernetes config was already loaded by is_configured() / _load_k8s_config()
            self._load_k8s_config()
            result.add_log("INFO", "Kubernetes config loaded")

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

            # Determine overall status - focus on essential PVC operations
            # Storage class listing and namespace access may fail with limited RBAC (this is OK)
            # The critical tests are PVC creation, status, and cleanup
            essential_tests = ["PVC Creation", "PVC Status", "PVC Cleanup"]
            auxiliary_tests = ["List Storage Classes", "Namespace Access"]
            
            failed_essential_tests = []
            failed_auxiliary_tests = []
            limited_permissions_detected = False
            
            for name, test_result in result.sub_tests.items():
                if not test_result.get("success", False):
                    if name in essential_tests:
                        failed_essential_tests.append(name)
                    else:
                        failed_auxiliary_tests.append(name)
                elif test_result.get("limited_permissions", False):
                    limited_permissions_detected = True

            if not failed_essential_tests:
                if limited_permissions_detected:
                    success_message = "PVC tests completed successfully (using least-privilege RBAC policy)"
                    additional_info = {
                        "namespace": self.namespace,
                        "storage_class": self.storage_class,
                        "security_note": "Using namespace-scoped permissions - recommended configuration",
                    }
                else:
                    success_message = "All PVC tests passed successfully"
                    additional_info = {
                        "namespace": self.namespace,
                        "storage_class": self.storage_class,
                    }
                
                result.complete(True, success_message, additional_info)
            else:
                # Only fail if essential PVC operations don't work
                result.fail(
                    f"Essential PVC operations failed: {', '.join(failed_essential_tests)}",
                    remediation="Check RBAC permissions for PVC operations and storage class availability",
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
            # Handle RBAC permission limitations gracefully
            if e.status == 403:  # Forbidden - RBAC limitation
                result.add_sub_test(
                    "List Storage Classes",
                    {
                        "success": True,
                        "message": "Skipped: Limited RBAC permissions (security best practice)",
                        "details": {
                            "note": "Using namespace-scoped permissions instead of cluster-wide access",
                            "recommendation": "This is a recommended secure RBAC configuration",
                            "configured_class": self.storage_class,
                        },
                        "limited_permissions": True,
                    },
                )
            else:
                result.add_sub_test(
                    "List Storage Classes",
                    {
                        "success": False,
                        "message": f"Failed to list storage classes: {e.reason}",
                        "remediation": "Check cluster configuration and storage class availability",
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
            # Handle RBAC permission limitations gracefully
            if e.status == 403:  # Forbidden - may still have PVC permissions within namespace
                result.add_sub_test(
                    "Namespace Access",
                    {
                        "success": True,
                        "message": f"Limited namespace read permissions (proceeding with PVC test)",
                        "details": {
                            "note": f"Cannot read namespace '{self.namespace}' metadata but may still have PVC permissions",
                            "recommendation": "This is acceptable for namespace-scoped RBAC policies",
                        },
                        "limited_permissions": True,
                    },
                )
            else:
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
