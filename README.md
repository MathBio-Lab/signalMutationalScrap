Rate limit realista: por ejemplo 1 petición cada 1–3s. Para 2000 IDs, a 2s por petición tardas ~66 minutos. Ajusta expectativas.
Cacheamos resultados

Pedir permiso o solicitar un endpoint batch al propietario del sitio.
Consumo de API (si existe).# signalMutationalScrap

1. Diagrama lógico (resumen)

Cliente → FastAPI

/upload sube CSV

/status/{idwork} consulta estado

/download/{idwork} descarga output (si completed)

FastAPI:

guarda CSV en storage (S3 o uploads/ local)

crea registro Work en Postgres con idwork, estado PENDING

expande CSV en N tareas (según tu regla o tope max_tasks) — crea filas Task en Postgres

encola jobs en Redis/Celery (solo metadata de job: task_id, input_path, etc.)

Redis: broker para Celery + almacén para semáforo / tokens (límite concurrente)

Celery workers ("caja negra"):

toman job, adquieren token (si no hay token, re-enqueue or wait), procesan, escriben output en storage, actualizan estado Task y Work en Postgres, registran error si falla

Postgres: persistencia de metadata y trazabilidad

Storage (S3 o disco): archivos originales y outputs

POST /upload

Recibe CSV y un parámetro opcional max_tasks o resource_limit.

Guarda CSV (S3/local). Crea Work en DB.

Lee CSV (sin procesar todo en memoria: stream) y crea filas Task hasta max_tasks (o crea todas y deja el control de ejecución separado).

Para cada Task encola un job en Celery (payload reducido: task_id, path, meta).

Respuesta: { "idwork": "<uuid>", "tasks_enqueued": N }

GET /status/{idwork}

Devuelve estado del Work (counts por Task.status, porcentaje, errores, y si hay output_path).

Incluye link de descarga si Work.status == COMPLETED o Task.status == COMPLETED.

GET /download/{idwork}

Verifica estado COMPLETED. Sirve archivo desde S3 o archivo local con send_file.

(Opcional) POST /cancel/{idwork}

Marca Work y tasks como CANCELLED y envía revocación a Celery (si posible). Limpieza de recursos.

Control de concurrencia / límite de creación de tareas

Tienes dos requerimientos:

controlar cuántas tareas se generan;

controlar cuántas tareas se ejecutan concurrentemente (por recursos).

Opciones:

A) Límite en creación:
Cuando subes el CSV, aceptas un parámetro max_tasks. Al leer el CSV creas hasta max_tasks Task rows. Sencillo.

B) Límite en ejecución (recomendado global): Redis Token Bucket / Semaphore
Implementación simple con Redis:

Una clave semaphore:{name} con contador INCR/DECR.

Antes de ejecutar una tarea, worker intenta GET y DECR atomically (usando lua o SETNX + expire), o usar redlock/redis.lock.

Si no hay tokens: re-enqueue la tarea con backoff o dejar en estado PENDING y el scheduler la re-intenta.

Beneficios:

Control global entre múltiples workers y máquinas.

Puedes cambiar el límite en caliente poniendo el número de tokens deseado.

Pseudocódigo de adquisición:

# acquire token (atomic)

if redis.decr("tokens") >= 0: # proceed
else:
redis.incr("tokens") # devolver si no hay
raise NoToken

# uso aplicar el historial de migraciones

>[!IMPORTANT] Si se desea aplicar una nueva migración: `alembic revision --autogenerate -m "mensaje de la migración"`

```bash
alembic upgrade head
```
