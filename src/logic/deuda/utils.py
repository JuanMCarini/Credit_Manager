from itertools import groupby
import pandas as pd

from pathlib import Path
from datetime import date

from src.utils import select_file
from src.services.arca_consulta import validar_datos_arca
from src.database.models.deuda.movimientos import TipoMovimiento

mov_exp = {
    TipoMovimiento.SUSCRIPCION: 1,
    TipoMovimiento.RENOVACION_SUSCRIPCION: 1,
    TipoMovimiento.RESCATE: -1,
    TipoMovimiento.RENOVACION_RESCATE: -1,
    TipoMovimiento.VENCIMIENTO: -1,
    TipoMovimiento.RETIRO_INTERESES: -1
}

def clean_money(val):
    # Aseguramos que las columnas monetarias sean numéricas (limpiando formato string de CSV)
    if isinstance(val, str):
        val = val.replace('$', '').replace(' ', '').strip()
        if not val or val == '-':
            return 0.0
        # Si tiene coma y punto, asumimos formato es-AR (1.234,56)
        if ',' in val and '.' in val:
            val = val.replace('.', '').replace(',', '.')
        elif ',' in val:
            # Solo coma decimal (ej. 1234,56)
            val = val.replace(',', '.')
        elif val.count('.') > 1:
            # Múltiples puntos como separadores de miles sin coma (ej. 1.000.000)
            val = val.replace('.', '')
        # Si tiene un solo punto o ninguno (ej. 0.0001 o 1234.56), es float estándar
        try:
            f = float(val)
            return 0.0 if abs(f) < 0.005 else round(f, 2)
        except ValueError:
            return 0.0
    elif isinstance(val, (int, float)):
        if pd.isna(val) or abs(val) < 0.005:
            return 0.0
        return round(float(val), 2)
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
        df = df.groupby(["ID Cta. Cte.", "CUIT/CUIL"]).agg({"Razón Social": 'first', "Dirección": 'first', "Capital": 'sum', "Interés": 'sum', "Total": 'sum'}).reset_index()
    elif len(df.columns) == 10:
        df.columns = ["ID Cta. Cte.", "Razón Social", "CUIT/CUIL", "Dirección", "Capital", "Interés", "Total", "Rescate", "Suscripción", "Observación"]
        df = df.groupby(["ID Cta. Cte.", "CUIT/CUIL"]).agg({"Razón Social": 'first', "Dirección": 'first', "Capital": 'sum', "Interés": 'sum', "Total": 'sum', "Rescate": 'sum', "Suscripción": 'sum', "Observación": 'first'}).reset_index()
    else:
        raise ValueError("El archivo, para nueva serie, debe tener 7 o 10 columnas")

    for col in ["Capital", "Interés", "Total", "Rescate", "Suscripción"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_money).astype(float)
            df[col] = df[col].fillna(0.0)
            df[col] = df[col].apply(lambda x: 0.0 if abs(x) < 0.005 else round(x, 2))

    # Limpiamos filas completamente vacías al final del archivo
    df = df.dropna(subset=["ID Cta. Cte.", "CUIT/CUIL", "Capital"])
    df["Conjunta"] = False
    df = df.reset_index(drop=True).reset_index(names="ID Movimiento")

    df["CUIT/CUIL"] = df["CUIT/CUIL"].astype(str).apply(lambda x: x.split(" - "))
    df["Razón Social"] = df["Razón Social"].astype(str).apply(lambda x: x.split(" Y/O "))

    # validar_datos_arca(df)

    return df
