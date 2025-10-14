from typing import AsyncGenerator
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from app.config.environment import settings

DB_URL = (
    f"postgresql+asyncpg://"
    f"{settings.DATABASE_USER}:"
    f"{settings.DATABASE_PASSWORD}@"
    f"{settings.DATABASE_HOST}:"
    f"{settings.DATABASE_PORT}/"
    f"{settings.DATABASE_NAME}"
)

# Crear el engine asíncrono
engine = create_async_engine(DB_URL, echo=False, future=True)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
