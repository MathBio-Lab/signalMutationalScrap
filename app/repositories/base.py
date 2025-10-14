# repositories/base.py
from typing import TypeVar, Generic, Type, List, Optional
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id) -> Optional[ModelType]:
        result = await self.session.exec(select(self.model).where(self.model.id == id))
        return result.first()

    async def list(self) -> List[ModelType]:
        result = await self.session.exec(select(self.model))
        return result.all()

    async def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id) -> Optional[ModelType]:
        obj = await self.get(id)
        if obj:
            await self.session.delete(obj)
            await self.session.commit()
        return obj
