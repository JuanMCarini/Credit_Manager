from datetime import date
import pandas as pd

from src.database import SessionLocal
from src.database.models import Movimiento, Concepto, Clasificacion, CategoriaMovimiento
db = SessionLocal()

query = (
    db.query(
        Movimiento.id,
        Movimiento.fecha,
        Movimiento.monto,
        Concepto.name.label("concepto_nombre"), 
        Concepto.tipo_movimiento.label("tipo_movimiento"), 
        Clasificacion.name.label("clasificacion_nombre")
    )
    .select_from(Movimiento)
    .join(Concepto, isouter=True)
    .join(Clasificacion, isouter=True)
)

df = pd.read_sql(query.statement, db.connection(), index_col="id")
db.close()

# 1. Modificar valores usando vectorización y .loc
# Por si read_sql los trae como strings de sus nombres ('EGRESO', etc) 
# o como Enum de Python, podemos abarcar ambos casos de la siguiente manera:
egresos = [
    CategoriaMovimiento.EGRESO, 
    CategoriaMovimiento.SUSCRIPCION_FCI, 
    CategoriaMovimiento.PLAZO_FIJO_INGRESOS,
    # También incluimos los strings (values/names) por si pandas los convierte
    CategoriaMovimiento.EGRESO.name,
    CategoriaMovimiento.SUSCRIPCION_FCI.name,
    CategoriaMovimiento.PLAZO_FIJO_INGRESOS.name
]

# Aplicamos la multiplicación solo a las filas que coincidan
mask = df["tipo_movimiento"].isin(egresos)
df.loc[mask, "monto"] *= -1

def resumen(fecha: str | date | None = None):
    if isinstance(fecha, str):
        fecha = pd.to_datetime(fecha).date()
    if fecha is None:
        fecha = df["fecha"].max()
    return df[df["fecha"] <= fecha].groupby("clasificacion_nombre")["monto"].sum()