from typing import AsyncGenerator
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config.environment import settings

DB_URL = (
    f"postgresql+asyncpg://"
    f"{settings.DATABASE_USER}:"
    f"{settings.DATABASE_PASSWORD}@"
    f"{settings.DATABASE_HOST}:"
    f"{settings.DATABASE_PORT}/"
    f"{settings.DATABASE_NAME}"
)

# set up engine
engine = create_async_engine(
    DB_URL,
    echo=False,
    future=True,
    pool_size=5,  # conexiones permanentes en el pool
    max_overflow=10,  # conexiones adicionales permitidas si se satura el pool
    pool_timeout=30,  # segundos que espera antes de lanzar error si no hay conexiones libres
    pool_recycle=1800,  # recicla conexiones cada 30 min (evita timeouts del servidor)
    pool_pre_ping=True,  # verifica si la conexión sigue viva antes de usarla
)

# factory
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
