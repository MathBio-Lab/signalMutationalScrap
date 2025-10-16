from typing import Optional
from uuid import UUID
from sqlmodel.ext.asyncio.session import AsyncSession
from app.database.models import Work as WorkModel
from app.entities.work import Work as WorkEntity
from app.repositories.repositories import IWorkRepository
from app.database.models import WorkStatus as DbWorkStatus
from app.entities.work import WorkStatus as DomainWorkStatus


class WorkRepository(IWorkRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, work: WorkEntity) -> None:
        model = WorkModel(
            id=UUID(work.id),
            filename=work.filename,
            storage_path=work.storage_path,
            status=DbWorkStatus(work.status.value),
            output_path=work.output_path,
            error=work.error,
            created_at=work.created_at,
            updated_at=work.updated_at,
        )
        self.session.add(model)

    async def get(self, work_id: str) -> Optional[WorkEntity]:
        db_work = await self.session.get(WorkModel, UUID(work_id))

        if not db_work:
            return None

        # Crear la entidad con los valores requeridos
        work_entity = WorkEntity(
            filename=db_work.filename,
            storage_path=db_work.storage_path,
            max_tasks=db_work.max_tasks,
        )

        # Sobrescribir los valores generados por defecto
        work_entity.id = str(db_work.id)
        work_entity.status = DomainWorkStatus(db_work.status.value)
        work_entity.output_path = db_work.output_path
        work_entity.error = db_work.error
        work_entity.created_at = db_work.created_at
        work_entity.updated_at = db_work.updated_at

        return work_entity

    async def update(self, work: WorkEntity) -> None:
        db_work = await self.session.get(WorkModel, UUID(work.id))
        if db_work:
            db_work.status = DbWorkStatus(work.status.value)
            db_work.output_path = work.output_path
            db_work.error = work.error
            db_work.updated_at = work.updated_at
            await self.session.flush()
