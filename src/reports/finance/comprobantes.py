from datetime import date
import pandas as pd

from src.database import SessionLocal
from src.database.models import Comprobante, Proveedor, EstadoComprobante

db = SessionLocal()

def pendientes(fecha_corte: date | str = date.today()):

    if isinstance(fecha_corte, str):
        fecha_corte = date.fromisoformat(fecha_corte)

    query = (
        db.query(
            Comprobante,
            Proveedor.razon_social)
            .join(Proveedor)
        .filter(Comprobante.fecha_emision <= fecha_corte)
        .filter(Comprobante.fecha_cancelacion <= fecha_corte))

    return pd.read_sql(query.statement, db.bind)