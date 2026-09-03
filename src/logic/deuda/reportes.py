import pandas as pd

import src.logic.deuda.series as series

from src.database import SessionLocal
from src.database.models.deuda import Serie

def estado(periodo: pd.Period = pd.Period.now("D")):

    fin_mes = pd.Period(year=periodo.year, month=periodo.month+1, day=1, freq="D") - 1
    try:
        db = SessionLocal()
        query = db.query(Serie.name.label("Serie"), Serie.fecha_suscripcion.label("Fecha Suscripción"), Serie.tna.label("TNA"), Serie.plazo.label("Plazo"))
        df = pd.read_sql(query.statement, db.get_bind())
        df["Fecha Suscripción"] = pd.to_datetime(df["Fecha Suscripción"]).dt.to_period("D")
        df["Fecha Vencimiento"] = df["Fecha Suscripción"] + df["Plazo"]
        df.set_index("Serie", inplace=True)
        df["Capital"] = 0.0
        df["Interés"] = 0.0
        df["Total"] = 0.0
        df["Int. Dev."] = 0.0

        for _, row in df.iterrows():
            df_serie = series.resumen(_)
            df_serie["Fecha"] = pd.to_datetime(df_serie["Fecha"]).dt.to_period("D")
            df_serie = df_serie[df_serie["Fecha"] <= fin_mes]
            dias_devengados = (min(row["Fecha Vencimiento"], fin_mes) - row["Fecha Suscripción"]).n
            df_serie["Int. Dev."] = df_serie["Capital"] * row["TNA"]/365 * dias_devengados
            df.loc[_, ["Capital", "Interés", "Total", "Int. Dev."]] = df_serie[["Capital", "Interés", "Total", "Int. Dev."]].sum().round(0)
        df["Deuda Dev. Total"] = df["Capital"] + df["Int. Dev."]
    except Exception:
        raise

    finally:
        db.close()

    return df