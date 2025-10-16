import pandas as pd
from pathlib import Path


def destructure_csvs(work_dir: Path, mapping: dict):
    """
    Combina los CSV descargados en un solo archivo,
    usando el mapping SP<->DO para nombrar las columnas.
    """
    downloads_dir = work_dir / "downloads"
    csv_files = list(downloads_dir.glob("*.csv"))

    if not csv_files:
        print("⚠️ No se encontraron CSVs en", downloads_dir)
        return None

    combined_df: pd.DataFrame | None = None

    for csv_file in csv_files:
        do_id = csv_file.stem
        sp_id = mapping.get(do_id, do_id)

        df = pd.read_csv(csv_file)
        df.columns = ["Type", sp_id]
        df.set_index("Type", inplace=True)

        if combined_df is None:
            combined_df = df
        else:
            combined_df = combined_df.join(df, how="outer")

    # Asegurarse de que no sea None
    if combined_df is None:
        print("⚠️ No se generó ningún DataFrame combinado.")
        return None

    combined_df.reset_index(inplace=True)
    combined_path = downloads_dir / "combined.csv"
    combined_df.to_csv(combined_path, index=False)

    print(f"✅ Archivo combinado guardado en: {combined_path}")
    return combined_path
