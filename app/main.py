import csv
import io
import json
from typing import Union
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Request,
    Form,
    UploadFile,
    WebSocket,
)
from pathlib import Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic_core import ValidationError

app = FastAPI()


app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = Path("app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def validate_csv_bytes(
    content: bytes, max_sample_bytes: int = 65536, max_rows: int = 500
):
    """
    Valida bytes que deberían representar un CSV.
    Retorna dict con keys: valid (bool), errors (list), info (dict).
    info incluye: delimiter, has_header (bool), n_columns, sample_rows (list).
    """
    errors = []
    info = {}
    # Intentar decodificar (prueba utf-8, luego latin-1)
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

    # Usar Sniffer para detectar delimitador y header
    sniffer = csv.Sniffer()
    dialect = None
    try:
        dialect = sniffer.sniff(sample)
        delimiter = dialect.delimiter
    except (csv.Error, Exception):
        for d in [",", ";", "\t", "|"]:
            if d in sample:
                delimiter = d
                break
        else:
            delimiter = ","
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
        n = 0
        for row in reader:
            if not any(cell.strip() for cell in row):
                continue
            rows.append(row)
            if expected_cols is None:
                expected_cols = len(row)
            else:
                if len(row) != expected_cols:
                    errors.append(
                        f"Inconsistencia de columnas en la fila {n+1}: tiene {len(row)} columnas, se esperaban {expected_cols}."
                    )
            n += 1
            if n >= max_rows:
                break
        if not rows:
            errors.append(
                "No se encontraron filas útiles en el CSV (posible archivo malformado)."
            )
        info["n_sample_rows"] = len(rows)
        info["n_columns"] = expected_cols or 0

        info["sample_rows"] = rows[:5]

    except Exception as e:
        errors.append(f"Error leyendo CSV: {e}")

    valid = len(errors) == 0
    info["encoding"] = used_encoding

    return {"valid": valid, "errors": errors, "info": info}


@app.get("/", response_class=HTMLResponse)
async def form_get(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    # Validaciones básicas antes de leer contenido
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No se recibió nombre de archivo válido.",
        )

    filename = Path(file.filename).name
    if not filename:
        raise HTTPException(
            status_code=400, detail="No se recibió nombre de archivo válido."
        )

    # chequeo por extensión
    if not filename.lower().endswith(".csv"):
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "El archivo debe tener extensión .csv"},
        )

    # chequeo por content-type (puede ser inconsistente según navegador)
    if file.content_type and not (
        file.content_type.startswith("text/") or "csv" in file.content_type
    ):
        # no lo rechazamos categóricamente, pero avisamos
        # si quieres rechazarlos estrictamente, cambia a raise HTTPException
        warning = f"Tipo MIME recibido: {file.content_type}. Se continuará validando por contenido."
    else:
        warning = None

    content = await file.read()
    result = validate_csv_bytes(content)

    if not result["valid"]:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Validación fallida", "details": result},
        )

    # Opcional: guardar
    out_path = UPLOAD_DIR / filename
    with out_path.open("wb") as f:
        f.write(content)

    response = {
        "ok": True,
        "filename": filename,
        "saved_to": str(out_path),
        "warn": warning,
        "validation": result["info"],
    }
    return JSONResponse(status_code=200, content=response)
