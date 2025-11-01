from celery import shared_task
import psutil
import asyncio
from redis import asyncio as aioredis
from app.database.db import get_async_session
from app.database.models import Task, TaskStatus
from app.integrations.scraper import call_black_box
from app.celery.celery_app import broker_url

# ------------------------------
# Configuración Redis (async)
# ------------------------------
r = aioredis.from_url(broker_url, decode_responses=True)
TOKEN_KEY = "global:processing_tokens"

# ==============================
# Inicialización de tokens
# ==============================
async def set_initial_tokens():
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
        print(f"[WARN] Error inicializando tokens: {e}")
        if not await r.exists(TOKEN_KEY):
            await r.set(TOKEN_KEY, 1)

# ==============================
# Funciones ASÍNCRONAS para tokens
# ==============================
async def acquire_token() -> bool:
    async with r.pipeline() as pipe:
        while True:
            try:
                await pipe.watch(TOKEN_KEY)
                tokens = int(await r.get(TOKEN_KEY) or 0)
                if tokens <= 0:
                    await pipe.unwatch()
                    return False
                pipe.multi()
                pipe.decr(TOKEN_KEY)
                await pipe.execute()
                return True
            except aioredis.WatchError:
                continue

async def release_token():
    await r.incr(TOKEN_KEY)

# ==============================
# Tarea Celery
# ==============================
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_task(self, task_id: str):
    """
    Wrapper síncrono para Celery que ejecuta la tarea principal de forma async.
    """
    asyncio.run(_process_task_async(self, task_id))

# ==============================
# Función asíncrona interna
# ==============================
async def _process_task_async(self, task_id: str):
    async for db in get_async_session():
        db_task = await db.get(Task, task_id)  # Evitamos colisión de nombres
        if not db_task:
            return

        if not await acquire_token():
            print(f"No hay tokens, reintentando tarea {task_id}...")
            raise self.retry(countdown=30)

        try:
            # Actualizamos estado a RUNNING
            db_task.status = TaskStatus.RUNNING
            await db.commit()

            if not db_task.payload:
                raise ValueError("task.payload no puede ser None")

            # Ejecutamos función pesada sin bloquear el loop
            loop = asyncio.get_running_loop()
            result_path = await loop.run_in_executor(None, call_black_box, db_task.payload)

            # Guardamos resultado y marcamos completada
            db_task.result_path = result_path
            db_task.status = TaskStatus.COMPLETED
            await db.commit()

        except Exception as exc:
            db_task.attempts += 1
            db_task.status = TaskStatus.FAILED
            db_task.error = str(exc)
            await db.commit()
            raise self.retry(exc=exc)
        
        finally:
            await release_token()
