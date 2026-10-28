from datetime import date
import pandas as pd

from src.database import SessionLocal
from src.database.models import Movimiento, Concepto, Clasificacion, CategoriaMovimiento


def get_df() -> pd.DataFrame:
    with SessionLocal() as db:
        query = (
            db.query(
                Movimiento.id,
                Movimiento.fecha,
                Movimiento.monto,
                Concepto.name.label("concepto_nombre"),
                Concepto.tipo_movimiento.label("tipo_movimiento"),
                Clasificacion.name.label("clasificacion_nombre"),
            )
            .select_from(Movimiento)
            .join(Concepto, isouter=True)
            .join(Clasificacion, isouter=True)
        )
        df = pd.read_sql(query.statement, db.connection(), index_col="id")

    if not df.empty:
        df["monto"] = df["monto"].astype(float)
        egresos = [
            CategoriaMovimiento.EGRESO,
            CategoriaMovimiento.SUSCRIPCION_FCI,
            CategoriaMovimiento.PLAZO_FIJO_INGRESOS,
            CategoriaMovimiento.EGRESO.name,
            CategoriaMovimiento.SUSCRIPCION_FCI.name,
            CategoriaMovimiento.PLAZO_FIJO_INGRESOS.name,
            CategoriaMovimiento.EGRESO.value,
            CategoriaMovimiento.SUSCRIPCION_FCI.value,
            CategoriaMovimiento.PLAZO_FIJO_INGRESOS.value,
        ]
        mask = df["tipo_movimiento"].isin(egresos)
        df.loc[mask, "monto"] *= -1

    return df


def resumen(fecha: str | date | None = None):
    df = get_df()
    if df.empty:
        return pd.Series(dtype=float)
    if isinstance(fecha, str):
        fecha = pd.to_datetime(fecha).date()
    if fecha is None:
        fecha = df["fecha"].max()
    filtro = pd.to_datetime(df["fecha"]).dt.date <= pd.to_datetime(fecha).date()
    return df[filtro].groupby("clasificacion_nombre")["monto"].sum()


def fci(fecha: str | date | None = None):
    df = get_df()
    if df.empty:
        return 0.0
    if isinstance(fecha, str):
        fecha = pd.to_datetime(fecha).date()
    if fecha is None:
        fecha = df["fecha"].max()
    filtro = (pd.to_datetime(df["fecha"]).dt.date <= pd.to_datetime(fecha).date()) & (
        df["tipo_movimiento"].isin([
            CategoriaMovimiento.SUSCRIPCION_FCI,
            CategoriaMovimiento.RESCATE_FCI,
            CategoriaMovimiento.SUSCRIPCION_FCI.name,
            CategoriaMovimiento.RESCATE_FCI.name,
            CategoriaMovimiento.SUSCRIPCION_FCI.value,
            CategoriaMovimiento.RESCATE_FCI.value,
        ])
    )

    df_fci = df[filtro].sort_values(by="fecha")

    saldo = 0.0
    for monto in df_fci["monto"]:
        saldo -= float(monto)
        saldo = max(saldo, 0.0)

    return saldo


def __getattr__(name: str):
    if name == "df":
        return get_df()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
