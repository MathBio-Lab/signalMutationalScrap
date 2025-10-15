from typing import Optional
from sqlmodel import select
from app.database.db import get_async_session
from app.entities.work import Work
from app.entities.task import Task
from app.repositories.repositories import IWorkRepository, ITaskRepository
from app.database.models import Work as WorkModel, Task as TaskModel


class SQLAlchemyTaskRepository(ITaskRepository):
    async def add(self, task: Task) -> None:
        async for session in get_async_session():
            model = TaskModel(
                id=task.id,
                work_id=task.work_id,
                payload=task.payload,
                status=task.status,
                result_path=task.result_path,
                attempts=task.attempts,
                error=task.error,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            session.add(model)
            await session.commit()

    async def get(self, task_id: str) -> Optional[Task]:
        async for session in get_async_session():
            db_task = await session.get(TaskModel, task_id)
            if not db_task:
                return None
            return Task(
                work_id=db_task.work_id,
                payload=db_task.payload,
            )

    async def update(self, task: Task) -> None:
        async for session in get_async_session():
            db_task = await session.get(TaskModel, task.id)
            if db_task:
                db_task.status = task.status
                db_task.result_path = task.result_path
                db_task.error = task.error
                db_task.updated_at = task.updated_at
                await session.commit()
