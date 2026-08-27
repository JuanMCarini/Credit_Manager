import pandas as pd

from sqlalchemy import or_
from src.database import SessionLocal
from src.database.models.deuda.inversores import CuentaComitente
from src.database.models.deuda.movimientos import MovimientoDeuda


def buscar(id_cuenta_comitente: str | int):

    with SessionLocal() as db:
        cuenta_comitente = db.query(CuentaComitente).filter(or_(CuentaComitente.id == id_cuenta_comitente, CuentaComitente.id_externo == id_cuenta_comitente)).first()
        if not cuenta_comitente:
            raise ValueError(f"Cuenta comitente {id_cuenta_comitente} no encontrada")

        query = db.query(MovimientoDeuda).filter(MovimientoDeuda.id_cuenta_comitente == cuenta_comitente.id)
        df_movimientos = pd.read_sql(query.statement, db.get_bind())
        
    return df_movimientos