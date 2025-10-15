from app.entities.work import Work
from app.entities.task import Task
from app.repositories.repositories import ITaskRepository, IWorkRepository
from app.task import process_task


class UploadCSVUseCase:
    def __init__(self, work_repo: IWorkRepository, task_repo: ITaskRepository):
        self.work_repo = work_repo
        self.task_repo = task_repo

    async def execute(self, file_path: str, filename: str):
        # Crear entidad de dominio Work
        work = Work(filename=filename, storage_path=file_path)

        # Guardar en repositorio
        await self.work_repo.add(work)

        # Crear entidad de dominio Task
        task = Task(work_id=work.id, payload={"csv_path": file_path})
        await self.task_repo.add(task)

        # Lanzar tarea Celery
        process_task.delay(str(task.id))  # type: ignore

        return {"work_id": work.id, "task_id": task.id}
