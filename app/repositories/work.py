from typing import Optional
from sqlmodel import select
from app.db import get_async_session
from domain.entities.work import Work
from domain.entities.task import Task
from application.repositories import IWorkRepository, ITaskRepository
from app.models import Work as WorkModel, Task as TaskModel


class SQLAlchemyWorkRepository(IWorkRepository):
    async def add(self, work: Work) -> None:
        async for session in get_async_session():
            model = WorkModel(
                id=work.id,
                filename=work.filename,
                storage_path=work.storage_path,
                status=work.status,
                output_path=work.output_path,
                error=work.error,
                created_at=work.created_at,
                updated_at=work.updated_at,
            )
            session.add(model)
            await session.commit()

    async def get(self, work_id: str) -> Optional[Work]:
        async for session in get_async_session():
            result = await session.get(WorkModel, work_id)
            if not result:
                return None
            # mapear a entidad de dominio
            return Work(
                filename=result.filename,
                storage_path=result.storage_path,
                max_tasks=result.max_tasks,
            )

    async def update(self, work: Work) -> None:
        async for session in get_async_session():
            db_work = await session.get(WorkModel, work.id)
            if db_work:
                db_work.status = work.status
                db_work.output_path = work.output_path
                db_work.error = work.error
                db_work.updated_at = work.updated_at
                await session.commit()
