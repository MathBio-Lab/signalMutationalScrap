from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.work import Work


class WorkRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, work: Work) -> Work:
        self.session.add(work)
        await self.session.commit()
        await self.session.refresh(work)
        return work

    async def get(self, work_id):
        result = await self.session.exec(select(Work).where(Work.id == work_id))
        return result.first()

    async def list(self):
        result = await self.session.exec(select(Work))
        return result.all()

    async def update(self, work: Work) -> Work:
        self.session.add(work)
        await self.session.commit()
        await self.session.refresh(work)
        return work

    async def delete(self, work_id):
        work = await self.get(work_id)
        if work:
            await self.session.delete(work)
            await self.session.commit()
        return work
