import pandas as pd

from pathlib import Path
from datetime import date

from src.utils import select_file

def clean_money(val):
    # Aseguramos que las columnas monetarias sean numéricas (limpiando formato string de CSV)
    if isinstance(val, str):
        val = val.replace('$', '').replace(' ', '').replace('.', '').replace(',', '.')
        # Si el string queda vacío (por ejemplo en celdas vacías), devolvemos NaN
        return float(val) if val else pd.NA
    return val

def read_file(path: Path | None):
    if path == None:
        path = select_file()

    if path.suffix == ".xlsx":
        df = pd.read_excel(path)

    elif path.suffix == ".csv":
        df = pd.read_csv(path, sep=";")

    else:
        raise ValueError("El archivo debe ser Excel o CSV")

    if len(df.columns) == 7:
        df.columns = ["ID Cta. Cte.", "Razón Social", "CUIT/CUIL", "Dirección", "Capital", "Interés", "Total"]
    elif len(df.columns) == 10:
        df.columns = ["ID Cta. Cte.", "Razón Social", "CUIT/CUIL", "Dirección", "Capital", "Interés", "Total", "Rescate", "Suscripción", "Observación"]
    else:
        raise ValueError("El archivo, para nueva serie, debe tener 7 o 10 columnas")

    for col in ["Capital", "Interés", "Total", "Rescate", "Suscripción"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_money).astype(float)

    # Limpiamos filas completamente vacías al final del archivo
    df = df.dropna(subset=["ID Cta. Cte.", "CUIT/CUIL", "Capital"])
    df["Conjunta"] = False
    df = df.reset_index(drop=True).reset_index(names="ID Movimiento")

    df["CUIT/CUIL"] = df["CUIT/CUIL"].astype(str).apply(lambda x: x.split(" - "))
    df["Razón Social"] = df["Razón Social"].astype(str).apply(lambda x: x.split(" Y/O "))

    return df
