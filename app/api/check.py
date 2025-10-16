from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from app.config.config import TEMPLATES


router = APIRouter(prefix="/check", tags=["Check Routes"])


@router.get("/", response_class=HTMLResponse)
def get_form(request: Request):
    return TEMPLATES.TemplateResponse("status.html", {"request": request})


@router.post("/", response_class=HTMLResponse)
def check_status(request: Request, work_id: str = Form(...)):
    # Simula consultar el estado
    # Aquí reemplaza con tu lógica real
    fake_db = {"123": "ok", "456": "pendiente", "789": "error"}
    status = fake_db.get(work_id, "pendiente")
    download_url = f"/download/{work_id}" if status == "ok" else None
    return TEMPLATES.TemplateResponse(
        "status.html",
        {"request": request, "status": status, "download_url": download_url},
    )
