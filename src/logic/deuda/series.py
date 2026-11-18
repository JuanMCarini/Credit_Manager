import pandas as pd

from sqlalchemy import or_

from src.database import SessionLocal, Serie, Comision, ComisionesSerie
from .ctas_ctes import buscar

def resumen(serie: int | str):
    
    db = SessionLocal()
    try:
        serie_obj = None
        if isinstance(serie, int):
            serie_obj = db.query(Serie).filter(Serie.id == serie).first()
            if not serie_obj:
                serie_obj = db.query(Serie).filter(Serie.name == str(serie)).first()
        else:
            serie_obj = db.query(Serie).filter(Serie.name == str(serie)).first()
            if not serie_obj:
                try:
                    serie_obj = db.query(Serie).filter(Serie.id == int(serie)).first()
                except (ValueError, TypeError):
                    pass

        if not serie_obj:
            raise ValueError(f"Serie {serie} no encontrada")

        cuentas_ids = list(set([mov.id_cuenta_comitente for mov in serie_obj.movimientos]))
        if not cuentas_ids:
            return pd.DataFrame()
            
        ctas_ctes_data = []
        for ctas_cte in cuentas_ids:
            df_inv, df_mov = buscar(ctas_cte)
            # Filter the movements only for the current series
            df_mov_serie = df_mov[df_mov['Serie'] == serie_obj.name]
            if not df_mov_serie.empty:
                ctas_ctes_data.append(df_mov_serie)
                
        if not ctas_ctes_data:
            return pd.DataFrame()
            
        return pd.concat(ctas_ctes_data, ignore_index=True)

    finally:
        db.close()


def resumen_general(comisiones: bool) -> pd.DataFrame:

    db = SessionLocal()
    try:
        query = (
            db.query(
                Serie.name.label("Serie"),
                Serie.fecha_suscripcion.label("Fecha Suscripción"),
                Serie.tna.label("TNA"),
                Serie.plazo.label("Plazo"),
                Comision.porcentaje.label("% Comisión"))
            .outerjoin(Serie.comisiones_asociadas) # Va a ComisionesSerie
            .outerjoin(ComisionesSerie.comision)   # Va a Comision
            .filter(Serie.comision == comisiones)
        )

        df = pd.read_sql(query.statement, db.get_bind())
    finally:
        db.close()

    if df.empty:
        return pd.DataFrame(
            columns=["Fecha Suscripción", "TNA", "Plazo", "% Comisión", "Fecha Vencimiento", "Capital", "Interés", "Total", "Comisión"]
        )

    df["TNA"] = pd.to_numeric(df["TNA"], errors="coerce").fillna(0.0)
    df["% Comisión"] = pd.to_numeric(df["% Comisión"], errors="coerce").fillna(0.0)
    df = df.groupby("Serie", as_index=False).agg({
        "Fecha Suscripción": "first",
        "TNA": "first",
        "Plazo": "first",
        "% Comisión": "sum",
    })

    df["Fecha Suscripción"] = pd.to_datetime(df["Fecha Suscripción"]).dt.to_period("D")
    df["Fecha Vencimiento"] = df["Fecha Suscripción"] + df["Plazo"]
    df = df[df["Fecha Vencimiento"] > pd.Period.now("D")]
    df.set_index("Serie", inplace=True)
    df.sort_values(by=["Fecha Vencimiento"], inplace=True)
    df[["Capital", "Interés", "Total"]] = 0.0

    for s in df.index:
        df_s = resumen(s)
        if not df_s.empty:
            df.loc[s, ["Capital", "Interés", "Total"]] = df_s[["Capital", "Interés", "Total"]].sum().round(2)
    df["Comisión"] = (df["Capital"] * df["% Comisión"]/365 * df["Plazo"]).round(2)

    return df
