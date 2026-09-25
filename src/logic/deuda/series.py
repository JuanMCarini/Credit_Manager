import pandas as pd

from sqlalchemy import or_

from src.database import SessionLocal, Serie, Comision, ComisionesSerie
from .ctas_ctes import buscar

def resumen(serie: int | str):
    
    try:
        db = SessionLocal()
        
        filters = [Serie.name == str(serie)]
        try:
            filters.append(Serie.id == int(serie))
        except ValueError:
            pass
            
        serie_obj = db.query(Serie).filter(or_(*filters)).first()
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
    query = (
        db.query(
            Serie.name.label("Serie"),
            Serie.fecha_suscripcion.label("Fecha Suscripción"),
            Serie.tna.label("TNA"),
            Serie.plazo.label("Plazo"),
            Comision.porcentaje.label("% Comisión"))
        .join(Serie.comisiones_asociadas) # Va a ComisionesSerie
        .join(ComisionesSerie.comision)   # Va a Comision
        .filter(Serie.comision == comisiones)
    )

    df = pd.read_sql(query.statement, db.get_bind())
    df["Fecha Suscripción"] = pd.to_datetime(df["Fecha Suscripción"]).dt.to_period("D")
    df["Fecha Vencimiento"] = df["Fecha Suscripción"] + df["Plazo"]
    df = df[df["Fecha Vencimiento"] > pd.Period.now("D")]
    df.set_index("Serie", inplace=True)
    df.sort_values(by=["Fecha Vencimiento"], inplace=True)

    for s in df.index:
        df_s = resumen(s)
        df.loc[s, ["Capital", "Interés", "Total"]] = df_s[["Capital", "Interés", "Total"]].sum().round(2)
    df["Comisión"] = df["Capital"] * df["% Comisión"]/365 * df["Plazo"]

    return df
