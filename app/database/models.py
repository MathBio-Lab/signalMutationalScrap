# enums
from enum import Enum


class WorkStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# Work (un upload de CSV - agrupa tasks)
class Work(Base):
    __tablename__ = "works"
    id = Column(UUID, primary_key=True, default=uuid4)
    filename = Column(String)
    storage_path = Column(String)        # ruta en S3 o local
    status = Column(Enum(WorkStatus), default=WorkStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    max_tasks = Column(Integer, nullable=True)  # valor que defines al crear
    output_path = Column(String, nullable=True) # si hay output global
    error = Column(Text, nullable=True)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(UUID, primary_key=True, default=uuid4)
    work_id = Column(UUID, ForeignKey("works.id"))
    payload = Column(JSON)               # fila del csv u otros datos
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    result_path = Column(String, nullable=True)  # path al output si aplica
    attempts = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
