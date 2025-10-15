from celery import shared_task
import psutil
import asyncio
from redis import asyncio as aioredis
from app.database.db import get_async_session
from app.database.models import Task, TaskStatus
from app.integrations.scraper import call_black_box
from celery_app import celery

r = aioredis.Redis()
TOKEN_KEY = "global:processing_tokens"


async def set_initial_tokens():
    """Configura el número de tokens según la RAM disponible."""
    try:
        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024**3)

        tokens = max(1, int(available_gb // 2))

        if not await r.exists(TOKEN_KEY):
            await r.set(TOKEN_KEY, tokens)
            print(f"[INIT] Tokens inicializados a {tokens} según RAM disponible.")
        else:
            current = int(await r.get(TOKEN_KEY) or 0)
            print(f"[INIT] Tokens existentes detectados: {current}. No se modifican.")
    except Exception as e:
        if not await r.exists(TOKEN_KEY):
            await r.set(TOKEN_KEY, 1)
        print(
            f"[WARN] No se pudo calcular tokens dinámicamente ({e}). Se usa 1 por defecto."
        )


# --- Inicialización segura ---
def init_tokens_sync():
    """Ejecuta la inicialización async de tokens de forma segura al inicio."""
    try:
        asyncio.run(set_initial_tokens())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.create_task(set_initial_tokens())


init_tokens_sync()


# --- Funciones síncronas (para usar dentro de Celery) ---
def acquire_token():
    """Versión síncrona usando asyncio para compatibilidad con Celery."""

    async def _acquire():
        async with r.pipeline() as pipe:
            while True:
                try:
                    await pipe.watch(TOKEN_KEY)
                    value = await r.get(TOKEN_KEY)
                    tokens = int(value or 0)
                    if tokens <= 0:
                        await pipe.unwatch()
                        return False
                    pipe.multi()
                    pipe.decr(TOKEN_KEY)
                    await pipe.execute()
                    return True
                except aioredis.WatchError:
                    continue

    return asyncio.run(_acquire())


def release_token():
    """Libera un token (versión síncrona)."""

    async def _release():
        await r.incr(TOKEN_KEY)

    asyncio.run(_release())


# --- Tarea Celery ---
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_task(self, task_id: str):
    """Celery ejecuta esto (sincrónico), pero adentro lanzamos asyncio."""
    asyncio.run(_process_task_async(self, task_id))


async def _process_task_async(self, task_id: str):
    """Lógica principal asíncrona compatible con SQLAlchemy async."""
    async for db in get_async_session():
        task = await db.get(Task, task_id)
        if not task:
            return

        if not acquire_token():
            raise self.retry(countdown=30)

        try:
            task.status = TaskStatus.RUNNING
            await db.commit()

            if not task.payload:
                raise ValueError("task.payload no puede ser None")

            loop = asyncio.get_running_loop()
            result_path = await loop.run_in_executor(None, call_black_box, task.payload)

            task.result_path = result_path
            task.status = TaskStatus.COMPLETED
            await db.commit()

        except Exception as exc:
            task.attempts += 1
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            await db.commit()
            raise self.retry(exc=exc)
        finally:
            release_token()
