from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.config import TEMPLATES
from app.database.db import get_async_session
from app.database.models import Task as TaskModel, TaskStatus


router = APIRouter(prefix="/check", tags=["Check Routes"])


@router.get("/", response_class=HTMLResponse)
def get_form(request: Request):
    return TEMPLATES.TemplateResponse("status.html", {"request": request})


@router.post("/", response_class=HTMLResponse)
async def check_status(
    request: Request,
    work_id: str = Form(...),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Verifica el estado de una tarea en la base de datos.
    
    Estados posibles:
    - PENDING: La tarea está en cola esperando ser procesada
    - RUNNING: La tarea se está ejecutando actualmente
    - COMPLETED: La tarea finalizó exitosamente
    - FAILED: La tarea falló
    """
    # Buscar la task en la DB por work_id
    from sqlalchemy import select
    stmt = select(TaskModel).where(TaskModel.work_id == work_id)
    result = await session.execute(stmt)
    task = result.scalar_one_or_none()
    
    if not task:
        status = "no encontrado"
        download_url = None
        error_message = None
    else:
        # Convertimos el status a string para la plantilla
        status = task.status.value if isinstance(task.status, TaskStatus) else str(task.status)
        download_url = f"/download/{task.id}" if task.status == TaskStatus.COMPLETED else None
        error_message = task.error if task.status == TaskStatus.FAILED else None

    return TEMPLATES.TemplateResponse(
        "status.html",
        {
            "request": request, 
            "status": status, 
            "download_url": download_url,
            "error_message": error_message,
            "work_id": work_id
        },
    )