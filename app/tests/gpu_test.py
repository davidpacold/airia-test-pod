import os
import subprocess
from typing import Any, Dict

from .base_test import BaseTest, TestResult


class GPUTest(BaseTest):
    """Test GPU availability and configuration"""

    def __init__(self):
        super().__init__()
        self.require_gpu = os.getenv("GPU_REQUIRED", "false").lower() == "true"

    @property
    def test_name(self) -> str:
        return "GPU Detection"

    @property
    def test_description(self) -> str:
        return "Detects and validates GPU availability, driver, and CUDA installation"

    @property
    def test_id(self) -> str:
        return "gpu"

    @property
    def is_optional(self) -> bool:
        # If GPU is not required, make this test optional
        return not self.require_gpu

    @property
    def timeout_seconds(self) -> int:
        return 30

    def is_configured(self) -> bool:
        """Always run GPU detection test"""
        # Always return True so the test runs and reports GPU presence
        return True

    def get_configuration_help(self) -> str:
        return (
            "GPU detection test always runs and reports GPU presence. "
            "To allocate a GPU to the pod, add 'nvidia.com/gpu: 1' to resources.requests in values.yaml. "
            "Set GPU_REQUIRED=true to fail the test if no GPU is found. "
            "Requires NVIDIA drivers and GPU-enabled Kubernetes node."
        )

    def run_test(self) -> TestResult:
        result = TestResult(self.test_name)
        result.start()

        try:
            # Test 1: Check nvidia-smi availability
            nvidia_smi_result = self._test_nvidia_smi_availability()
            result.add_sub_test("nvidia-smi Availability", nvidia_smi_result)

            if not nvidia_smi_result["success"]:
                # nvidia-smi not available - no GPU detected
                if self.require_gpu:
                    result.fail(
                        "GPU required but nvidia-smi command not available",
                        remediation="Install NVIDIA drivers and ensure pod is on a GPU node with GPU resources requested",
                    )
                else:
                    result.complete(
                        True,
                        "No GPU detected (nvidia-smi not available)",
                        {"gpu_detected": False, "gpu_count": 0},
                    )
                return result

            # Test 2: Detect GPUs
            gpu_detection_result = self._test_gpu_detection()
            result.add_sub_test("GPU Detection", gpu_detection_result)

            if not gpu_detection_result["success"]:
                # nvidia-smi available but no GPUs found
                if self.require_gpu:
                    result.fail(
                        "GPU required but no GPUs detected",
                        remediation="Ensure pod has GPU resources requested (nvidia.com/gpu: 1) and node has GPUs",
                    )
                else:
                    result.complete(
                        True,
                        "No GPU detected",
                        {"gpu_detected": False, "gpu_count": 0},
                    )
                return result

            gpu_count = gpu_detection_result.get("gpu_count", 0)
            result.add_log("INFO", f"Detected {gpu_count} GPU(s)")

            # Test 3: Get driver version
            driver_result = self._test_driver_version()
            result.add_sub_test("Driver Version", driver_result)

            # Test 4: Get CUDA version
            cuda_result = self._test_cuda_version()
            result.add_sub_test("CUDA Version", cuda_result)

            # Test 5: Get GPU details for each GPU
            for i in range(gpu_count):
                gpu_details_result = self._test_gpu_details(i)
                result.add_sub_test(f"GPU {i} Details", gpu_details_result)

            # Determine overall success
            all_critical_passed = (
                nvidia_smi_result["success"]
                and gpu_detection_result["success"]
                and driver_result["success"]
            )

            if all_critical_passed:
                result.complete(
                    True,
                    f"GPU detected - {gpu_count} GPU(s) available",
                    {
                        "gpu_detected": True,
                        "gpu_count": gpu_count,
                        "driver_version": driver_result.get("driver_version"),
                        "cuda_version": cuda_result.get("cuda_version"),
                    },
                )
            else:
                if self.require_gpu:
                    result.fail(
                        "GPU validation failed",
                        remediation="Check GPU availability, drivers, and CUDA installation",
                    )
                else:
                    result.complete(
                        True,
                        "GPU detection incomplete",
                        {"gpu_detected": True, "gpu_count": gpu_count, "warnings": True},
                    )

        except Exception as e:
            if self.require_gpu:
                result.fail(
                    f"GPU test failed: {str(e)}",
                    error=e,
                    remediation="Check NVIDIA drivers, GPU availability, and nvidia-smi installation",
                )
            else:
                result.complete(
                    True,
                    f"No GPU detected (error during detection: {str(e)})",
                    {"gpu_detected": False, "gpu_count": 0, "error": str(e)},
                )

        return result

    def _test_nvidia_smi_availability(self) -> Dict[str, Any]:
        """Test if nvidia-smi command is available"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "nvidia-smi is available",
                    "output": result.stdout.strip(),
                }
            else:
                return {
                    "success": False,
                    "message": "nvidia-smi command failed",
                    "error": result.stderr.strip(),
                    "remediation": "Install NVIDIA drivers",
                }

        except FileNotFoundError:
            return {
                "success": False,
                "message": "nvidia-smi not found",
                "remediation": "Install NVIDIA drivers and ensure nvidia-smi is in PATH",
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "nvidia-smi command timed out",
                "remediation": "Check GPU driver status",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to check nvidia-smi: {str(e)}",
                "error": str(e),
            }

    def _test_gpu_detection(self) -> Dict[str, Any]:
        """Test GPU detection and count"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=count", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "message": "Failed to query GPU count",
                    "error": result.stderr.strip(),
                }

            # Count number of GPUs by listing them
            gpu_list_result = subprocess.run(
                ["nvidia-smi", "--list-gpus"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if gpu_list_result.returncode == 0:
                gpu_lines = [
                    line
                    for line in gpu_list_result.stdout.strip().split("\n")
                    if line.strip()
                ]
                gpu_count = len(gpu_lines)

                if gpu_count > 0:
                    return {
                        "success": True,
                        "message": f"Detected {gpu_count} GPU(s)",
                        "gpu_count": gpu_count,
                        "gpu_list": gpu_lines,
                    }
                else:
                    return {
                        "success": False,
                        "message": "No GPUs detected",
                        "gpu_count": 0,
                        "remediation": "Ensure pod is scheduled on a GPU node with nvidia.com/gpu resource request",
                    }
            else:
                return {
                    "success": False,
                    "message": "Failed to list GPUs",
                    "error": gpu_list_result.stderr.strip(),
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "GPU detection timed out",
                "remediation": "Check GPU driver status",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"GPU detection failed: {str(e)}",
                "error": str(e),
            }

    def _test_driver_version(self) -> Dict[str, Any]:
        """Test NVIDIA driver version"""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=driver_version",
                    "--format=csv,noheader",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                driver_version = result.stdout.strip().split("\n")[0]
                return {
                    "success": True,
                    "message": f"Driver version: {driver_version}",
                    "driver_version": driver_version,
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to get driver version",
                    "error": result.stderr.strip(),
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to check driver version: {str(e)}",
                "error": str(e),
            }

    def _test_cuda_version(self) -> Dict[str, Any]:
        """Test CUDA version using a single nvidia-smi call"""
        try:
            # Single call to get both compute capability and full output for CUDA version
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            cuda_version = "Unknown"
            compute_capability = None

            if result.returncode == 0:
                # Parse CUDA version from nvidia-smi output header
                for line in result.stdout.split("\n"):
                    if "CUDA Version:" in line:
                        cuda_version = line.split("CUDA Version:")[1].strip().split()[0]
                        break

            # Get compute capability via query flag (lightweight additional call)
            cap_result = subprocess.run(
                ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if cap_result.returncode == 0:
                compute_capability = cap_result.stdout.strip().split("\n")[0]

            return {
                "success": True,
                "message": f"CUDA version: {cuda_version}",
                "cuda_version": cuda_version,
                "compute_capability": compute_capability,
            }

        except Exception as e:
            return {
                "success": True,  # Don't fail the test if CUDA version check fails
                "message": f"Could not determine CUDA version: {str(e)}",
                "warning": True,
            }

    def _test_gpu_details(self, gpu_index: int) -> Dict[str, Any]:
        """Get detailed information about a specific GPU"""
        try:
            # Query multiple GPU properties
            query_fields = [
                "name",
                "memory.total",
                "memory.used",
                "memory.free",
                "utilization.gpu",
                "utilization.memory",
                "temperature.gpu",
                "power.draw",
                "power.limit",
            ]

            result = subprocess.run(
                [
                    "nvidia-smi",
                    f"--id={gpu_index}",
                    f"--query-gpu={','.join(query_fields)}",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "message": f"Failed to query GPU {gpu_index} details",
                    "error": result.stderr.strip(),
                }

            # Parse the output
            values = result.stdout.strip().split(", ")

            if len(values) >= len(query_fields):
                memory_total_mb = float(values[1]) if values[1] != "[N/A]" else 0
                memory_used_mb = float(values[2]) if values[2] != "[N/A]" else 0
                memory_free_mb = float(values[3]) if values[3] != "[N/A]" else 0
                gpu_util = values[4] if values[4] != "[N/A]" else "N/A"
                memory_util = values[5] if values[5] != "[N/A]" else "N/A"
                temperature = values[6] if values[6] != "[N/A]" else None
                power_draw = values[7] if values[7] != "[N/A]" else "N/A"
                power_limit = values[8] if values[8] != "[N/A]" else "N/A"

                return {
                    "success": True,
                    "message": f"GPU {gpu_index}: {values[0]}",
                    "gpu_name": values[0],
                    "memory_total_mb": memory_total_mb,
                    "memory_total_gb": round(memory_total_mb / 1024, 2),
                    "memory_used_mb": memory_used_mb,
                    "memory_used_gb": round(memory_used_mb / 1024, 2),
                    "memory_free_mb": memory_free_mb,
                    "memory_free_gb": round(memory_free_mb / 1024, 2),
                    "utilization_gpu_percent": gpu_util,
                    "utilization_memory_percent": memory_util,
                    "temperature_celsius": int(temperature) if temperature else None,
                    "power_draw_watts": power_draw,
                    "power_limit_watts": power_limit,
                }
            else:
                return {
                    "success": False,
                    "message": f"Unexpected output format from nvidia-smi for GPU {gpu_index}",
                    "raw_output": result.stdout.strip(),
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get GPU {gpu_index} details: {str(e)}",
                "error": str(e),
            }
