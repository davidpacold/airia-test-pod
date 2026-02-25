"""Pod diagnostics collection module.

Runs the extract-pod-details.sh script to collect comprehensive pod
diagnostics from a target Kubernetes namespace, then packages the
results as a downloadable tar.gz archive.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tarfile
import threading
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCRIPT_PATH = Path("/app/scripts/extract-pod-details.sh")
# Fallback for local development
if not SCRIPT_PATH.exists():
    SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "extract-pod-details.sh"

OUTPUT_BASE = Path("/tmp/diagnostics")

# Namespace validation: alphanumeric, hyphens, max 63 chars (K8s DNS label)
_NS_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]{0,61}[a-z0-9]$|^[a-z0-9]$")

# Valid --since duration pattern (e.g., 1h, 6h, 24h, 30m, 1h30m)
_SINCE_PATTERN = re.compile(r"^[0-9]+[hms]([0-9]+[hms])?$")


class DiagnosticsState(str, Enum):
    IDLE = "idle"
    COLLECTING = "collecting"
    READY = "ready"
    ERROR = "error"


class DiagnosticsCollector:
    """Thread-safe diagnostics collector singleton."""

    def __init__(self):
        self._lock = threading.Lock()
        self._state = DiagnosticsState.IDLE
        self._archive_path: Optional[str] = None
        self._error_message: Optional[str] = None
        self._namespace: Optional[str] = None
        self._pod_count: int = 0
        self._thread: threading.Thread | None = None

    @property
    def state(self) -> dict:
        with self._lock:
            return {
                "state": self._state.value,
                "namespace": self._namespace,
                "pod_count": self._pod_count,
                "error": self._error_message,
                "archive_ready": self._archive_path is not None
                    and Path(self._archive_path).exists(),
            }

    def collect(self, namespace: str, since: Optional[str] = None) -> dict:
        """Start diagnostics collection in a background thread."""
        if not _NS_PATTERN.match(namespace):
            return {"error": "Invalid namespace format", "state": "error"}

        if since and not _SINCE_PATTERN.match(since):
            return {"error": "Invalid --since format (use e.g. 1h, 6h, 24h)", "state": "error"}

        with self._lock:
            if self._state == DiagnosticsState.COLLECTING:
                return {"error": "Collection already in progress", "state": "collecting"}
            self._state = DiagnosticsState.COLLECTING
            self._namespace = namespace
            self._pod_count = 0
            self._error_message = None
            self._archive_path = None

        self._thread = threading.Thread(
            target=self._run_collection,
            args=(namespace, since),
            daemon=True,
        )
        self._thread.start()

        return {"state": "collecting", "namespace": namespace}

    def _run_collection(self, namespace: str, since: Optional[str]):
        """Execute the diagnostics script and create archive."""
        try:
            # Clean up old output
            if OUTPUT_BASE.exists():
                shutil.rmtree(OUTPUT_BASE, ignore_errors=True)
            OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

            cmd = ["bash", str(SCRIPT_PATH), namespace, str(OUTPUT_BASE)]
            if since:
                cmd.append(f"--since={since}")

            logger.info(f"Running diagnostics: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode != 0:
                logger.error(f"Diagnostics script failed: {result.stderr}")
                with self._lock:
                    self._state = DiagnosticsState.ERROR
                    self._error_message = result.stderr[:500] or "Script failed"
                return

            # Find the output directory (timestamp-based)
            output_dirs = sorted(
                [d for d in OUTPUT_BASE.iterdir() if d.is_dir()],
                key=lambda d: d.name,
                reverse=True,
            )

            if not output_dirs:
                with self._lock:
                    self._state = DiagnosticsState.ERROR
                    self._error_message = "No output directory created"
                return

            output_dir = output_dirs[0]

            # Count pods
            pods_dir = output_dir / "pods"
            pod_count = len(list(pods_dir.iterdir())) if pods_dir.exists() else 0

            # Create tar.gz archive
            archive_path = str(output_dir) + ".tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(str(output_dir), arcname=f"diagnostics-{namespace}-{output_dir.name}")

            with self._lock:
                self._state = DiagnosticsState.READY
                self._archive_path = archive_path
                self._pod_count = pod_count

            logger.info(f"Diagnostics complete: {pod_count} pods, archive at {archive_path}")

        except subprocess.TimeoutExpired:
            with self._lock:
                self._state = DiagnosticsState.ERROR
                self._error_message = "Collection timed out after 5 minutes"
        except Exception as e:
            logger.exception("Diagnostics collection failed")
            with self._lock:
                self._state = DiagnosticsState.ERROR
                self._error_message = str(e)[:500]

    def get_archive_path(self) -> Optional[str]:
        with self._lock:
            if self._state == DiagnosticsState.READY and self._archive_path:
                if Path(self._archive_path).exists():
                    return self._archive_path
            return None

    def get_archive_filename(self) -> str:
        with self._lock:
            ns = self._namespace or "unknown"
            return f"diagnostics-{ns}.tar.gz"


# Singleton instance
diagnostics_collector = DiagnosticsCollector()
