from enum import Enum
from uuid import uuid4
from datetime import datetime

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Task:
    def __init__(self, work_id: str, payload: dict):
        self.id = str(uuid4())
        self.work_id = work_id
        self.payload = payload
        self.status = TaskStatus.PENDING
        self.result_path = None
        self.attempts = 0
        self.error = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def mark_running(self):
        self.status = TaskStatus.RUNNING
        self.updated_at = datetime.now()

    def mark_completed(self, result_path: str):
        self.status = TaskStatus.COMPLETED
        self.result_path = result_path
        self.updated_at = datetime.now()

    def mark_failed(self, error: str):
        self.status = TaskStatus.FAILED
        self.error = error
        self.updated_at = datetime.now()
