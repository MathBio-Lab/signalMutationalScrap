import csv
import io
from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from app.config.config import TEMPLATES, UPLOAD_DIR

router = APIRouter(tags=["Upload Routes"])


def validate_csv_bytes(
    content: bytes, max_sample_bytes: int = 65536, max_rows: int = 500
):
    errors = []
    info = {}
    for encoding in ("utf-8", "latin-1"):
        try:
            text = content.decode(encoding)
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            used_encoding = None
    else:
        errors.append("No se pudo decodificar el archivo como UTF-8 ni latin-1.")
        return {"valid": False, "errors": errors, "info": {}}

    sample = text[:max_sample_bytes]
    if not sample.strip():
        errors.append(
            "El archivo está vacío o contiene solo espacios/lineas en blanco."
        )
        return {"valid": False, "errors": errors, "info": {}}

    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample)
        delimiter = dialect.delimiter
    except (csv.Error, Exception):
        delimiter = next((d for d in [",", ";", "\t", "|"] if d in sample), ",")

    info["delimiter"] = delimiter
    try:
        info["has_header"] = sniffer.has_header(sample)
    except Exception:
        info["has_header"] = False

    try:
        stream = io.StringIO(text)
        reader = csv.reader(stream, delimiter=delimiter)
        rows = []
        expected_cols = None
        for n, row in enumerate(reader, 1):
            if not any(cell.strip() for cell in row):
                continue
            rows.append(row)
            if expected_cols is None:
                expected_cols = len(row)
            elif len(row) != expected_cols:
                errors.append(
                    f"Inconsistencia de columnas en la fila {n}: tiene {len(row)} columnas, se esperaban {expected_cols}."
                )
            if len(rows) >= max_rows:
                break
        if not rows:
            errors.append("No se encontraron filas útiles en el CSV.")
        info.update(
            {
                "n_sample_rows": len(rows),
                "n_columns": expected_cols or 0,
                "sample_rows": rows[:5],
                "encoding": used_encoding,
            }
        )
    except Exception as e:
        errors.append(f"Error leyendo CSV: {e}")

    return {"valid": len(errors) == 0, "errors": errors, "info": info}


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
async def upload_csv(file: UploadFile = File(...)):
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
