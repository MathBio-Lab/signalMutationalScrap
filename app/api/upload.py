from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi import Depends
from fastapi.responses import HTMLResponse, JSONResponse
from app.config.config import TEMPLATES, UPLOAD_DIR
from app.dependencies import get_upload_csv_use_case
from app.service.upload_csv import UploadCSVUseCase
from app.utils.validate_csv_bytes import validate_csv_bytes

router = APIRouter(tags=["Upload Routes"])

# @app.post("/uploasasdasdd")
# async def upload_csvf(file: UploadFile, max_tasks: int = Form(None), db: Session = Depends(get_db)):
#     work_id = str(uuid4())
#     # guardar archivo en storage (S3 o disk)
#     storage_path = save_file_to_storage(file, folder=f"works/{work_id}")
#     work = Work(id=work_id, filename=file.filename, storage_path=storage_path, max_tasks=max_tasks)
#     db.add(work); db.commit()
#     # stream csv -> crear tasks
#     created = 0
#     for row in stream_csv_from_storage(storage_path):
#         if max_tasks and created >= max_tasks:
#             break
#         task = Task(work_id=work_id, payload=row)
#         db.add(task); db.commit()
#         # enqueue job con celery
#         celery.send_task("tasks.process_task", args=[str(task.id)])
#         created += 1
#     return {"idwork": work_id, "tasks_enqueued": created}


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

    content = await file.read()
    result = validate_csv_bytes(content)

    if not result["valid"]:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Validación fallida", "details": result},
        )

    out_path = UPLOAD_DIR / filename
    with out_path.open("wb") as f:
        f.write(content)

    return JSONResponse(
        status_code=200,
        content={
            "ok": True,
            "filename": filename,
            "saved_to": str(out_path),
            "validation": result["info"],
        },
    )
