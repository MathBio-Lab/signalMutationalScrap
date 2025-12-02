from celery import shared_task
import psutil
import asyncio
from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.db import DB_URL
from app.database.models import Task, TaskStatus
from app.integrations.scraper_service import run_scraper_job
from app.celery.celery_app import broker_url

# ------------------------------
# Configuración Redis
# ------------------------------
TOKEN_KEY = "global:processing_tokens"

# ==============================
# Inicialización de tokens
# ==============================
async def set_initial_tokens():
    """Inicializa tokens en Redis basado en RAM disponible"""
    r = aioredis.from_url(broker_url, decode_responses=True)
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
    finally:
        await r.aclose()

# ==============================
# Funciones ASÍNCRONAS para tokens
# ==============================
async def acquire_token(redis_client: aioredis.Redis) -> bool:
    """Intenta adquirir un token del pool usando transacciones Redis"""
    async with redis_client.pipeline() as pipe:
        while True:
            try:
                await pipe.watch(TOKEN_KEY)
                tokens = int(await redis_client.get(TOKEN_KEY) or 0)
                if tokens <= 0:
                    await pipe.unwatch()
                    return False
                pipe.multi()
                pipe.decr(TOKEN_KEY)
                await pipe.execute()
                return True
            except aioredis.WatchError:
                continue

async def release_token(redis_client: aioredis.Redis):
    """Libera un token de vuelta al pool"""
    await redis_client.incr(TOKEN_KEY)

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
    # Crear un engine y sessionmaker locales para este loop
    engine = create_async_engine(DB_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    # Crear cliente Redis local para este loop
    redis_client = aioredis.from_url(broker_url, decode_responses=True)
    
    db_task = None
    
    try:
        async with async_session() as db:
            db_task = await db.get(Task, task_id)
            
            if not db_task:
                print(f"[ERROR] Task {task_id} not found in database")
                return

            if not await acquire_token(redis_client):
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
                await release_token(redis_client)
            
    except Exception as exc:
        # Error al conectar a la DB o error general fuera del bloque interno
        print(f"[CRITICAL ERROR] Failed to process task {task_id}: {exc}")
        
        # Intentar actualizar el estado si es posible (creando nueva sesión si es necesario)
        try:
            async with async_session() as db_err:
                task_err = await db_err.get(Task, task_id)
                if task_err:
                    task_err.status = TaskStatus.FAILED
                    task_err.error = f"Error crítico: {str(exc)}"
                    await db_err.commit()
        except Exception as commit_error:
            print(f"[ERROR] Could not update task status: {commit_error}")
        
        raise
    
    finally:
        # Importante: cerrar el engine local y el cliente Redis
        await engine.dispose()
        await redis_client.aclose()


