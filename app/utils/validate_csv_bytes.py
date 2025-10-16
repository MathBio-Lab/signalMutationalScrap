import csv
import io


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

