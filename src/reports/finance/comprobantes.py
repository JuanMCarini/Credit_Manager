from datetime import date
import pandas as pd

from src.database import SessionLocal
from src.database.models import Comprobante, Proveedor, Concepto, Clasificacion
from src.database.models.finance.comprobantes import CancelacionComprobante
from sqlalchemy import func

db = SessionLocal()

def pendientes(fecha_corte: date | str = date.today()):

    if isinstance(fecha_corte, str):
        fecha_corte = pd.to_datetime(fecha_corte).date()

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

    df = pd.read_sql(query.statement, db.bind)

    query_pagos = (
        db.query(
            CancelacionComprobante.comprobante_id,
            func.sum(CancelacionComprobante.importe).label("pagado_historico")
        )
        .filter(func.date(CancelacionComprobante.fecha_cancelacion) <= fecha_corte)
        .group_by(CancelacionComprobante.comprobante_id)
    )

    df_pagos = pd.read_sql(query_pagos.statement, db.bind)
    df_pagos.rename(columns={'pagado_historico':'importe_cancelado'}, inplace=True)

    df_result = df.merge(df_pagos, on='comprobante_id', how='left')
    df_result['importe_cancelado'] = df_result['importe_cancelado'].fillna(0)
    df_result['saldo'] = df_result['importe_total'] - df_result['importe_cancelado']

    return df_result[df_result['saldo'] > 0]

query = (db.query(
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

df_comprobantes = pd.read_sql(query.statement, db.bind)

query_pagos = (
        db.query(
            CancelacionComprobante,
        )
    )

df_pagos = pd.read_sql(query_pagos.statement, db.bind)