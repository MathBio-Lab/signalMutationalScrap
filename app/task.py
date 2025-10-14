# tasks.py
from celery_app import celery
import redis

r = redis.Redis()

TOKEN_KEY = "global:processing_tokens"


def acquire_token():
    # simple atomic acquire with LUA would be better; conceptual:
    with r.pipeline() as pipe:
        while True:
            try:
                pipe.watch(TOKEN_KEY)
                tokens = int(pipe.get(TOKEN_KEY) or 0)
                if tokens <= 0:
                    pipe.unwatch()
                    return False
                pipe.multi()
                pipe.decr(TOKEN_KEY)
                pipe.execute()
                return True
            except redis.WatchError:
                continue


def release_token():
    r.incr(TOKEN_KEY)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def process_task(self, task_id: str):
    db = get_db_session()
    task = db.query(Task).get(task_id)
    if not task:
        return
    # try acquiring token
    if not acquire_token():
        # requeue with delay (simple backoff)
        raise self.retry(countdown=30)

    try:
        task.status = TaskStatus.RUNNING
        db.commit()

        # CALL to "caja negra" (puede ser petición HTTP, CLI, etc.)
        result_path = call_black_box(task.payload)  # devuelve path en storage

        task.result_path = result_path
        task.status = TaskStatus.COMPLETED
        db.commit()
    except Exception as exc:
        task.attempts += 1
        task.status = TaskStatus.FAILED
        task.error = str(exc)
        db.commit()
        raise self.retry(exc=exc)
    finally:
        release_token()
