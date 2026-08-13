from datetime import date
import pandas as pd

from src.database import SessionLocal
from src.database.models import Comprobante, Proveedor, Concepto
from src.database.models.finance.comprobantes import CancelacionComprobante
from sqlalchemy import func

db = SessionLocal()

def pendientes(fecha_corte: date | str = date.today()):

    if isinstance(fecha_corte, str):
        fecha_corte = pd.to_datetime(fecha_corte).date()

    query = (
        db.query(
            Proveedor.razon_social,
            Comprobante.fecha_emision,
            Concepto.name.label("concepto"),
            Comprobante.importe_total,
        )
        .join(Proveedor, Comprobante.proveedor_id == Proveedor.id)
        .filter(Comprobante.fecha_emision <= fecha_corte)
    )

    df = pd.read_sql(query.statement, db.bind)
    # df['saldo'] = df['importe_total'] - df['importe_cancelado']
    
    # Filtrar solo los comprobantes que realmente tenían saldo > 0 a esa fecha
    # df = df[df['saldo'] > 0]
    
    return df