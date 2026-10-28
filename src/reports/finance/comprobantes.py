from datetime import date
import pandas as pd

from src.database import SessionLocal
from src.database.models import Comprobante, Proveedor, Concepto, Clasificacion
from src.database.models.finance.comprobantes import CancelacionComprobante
from sqlalchemy import func


def pendientes(fecha_corte: date | str | None = None):
    if fecha_corte is None:
        fecha_corte = date.today()
    elif isinstance(fecha_corte, str):
        fecha_corte = pd.to_datetime(fecha_corte).date()

    with SessionLocal() as db:
        query = (
            db.query(
                Comprobante.id.label("comprobante_id"),
                Proveedor.razon_social,
                Comprobante.fecha_emision,
                Clasificacion.name.label("concepto"),
                Comprobante.importe_total,
            )
            .join(Proveedor, Comprobante.proveedor_id == Proveedor.id)
            .outerjoin(Concepto, Comprobante.concepto_id == Concepto.id)
            .outerjoin(Clasificacion, Concepto.clasificacion_id == Clasificacion.id)
            .filter(Comprobante.fecha_emision <= fecha_corte)
        )

        df = pd.read_sql(query.statement, db.get_bind())

        query_pagos = (
            db.query(
                CancelacionComprobante.comprobante_id,
                func.sum(CancelacionComprobante.importe).label("pagado_historico"),
            )
            .filter(func.date(CancelacionComprobante.fecha_cancelacion) <= fecha_corte)
            .group_by(CancelacionComprobante.comprobante_id)
        )

        df_pagos_hist = pd.read_sql(query_pagos.statement, db.get_bind())

    df_pagos_hist.rename(columns={"pagado_historico": "importe_cancelado"}, inplace=True)

    df_result = df.merge(df_pagos_hist, on="comprobante_id", how="left")
    df_result["importe_cancelado"] = df_result["importe_cancelado"].fillna(0)
    df_result["saldo"] = df_result["importe_total"] - df_result["importe_cancelado"]

    return df_result[df_result["saldo"] > 0]


def get_comprobantes() -> pd.DataFrame:
    with SessionLocal() as db:
        query = (
            db.query(
                Comprobante.id.label("comprobante_id"),
                Proveedor.razon_social,
                Comprobante.fecha_emision,
                Clasificacion.name.label("concepto"),
                Comprobante.importe_no_gravado,
                Comprobante.neto_gravado_21,
                Comprobante.iva_21,
                Comprobante.importe_total,
            )
            .join(Proveedor, Comprobante.proveedor_id == Proveedor.id)
            .outerjoin(Concepto, Comprobante.concepto_id == Concepto.id)
            .outerjoin(Clasificacion, Concepto.clasificacion_id == Clasificacion.id)
        )
        return pd.read_sql(query.statement, db.get_bind())


def get_pagos() -> pd.DataFrame:
    with SessionLocal() as db:
        query_pagos = db.query(CancelacionComprobante)
        return pd.read_sql(query_pagos.statement, db.get_bind())


def __getattr__(name: str):
    if name == "df_comprobantes":
        return get_comprobantes()
    if name == "df_pagos":
        return get_pagos()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
