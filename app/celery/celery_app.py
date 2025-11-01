from celery import Celery
import os

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6380/0")
backend_url = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6380/1")

celery = Celery(
    "app",
    broker=broker_url,
    backend=backend_url,
    include=["app.celery.task.process_task"]
)

celery.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)

@celery.task
def test_task(x, y):
    print(f"Running test task: {x} + {y}")
    return x + y
