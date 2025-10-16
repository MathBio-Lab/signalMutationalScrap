from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.db import get_async_session
from app.repositories.repositories import IWorkRepository, ITaskRepository
from app.repositories.task import TaskRepository
from app.repositories.work import WorkRepository
from app.service.upload_csv import UploadCSVUseCase


async def get_task_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ITaskRepository:
    return TaskRepository(session)


async def get_work_repository(
    session: AsyncSession = Depends(get_async_session),
) -> IWorkRepository:
    return WorkRepository(session)


async def get_upload_csv_use_case(
    session: AsyncSession = Depends(get_async_session),
    work_repo: IWorkRepository = Depends(get_work_repository),
    task_repo: ITaskRepository = Depends(get_task_repository),
) -> UploadCSVUseCase:
    return UploadCSVUseCase(session, work_repo, task_repo)

