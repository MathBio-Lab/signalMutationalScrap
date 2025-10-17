from app.entities.work import Work
from app.entities.task import Task
from app.repositories.repositories import ITaskRepository, IWorkRepository
from app.task import process_task


class UploadCSVUseCase:
    def __init__(self, session, work_repo: IWorkRepository, task_repo: ITaskRepository):
        self.session = session
        self.work_repo = work_repo
        self.task_repo = task_repo

    async def execute(self, file_path: str, filename: str):
        try:
            async with self.session.begin():
                work = Work(filename=filename, storage_path=file_path)
                await self.work_repo.add(work)
                print(f"[UseCase] Work created: {work.id}")

                task = Task(work_id=work.id, payload={"csv_path": file_path})
                await self.task_repo.add(task)
                print(f"[UseCase] Task created: {task.id}")

            # Encolar tarea Celery
            process_task.delay(str(task.id))  # type: ignore
            print(f"[UseCase] Task {task.id} enqueued in Celery")

            return {"work_id": work.id, "task_id": task.id}

        except Exception as e:
            await self.session.rollback()
            print(f"[UseCase] Exception: {e}")
            raise
