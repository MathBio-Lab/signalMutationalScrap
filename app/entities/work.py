from enum import Enum
from uuid import uuid4
from datetime import datetime
from typing import List, Optional
from app.entities.task import Task, TaskStatus

class WorkStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Work:
    """Aggregate Root del procesamiento de un archivo CSV."""

    def __init__(
        self,
        filename: str,
        storage_path: str,
        max_tasks: Optional[int] = None,
    ):
        self.id = str(uuid4())
        self.filename = filename
        self.storage_path = storage_path
        self.status = WorkStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.max_tasks = max_tasks
        self.output_path: Optional[str] = None
        self.error: Optional[str] = None
        self.tasks: List[Task] = []

    # ---------------------------
    # Métodos de dominio (reglas)
    # ---------------------------

    def add_task(self, task: Task):
        """Asocia una tarea a este Work."""
        if self.max_tasks and len(self.tasks) >= self.max_tasks:
            raise ValueError("Se alcanzó el número máximo de tareas permitido.")
        self.tasks.append(task)
        self._update_status()
        self.updated_at = datetime.now()

    def mark_in_progress(self):
        self.status = WorkStatus.IN_PROGRESS
        self.updated_at = datetime.now()

    def mark_completed(self, output_path: str):
        """Marca el Work como completado y guarda el archivo resultante."""
        self.status = WorkStatus.COMPLETED
        self.output_path = output_path
        self.updated_at = datetime.now()

    def mark_failed(self, error: str):
        self.status = WorkStatus.FAILED
        self.error = error
        self.updated_at = datetime.now()

    def _update_status(self):
        """Actualiza el estado global según las tareas."""
        if all(t.status == TaskStatus.COMPLETED for t in self.tasks):
            self.status = WorkStatus.COMPLETED
        elif any(t.status == TaskStatus.RUNNING for t in self.tasks):
            self.status = WorkStatus.IN_PROGRESS
        elif any(t.status == TaskStatus.FAILED for t in self.tasks):
            self.status = WorkStatus.FAILED
        else:
            self.status = WorkStatus.PENDING
