from datetime import date
import pandas as pd

from src.database import SessionLocal
from src.database.models import Comprobante, Proveedor, EstadoComprobante

db = SessionLocal()

query = (
    db.query(
        Comprobante,
        Proveedor.name)
        .join(Proveedor)
        .filter(Comprobante.estado != EstadoComprobante.PAGADO))

df = pd.read_sql(query.statement, db.bind)