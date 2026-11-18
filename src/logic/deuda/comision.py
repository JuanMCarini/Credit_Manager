from src.database import Serie
import pandas as pd

from pandas import Period, DataFrame, read_sql
from src.database import SessionLocal
from src.database.models.deuda import MovimientoDeuda, TipoMovimiento, Comision, ComisionesSerie
from src.database.models import SocioComercial

def calcular(periodo: Period = Period.now("M")) -> DataFrame:

    db = SessionLocal()
    try:
        deuda_db = (db.query(MovimientoDeuda.fecha.label("Periodo"), MovimientoDeuda.monto.label("Capital"), Serie.name.label("Serie"), Serie.tna.label("TNA"), Serie.plazo.label("Plazo"), SocioComercial.razon_social.label("Socio"), Comision.porcentaje.label("% Comisión"))
                    .join(Serie, Serie.id == MovimientoDeuda.id_serie)
                    .join(ComisionesSerie, ComisionesSerie.id_serie == Serie.id)
                    .join(Comision, Comision.id == ComisionesSerie.id_comision)
                    .join(SocioComercial, SocioComercial.id == Comision.id_socio_comercial)
                    .filter(MovimientoDeuda.fecha >= periodo.start_time)
                    .filter(MovimientoDeuda.fecha <= periodo.end_time)
                    .filter(MovimientoDeuda.tipo_movimiento.in_([TipoMovimiento.SUSCRIPCION, TipoMovimiento.RENOVACION_SUSCRIPCION])))

        if not deuda_db.count():
            return DataFrame()

        df = read_sql(deuda_db.statement, db.get_bind())
        df["Periodo"] = df["Periodo"].dt.to_period("M")
        df["Capital"] = pd.to_numeric(df["Capital"], errors="coerce").fillna(0.0)
        df["TNA"] = pd.to_numeric(df["TNA"], errors="coerce").fillna(0.0)
        df["% Comisión"] = pd.to_numeric(df["% Comisión"], errors="coerce").fillna(0.0)
        df["Comisión"] = df["Capital"] * df["% Comisión"]/365 * df["Plazo"]
        df = df.groupby(["Socio", "Serie"]).agg({"Capital": "sum", "TNA": "mean", "Plazo": "mean", "% Comisión": "mean", "Comisión": "sum"})
        df["Plazo"] = df["Plazo"].astype(int)
        df["Capital"] = df["Capital"].round(2)
        df["Comisión"] = df["Comisión"].round(2)

        return df
        
        
    except Exception:
        raise

    finally:
        db.close()