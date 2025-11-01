from typing import Optional, List
from uuid import UUID
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.repositories.repositories import ITaskRepository
from app.entities.task import Task, TaskStatus
from app.database.models import Task as TaskModel, TaskStatus as DBTaskStatus


class TaskRepository(ITaskRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, task: Task) -> None:
        model = TaskModel(
            id=UUID(task.id),
            work_id=UUID(task.work_id),
            payload=task.payload,
            status=DBTaskStatus(task.status.value),
            result_path=task.result_path,
            attempts=task.attempts,
            error=task.error,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        self.session.add(model)

    async def get(self, task_id: str) -> Optional[Task]:
        db_task = await self.session.get(TaskModel, UUID(task_id))
        if not db_task:
            return None
        task = Task(
            work_id=str(db_task.work_id),
            payload=db_task.payload,
        )
        task.id = str(db_task.id)
        task.status = TaskStatus(db_task.status.value)
        task.result_path = db_task.result_path
        task.attempts = db_task.attempts
        task.error = db_task.error
        task.created_at = db_task.created_at
        task.updated_at = db_task.updated_at
        return task

    async def update(self, task: Task) -> None:
        db_task = await self.session.get(TaskModel, UUID(task.id))
        if db_task:
            db_task.status = DBTaskStatus(task.status.value)
            db_task.result_path = task.result_path
            db_task.error = task.error
            db_task.attempts = task.attempts
            db_task.updated_at = task.updated_at
            await self.session.flush()

    async def list_by_work(self, work_id: str) -> List[Task]:
        result = await self.session.exec(
            select(TaskModel).where(TaskModel.work_id == UUID(work_id))
        )
        tasks = result.all()
        entities = []
        for db_task in tasks:
            task = Task(
                work_id=str(db_task.work_id),
                payload=db_task.payload,
            )
            task.id = str(db_task.id)
            task.status = TaskStatus(db_task.status.value)
            task.result_path = db_task.result_path
            task.attempts = db_task.attempts
            task.error = db_task.error
            task.created_at = db_task.created_at
            task.updated_at = db_task.updated_at
            entities.append(task)
        return entities
