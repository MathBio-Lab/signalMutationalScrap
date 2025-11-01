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
    """
    Inicializa el número de tokens disponibles según la RAM libre.
    Esta función AHORA se llama desde el evento startup de FastAPI.
    """
    try:
        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024**3)  # RAM disponible en GB
        tokens = max(1, int(available_gb // 2))  # 1 token por cada 2 GB libres

        if not await r.exists(TOKEN_KEY):
            await r.set(TOKEN_KEY, tokens)
            print(f"[INIT] Tokens inicializados a {tokens} según RAM disponible.")
        else:
            current = int(await r.get(TOKEN_KEY) or 0)
            print(f"[INIT] Tokens existentes detectados: {current}. No se modifican.")
    except Exception as e:
        print(f"[WARN] Error inicializando tokens: {e}")
        # Aseguramos que haya al menos 1 token
        if not await r.exists(TOKEN_KEY):
            await r.set(TOKEN_KEY, 1)

# ==============================
# Funciones ASÍNCRONAS para tokens
# ==============================
async def acquire_token():
    """
    Intenta adquirir un token de Redis para ejecutar una tarea.
    Devuelve True si se pudo adquirir, False si no hay tokens disponibles.
    (Versión asíncrona nativa)
    """
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
                # Si alguien más modificó la clave, reintentamos
                continue

async def release_token():
    """
    Libera un token de Redis, aumentando el contador disponible.
    (Versión asíncrona nativa)
    """
    await r.incr(TOKEN_KEY)

# ==============================
# Tarea Celery
# ==============================
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_task(self, task_id: str):
    """
    Wrapper síncrono para Celery que ejecuta la tarea principal de forma async.
    """
    # Esta es la única vez que asyncio.run() es correcto, 
    # ya que es el puente entre el worker síncrono de Celery y nuestro código async.
    asyncio.run(_process_task_async(self, task_id))


async def _process_task_async(self, task_id: str):
    """
    Lógica principal de la tarea, ejecutada de manera asíncrona.
    ...
    """
    async for db in get_async_session():
        task = await db.get(Task, task_id)
        if not task:
            return

        # <--- CAMBIO IMPORTANTE: Usamos 'await'
        if not await acquire_token():
            print(f"No hay tokens, reintentando tarea {task_id}...")
            raise self.retry(countdown=30)

        try:
            # Actualizamos el estado a RUNNING
            task.status = TaskStatus.RUNNING
            await db.commit()

            if not task.payload:
                raise ValueError("task.payload no puede ser None")

            # Ejecutamos la función pesada en un executor para no bloquear el loop
            loop = asyncio.get_running_loop()
            result_path = await loop.run_in_executor(None, call_black_box, task.payload)

            # Guardamos resultado y marcamos completada
            task.result_path = result_path
            task.status = TaskStatus.COMPLETED
            await db.commit()

        except Exception as exc:
            # Actualizamos la tarea como fallida y contamos el intento
            task.attempts += 1
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            await db.commit()
            raise self.retry(exc=exc)
        
        finally:
            # <--- CAMBIO IMPORTANTE: Usamos 'await'
            await release_token()