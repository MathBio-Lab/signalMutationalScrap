from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from app.config.config import TEMPLATES


router = APIRouter(prefix="/check", tags=["Check Routes"])


@router.get("/", response_class=HTMLResponse)
def get_form(request: Request):
    return TEMPLATES.TemplateResponse("status.html", {"request": request})


@router.post("/", response_class=HTMLResponse)
def check_status(request: Request, work_id: str = Form(...)):
    fake_db = {"123": "ok", "456": "pendiente", "789": "error"}
    status = fake_db.get(work_id, "pendiente")
    download_url = f"/download/{work_id}" if status == "ok" else None
    return TEMPLATES.TemplateResponse(
        "status.html",
        {"request": request, "status": status, "download_url": download_url},
    )


# @router.post("/", response_class=HTMLResponse)
# async def check_statuss(
#     request: Request,
#     work_id: str = Form(...),
#     session: AsyncSession = Depends(get_async_session),
# ):
#     # Buscar la task en la DB
#     task = await session.get(TaskModel, work_id)
    
#     if not task:
#         status = "no encontrado"
#         download_url = None
#     else:
#         # Convertimos el status a string para la plantilla
#         status = task.status.value if isinstance(task.status, TaskStatus) else str(task.status)
#         download_url = f"/download/{task.id}" if task.status == TaskStatus.COMPLETED else None

#     return TEMPLATES.TemplateResponse(
#         "status.html",
#         {"request": request, "status": status, "download_url": download_url},
#     )