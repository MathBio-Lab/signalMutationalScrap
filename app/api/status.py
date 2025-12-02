from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_async_session
from app.database.models import Task as TaskModel, TaskStatus

router = APIRouter(prefix="/api", tags=["API Routes"])


@router.get("/status/{work_id}")
async def get_task_status(
    work_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Obtiene el estado de una tarea por work_id.
    
    Retorna JSON con:
    - status: PENDING, RUNNING, COMPLETED, FAILED, o "not_found"
    - work_id: ID del trabajo
    - task_id: ID de la tarea (si existe)
    - error: Mensaje de error (si falló)
    - result_path: Ruta del resultado (si completó)
    """
    stmt = select(TaskModel).where(TaskModel.work_id == work_id)  # type: ignore
    result = await session.execute(stmt)
    task = result.scalar_one_or_none()
    
    if not task:
        return JSONResponse(
            status_code=404,
            content={
                "status": "not_found",
                "work_id": work_id,
                "message": "No se encontró ninguna tarea con ese work_id"
            }
        )
    
    status_value = task.status.value if isinstance(task.status, TaskStatus) else str(task.status)
    
    response_data = {
        "status": status_value,
        "work_id": work_id,
        "task_id": str(task.id),
    }
    
    if task.status == TaskStatus.FAILED and task.error:
        response_data["error"] = task.error
        
    if task.status == TaskStatus.COMPLETED and task.result_path:
        response_data["result_path"] = task.result_path
        response_data["download_url"] = f"/download/{task.id}"
    
    return JSONResponse(content=response_data)
