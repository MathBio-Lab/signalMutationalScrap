from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from app.config.config import TEMPLATES, UPLOAD_DIR
from app.core.dependencies import get_upload_csv_use_case
from app.service.upload_csv import UploadCSVUseCase
from app.utils.validate_csv_bytes import validate_csv_bytes

router = APIRouter(tags=["Upload Routes"])


@router.get("/", response_class=HTMLResponse)
async def form_get(request: Request):
    return TEMPLATES.TemplateResponse("upload.html", {"request": request})


@router.post("/")
async def upload_csv(
    file: UploadFile = File(...),
    use_case: UploadCSVUseCase = Depends(get_upload_csv_use_case),
):
    if not file.filename:
        raise HTTPException(
            status_code=400, detail="No se recibió nombre de archivo válido."
        )

    filename = Path(file.filename).name
    if not filename.lower().endswith(".csv"):
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "El archivo debe tener extensión .csv"},
        )

    # Leer bytes del archivo
    content = await file.read()
    result = validate_csv_bytes(content)
    if not result["valid"]:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Validación fallida", "details": result},
        )

    # Guardar archivo en disco
    out_path = UPLOAD_DIR / filename
    out_path.write_bytes(content)

    try:
        response = await use_case.execute(file_path=str(out_path), filename=filename)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Error al procesar Work/Task: {e}"},
        )

    # Responder con información del Work y Task creados
    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "work_id": response["work_id"],
            "task_id": response["task_id"],
            "filename": filename,
            "validation": result["info"],
            "saved_to": str(out_path),
        },
    )
