from app.entities.work import Work
from app.entities.task import Task
from app.repositories.repositories import ITaskRepository, IWorkRepository
from app.celery.task.process_task import process_task as celery_process_task


class UploadCSVUseCase:
    def __init__(self, session, work_repo: IWorkRepository, task_repo: ITaskRepository):
        self.session = session
        self.work_repo = work_repo
        self.task_repo = task_repo

    async def execute(self, file_path: str, filename: str):
        async with self.session.begin():  
            try:
                # Crear Work
                work = Work(filename=filename, storage_path=file_path)
                await self.work_repo.add(work)
                await self.session.flush()

                # Crear Task
                db_task = Task(work_id=work.id, payload={"csv_path": file_path})
                await self.task_repo.add(db_task)
                print(f"[UseCase] Work created: {work.id}")
                print(f"[UseCase] Task created: {db_task.id}")

            except Exception as e:
                print(f"[UseCase] Exception: {e}")
                raise

        # Encolar tarea Celery
        celery_process_task.apply_async(args=[str(db_task.id)]) # type: ignore
        print(f"[UseCase] Task {db_task.id} enqueued in Celery")

        return {"work_id": work.id, "task_id": db_task.id}
