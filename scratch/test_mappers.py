import sys
sys.path.insert(0, r"d:\Fondosur\Credit_Manager")

from src.database.connection import engine, Base
from src.database.models.deuda.__init__ import Inversor, CuentaComitente, MovimientoDeuda

try:
    from sqlalchemy.orm import configure_mappers
    configure_mappers()
    print("Mappers configured successfully!")
except Exception as e:
    print(f"Error configuring mappers: {e}")
