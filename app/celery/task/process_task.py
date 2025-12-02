from celery import shared_task
import psutil
import asyncio
from redis import asyncio as aioredis
from app.database.db import get_async_session
from app.database.models import Task, TaskStatus
from app.integrations.scraper_service import run_scraper_job
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
    db_task = None
    db = None
    
    try:
        async for session in get_async_session():
            db = session
            db_task = await db.get(Task, task_id)
            break
            
        if not db_task:
            print(f"[ERROR] Task {task_id} not found in database")
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
            result_path = await loop.run_in_executor(
                None, 
                run_scraper_job, 
                db_task.payload["csv_path"],
                str(db_task.work_id)
            )

            # Guardamos resultado y marcamos completada
            db_task.result_path = result_path
            db_task.status = TaskStatus.COMPLETED
            await db.commit()
            print(f"[SUCCESS] Task {task_id} completed successfully")

        except Exception as exc:
            print(f"[ERROR] Task {task_id} failed: {exc}")
            db_task.attempts += 1
            db_task.status = TaskStatus.FAILED
            db_task.error = str(exc)
            await db.commit()
            raise self.retry(exc=exc)
        
        finally:
            await release_token()
            
    except Exception as exc:
        # Error al conectar a la DB o error general
        print(f"[CRITICAL ERROR] Failed to process task {task_id}: {exc}")
        
        # Intentar actualizar el estado si tenemos la tarea
        if db_task and db:
            try:
                db_task.status = TaskStatus.FAILED
                db_task.error = f"Error crítico: {str(exc)}"
                await db.commit()
            except Exception as commit_error:
                print(f"[ERROR] Could not update task status: {commit_error}")
        
        raise
