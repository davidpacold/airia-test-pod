from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestResult(BaseModel):
    test_name: str
    test_description: str
    status: TestStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    remediation: Optional[str] = None


class TestSuiteResult(BaseModel):
    suite_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    tests: Dict[str, TestResult]
    overall_status: TestStatus


class TestRunRequest(BaseModel):
    test_names: Optional[List[str]] = None  # If None, run all tests
