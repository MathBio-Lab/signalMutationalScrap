from enum import Enum
from typing import Optional, Any
from uuid import UUID, uuid4
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship


class WorkStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Work(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    filename: str
    storage_path: str
    status: WorkStatus = Field(default=WorkStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    max_tasks: Optional[int] = None
    output_path: Optional[str] = None
    error: Optional[str] = None

    tasks: list["Task"] = Relationship(back_populates="work")


class Task(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    work_id: UUID = Field(foreign_key="works.id")
    payload: Any
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    result_path: Optional[str] = None
    attempts: int = Field(default=0)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # relación con Work
    work: Optional[Work] = Relationship(back_populates="tasks")
