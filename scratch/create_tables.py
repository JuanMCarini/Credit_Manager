import sys
import os
os.environ["DB_PORT"] = "5434"
sys.path.insert(0, r"d:\Fondosur\Credit_Manager")

from src.database.connection import engine, Base
from src.database.models.deuda.inversores import Inversor, CuentaComitente, TitularidadCuentaComitente
from src.database.models.deuda.series import Serie
from src.database.models.deuda.movimientos import MovimientoDeuda

# Drop to apply schema changes (safe because they are brand new and empty)
MovimientoDeuda.__table__.drop(engine, checkfirst=True)
Serie.__table__.drop(engine, checkfirst=True)

# We just want to create these specific tables
tables = [
    Inversor.__table__,
    CuentaComitente.__table__,
    TitularidadCuentaComitente.__table__,
    Serie.__table__,
    MovimientoDeuda.__table__
]

Base.metadata.create_all(engine, tables=tables)
print("Tables dropped and recreated successfully.")
