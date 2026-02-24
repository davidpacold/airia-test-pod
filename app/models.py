from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class TestRunRequest(BaseModel):
    test_names: Optional[List[str]] = None  # If None, run all tests
