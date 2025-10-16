import csv
from pathlib import Path

def load_mapping(uploaded_csv: Path) -> dict[str, str]:
    """
    Lee un archivo Donor_ID,_PATIENT (SP↔DO) y devuelve un mapping DO → SP.
    """
    mapping = {}
    with open(uploaded_csv, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # saltar encabezado
        for row in reader:
            if len(row) >= 2:
                sp_id, do_id = row[0].strip(), row[1].strip()
                mapping[do_id] = sp_id
    return mapping
