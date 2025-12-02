from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_async_session
from app.database.models import Task as TaskModel, TaskStatus
import os

router = APIRouter(tags=["Download"])


@router.get("/download/{task_id}")
async def download_result(
    task_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """
    Descarga el archivo de resultado de una tarea completada.

    Args:
        task_id: ID de la tarea

    Returns:
        FileResponse con el archivo CSV resultante
    """
    task = await session.get(TaskModel, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"La tarea no está completada. Estado actual: {task.status.value}",
        )

    if not task.result_path:
        raise HTTPException(
            status_code=404, detail="No se encontró el archivo de resultado"
        )

    # Verificar que el archivo existe
    if not os.path.exists(task.result_path):
        raise HTTPException(
            status_code=404,
            detail=f"El archivo de resultado no existe en el servidor: {task.result_path}",
        )

    # Extraer el nombre del archivo del path
    filename = os.path.basename(task.result_path)

    return FileResponse(
        path=task.result_path,
        filename=filename,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
