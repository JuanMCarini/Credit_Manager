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
    filtro = pd.to_datetime(df["fecha"]).dt.date <= pd.to_datetime(fecha).date()
    return df[filtro].groupby("clasificacion_nombre")["monto"].sum()


def fci(fecha: str | date | None = None):
    if isinstance(fecha, str):
        fecha = pd.to_datetime(fecha).date()
    if fecha is None:
        fecha = df["fecha"].max()
    # Usar tipo_movimiento atrapa todos los conceptos de suscripción/rescate, sin importar su nombre exacto
    filtro = (pd.to_datetime(df["fecha"]).dt.date <= pd.to_datetime(fecha).date()) & (
        df["tipo_movimiento"].isin([
            CategoriaMovimiento.SUSCRIPCION_FCI, 
            CategoriaMovimiento.RESCATE_FCI,
            CategoriaMovimiento.SUSCRIPCION_FCI.name,
            CategoriaMovimiento.RESCATE_FCI.name
        ])
    )

    # Es VITAL ordenar por fecha antes de hacer un saldo acumulado que tiene topes (max), 
    # de lo contrario el orden de inserción en BD puede alterar el resultado
    df_fci = df[filtro].sort_values(by="fecha")

    # Iterar directamente sobre la serie (columna) es mucho más rápido y limpio que iterrows()
    saldo = 0.0
    for monto in df_fci["monto"]:
        # Restamos porque la suscripción es un egreso del banco (negativo)
        # pero es un ingreso para el FCI (positivo)
        saldo -= monto
        saldo = max(saldo, 0.0)
        
    return saldo