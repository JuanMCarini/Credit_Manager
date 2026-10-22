"""
Script: backfill_historial_estados.py
Description: Populates initial history records for existing Clientes and Creditos
             so their timelines have an initial baseline.
"""

import sys
import os
from datetime import datetime, timezone, time

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.connection import SessionLocal, engine, Base
from src.database.models import (
    Credito,
    Cliente,
    HistorialEstadoCredito,
    HistorialEstadoCliente,
    EstadoClienteEnum,
)


def run_backfill():
    print("Iniciando creación de tablas si no existen...")
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        # 1. Backfill Creditos
        print("Verificando historial de créditos...")
        creditos = session.query(Credito).all()
        creditos_migrados = 0

        for cred in creditos:
            has_history = session.query(HistorialEstadoCredito).filter(
                HistorialEstadoCredito.credito_id == cred.id
            ).first()

            if not has_history:
                fecha = datetime.now(timezone.utc)
                if cred.fecha_emision:
                    fecha = datetime.combine(cred.fecha_emision, time.min, tzinfo=timezone.utc)

                estado_str = cred.estado.value if hasattr(cred.estado, "value") else str(cred.estado)

                reg = HistorialEstadoCredito(
                    credito_id=cred.id,
                    estado_anterior=None,
                    estado_nuevo=estado_str,
                    fecha_cambio=fecha,
                    usuario_id=None,
                    origen="MIGRACION_INICIAL",
                    motivo="Estado base al inicializar historial",
                )
                session.add(reg)
                creditos_migrados += 1

        session.commit()
        print(f"Créditos procesados: {len(creditos)}. Nuevos registros de historial creados: {creditos_migrados}.")

        # 2. Backfill Clientes
        print("Verificando historial de clientes...")
        clientes = session.query(Cliente).all()
        clientes_migrados = 0

        for cli in clientes:
            has_history = session.query(HistorialEstadoCliente).filter(
                HistorialEstadoCliente.cliente_cuil == cli.cuil
            ).first()

            if not has_history:
                fecha = datetime.now(timezone.utc)
                if cli.fecha_estado:
                    fecha = datetime.combine(cli.fecha_estado, time.min, tzinfo=timezone.utc)

                estado_val = cli.estado or EstadoClienteEnum.ACTIVO
                estado_str = estado_val.value if hasattr(estado_val, "value") else str(estado_val)

                reg = HistorialEstadoCliente(
                    cliente_cuil=cli.cuil,
                    estado_anterior=None,
                    estado_nuevo=estado_str,
                    fecha_cambio=fecha,
                    usuario_id=None,
                    origen="MIGRACION_INICIAL",
                    motivo="Estado base al inicializar historial",
                )
                session.add(reg)
                clientes_migrados += 1

        session.commit()
        print(f"Clientes procesados: {len(clientes)}. Nuevos registros de historial creados: {clientes_migrados}.")
        print("Backfill completado exitosamente.")

    except Exception as e:
        session.rollback()
        print(f"Error durante backfill: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_backfill()
