"""
Servicio de scraping web para descargar CSVs de mutational signatures.

Este módulo encapsula la lógica del scraper para ser usado por tareas de Celery.
"""
import asyncio
import csv
from pathlib import Path
from typing import Dict

from app.integrations.test import scrape_signal
from app.utils.destructure_file import destructure_csvs


def load_mapping_from_csv(csv_path: str) -> Dict[str, str]:
    """
    Lee un archivo CSV con columnas Donor_ID y _PATIENT y retorna un diccionario DO -> SP.
    
    Args:
        csv_path: Ruta completa al archivo CSV de entrada
        
    Returns:
        Dict con mapping {donor_id: sp_id}
        
    Example:
        >>> mapping = load_mapping_from_csv("uploads/test.csv")
        >>> # {'DO46416': 'SP101724', 'DO36062': 'SP79365', ...}
    """
    mapping = {}
    csv_file = Path(csv_path)
    
    with csv_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            donor_id = row["_PATIENT"].strip()
            sp_id = row["Donor_ID"].strip()
            mapping[donor_id] = sp_id
            
    return mapping


def run_scraper_job(csv_path: str, work_id: str) -> str:
    """
    Ejecuta el trabajo completo de scraping: descarga CSVs y los concatena.
    
    Esta función es síncrona y puede ser ejecutada por Celery.
    Internamente ejecuta código asíncrono usando asyncio.run().
    
    Args:
        csv_path: Ruta al archivo CSV con los IDs a procesar
        work_id: ID único del trabajo (usado para organizar archivos)
        
    Returns:
        Ruta al archivo CSV combinado final
        
    Raises:
        ValueError: Si el CSV está vacío o mal formateado
        Exception: Si hay errores durante el scraping
    """
    print(f"[SCRAPER SERVICE] Iniciando job {work_id}")
    print(f"[SCRAPER SERVICE] CSV de entrada: {csv_path}")
    
    # 1. Cargar mapping del CSV
    mapping = load_mapping_from_csv(csv_path)
    ids = list(mapping.keys())  # Lista de Donor IDs
    
    if not ids:
        raise ValueError(f"No se encontraron IDs en el archivo {csv_path}")
    
    print(f"[SCRAPER SERVICE] Se procesarán {len(ids)} IDs")
    
    # 2. Ejecutar scraper (código async)
    work_dir = asyncio.run(scrape_signal(ids, work_id=work_id))
    print(f"[SCRAPER SERVICE] Scraping completado: {work_dir}")
    
    # 3. Concatenar CSVs descargados
    combined_path = destructure_csvs(work_dir, mapping)
    
    if not combined_path:
        raise Exception("No se pudo generar el archivo combinado")
    
    print(f"[SCRAPER SERVICE] Resultado final: {combined_path}")
    return str(combined_path)
