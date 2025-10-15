from fastapi import Depends
from infrastructure.repositories.sqlalchemy_repositories import (
    SQLAlchemyWorkRepository,
    SQLAlchemyTaskRepository,
)
from application.use_cases.upload_csv import UploadCSVUseCase


# Repositorios
async def get_work_repo() -> SQLAlchemyWorkRepository:
    return SQLAlchemyWorkRepository()

async def get_task_repo() -> SQLAlchemyTaskRepository:
    return SQLAlchemyTaskRepository()


# Caso de uso (inyección de repositorios)
async def get_upload_csv_use_case(
    work_repo: SQLAlchemyWorkRepository = Depends(get_work_repo),
    task_repo: SQLAlchemyTaskRepository = Depends(get_task_repo),
) -> UploadCSVUseCase:
    return UploadCSVUseCase(work_repo=work_repo, task_repo=task_repo)
