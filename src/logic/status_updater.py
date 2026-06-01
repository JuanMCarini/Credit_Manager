from datetime import date
from typing import Optional, Union
import pandas as pd
from sqlalchemy.orm import Session
from src.database.connection import SessionLocal
from src.database.models import Cuota, EstadoCuota, Credito
from src.utils.dates import normalize_date


def actualizar_estados(
    fecha: Optional[Union[str, date]] = None, db: Optional[Session] = None
) -> pd.DataFrame:
    """
    =============================================================================
    Function: actualizar_estados
    Description: Evaluates all pending or overdue installments whose due date has
                 expired before the given evaluation date, transitions them to
                 MOROSA, updates the global status of their parent credits, and
                 commits the changes.
    Parameters:
        fecha (date | str): Reference date to check for delinquency (defaults to today).
        db (Session): Optional SQLAlchemy session. If not provided, a new one is managed.
    Returns:
        pd.DataFrame: A pandas DataFrame containing the updated state of overdue cuotas.
    =============================================================================
    """
    if fecha is None:
        fecha = date.today()
    else:
        fecha = normalize_date(fecha)

    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        estados_mutuables = [EstadoCuota.MOROSA, EstadoCuota.PENDIENTE]

        # 1. Query for overdue installments that are not cancelled or excluded
        query = (
            db.query(Cuota)
            .filter(Cuota.estado.in_(estados_mutuables))
            .filter(Cuota.fecha_vencimiento < fecha)
        )

        df = pd.read_sql(query.statement, db.get_bind(), index_col="id")
        if df.empty:
            return df

        df["fecha_vencimiento"] = pd.to_datetime(df["fecha_vencimiento"])
        affected_credits = df["credito_id"].unique().tolist()

        # 2. Update installments and credits in memory
        cuotas_db = db.query(Cuota).filter(Cuota.credito_id.in_(affected_credits)).all()
        for cuota in cuotas_db:
            cuota.actualizar_estado(fecha)

        creditos_db = db.query(Credito).filter(Credito.id.in_(affected_credits)).all()
        for credito in creditos_db:
            credito.actualizar_estado()

        # 3. Commit changes to the database
        db.commit()

        # 4. Fetch the updated state from the DB
        df_actualizado = pd.read_sql(query.statement, db.get_bind(), index_col="id")
        return df_actualizado

    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Error executing batch status update: {e}")

    finally:
        if own_session:
            db.close()
