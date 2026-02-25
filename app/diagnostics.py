"""Pod diagnostics collection module.

Runs the extract-pod-details.sh script to collect comprehensive pod
diagnostics from a target Kubernetes namespace, then packages the
results as a downloadable tar.gz archive.

Progress is streamed from the script via PROGRESS: lines and exposed
through the status API for real-time UI feedback.
"""

from __future__ import annotations

import logging
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
        self._total_pods: int = 0
        self._current_step: str = ""
        self._current_detail: str = ""
        self._completed_steps: list[str] = []
        self._thread: Optional[threading.Thread] = None

    @property
    def state(self) -> dict:
        with self._lock:
            return {
                "state": self._state.value,
                "namespace": self._namespace,
                "pod_count": self._pod_count,
                "total_pods": self._total_pods,
                "current_step": self._current_step,
                "current_detail": self._current_detail,
                "completed_steps": list(self._completed_steps),
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
            self._total_pods = 0
            self._current_step = "init"
            self._current_detail = "Starting collection..."
            self._completed_steps = []
            self._error_message = None
            self._archive_path = None

        self._thread = threading.Thread(
            target=self._run_collection,
            args=(namespace, since),
            daemon=True,
        )
        self._thread.start()

        return {"state": "collecting", "namespace": namespace}

    def _update_progress(self, step: str, detail: str):
        """Update current progress from a PROGRESS: line."""
        with self._lock:
            # Track completed steps
            if self._current_step and self._current_step != step:
                if self._current_step not in self._completed_steps:
                    self._completed_steps.append(self._current_step)
            self._current_step = step
            self._current_detail = detail

            # Parse pod counts from discover step
            if step == "discover" and "Found" in detail:
                try:
                    self._total_pods = int(detail.split("Found")[1].split("pods")[0].strip())
                except (ValueError, IndexError):
                    pass

            # Parse pod progress
            if step in ("pod", "pod-done") and "/" in detail:
                try:
                    self._pod_count = int(detail.split("/")[0])
                except (ValueError, IndexError):
                    pass

    def _run_collection(self, namespace: str, since: Optional[str]):
        """Execute the diagnostics script, streaming progress."""
        try:
            # Clean up old output
            if OUTPUT_BASE.exists():
                shutil.rmtree(OUTPUT_BASE, ignore_errors=True)
            OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

            cmd = ["bash", str(SCRIPT_PATH), namespace, str(OUTPUT_BASE)]
            if since:
                cmd.append(f"--since={since}")

            logger.info(f"Running diagnostics: {' '.join(cmd)}")

            # Stream stdout line-by-line for progress updates
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            for line in proc.stdout:
                line = line.strip()
                if line.startswith("PROGRESS:"):
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        self._update_progress(parts[1], parts[2])

            proc.wait(timeout=300)

            if proc.returncode != 0:
                stderr = proc.stderr.read() if proc.stderr else ""
                logger.error(f"Diagnostics script failed: {stderr}")
                with self._lock:
                    self._state = DiagnosticsState.ERROR
                    self._error_message = stderr[:500] or "Script failed"
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

            # Count pods (one .txt per pod, excluding _extraction-info.txt)
            pod_count = len([
                f for f in output_dir.iterdir()
                if f.suffix == ".txt" and not f.name.startswith("_")
                and f.name not in (
                    "namespace-events.txt", "services.txt",
                    "configmaps-list.txt", "secrets-list.txt",
                )
            ])

            # Create tar.gz archive
            self._update_progress("archive", "Creating archive...")
            archive_path = str(output_dir) + ".tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(str(output_dir), arcname=f"diagnostics-{namespace}-{output_dir.name}")

            with self._lock:
                self._state = DiagnosticsState.READY
                self._archive_path = archive_path
                self._pod_count = pod_count
                self._current_step = "complete"
                self._current_detail = f"{pod_count} pods collected"
                if "archive" not in self._completed_steps:
                    self._completed_steps.append("archive")

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
