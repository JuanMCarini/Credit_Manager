"""
Module: estado_audit.py
Description: Servicio centralizado para auditar y persistir transiciones de estado
             de Créditos y Clientes.
Author: Antigravity
"""

from datetime import datetime, timezone, date
from typing import Optional
import logging
from sqlalchemy.orm import Session

from src.database.models import (
    Credito,
    Cliente,
    HistorialEstadoCredito,
    HistorialEstadoCliente,
    EstadoCredito,
    EstadoClienteEnum,
)

logger = logging.getLogger(__name__)


def _to_estado_str(estado) -> Optional[str]:
    if estado is None:
        return None
    if hasattr(estado, "value"):
        return str(estado.value)
    return str(estado)


def registrar_cambio_estado_credito(
    db: Session,
    credito: Credito,
    nuevo_estado: str | EstadoCredito,
    usuario_id: Optional[int] = None,
    motivo: Optional[str] = None,
    origen: str = "MANUAL",
    forzar_registro: bool = False,
) -> Optional[HistorialEstadoCredito]:
    """
    Registra una transición de estado de un Crédito en la tabla de auditoría.
    Actualiza además el campo `credito.estado`.
    """
    estado_anterior_str = _to_estado_str(credito.estado)
    estado_nuevo_str = _to_estado_str(nuevo_estado)

    # Si no hay cambio y no se fuerza el registro, no creamos historial repetido
    if not forzar_registro and estado_anterior_str == estado_nuevo_str:
        return None

    # Actualizar estado en el modelo
    if isinstance(nuevo_estado, EstadoCredito):
        credito.estado = nuevo_estado
    else:
        try:
            credito.estado = EstadoCredito(estado_nuevo_str)
        except ValueError:
            credito.estado = estado_nuevo_str

    registro = HistorialEstadoCredito(
        credito_id=credito.id,
        estado_anterior=estado_anterior_str,
        estado_nuevo=estado_nuevo_str,
        fecha_cambio=datetime.now(timezone.utc),
        usuario_id=usuario_id,
        origen=origen,
        motivo=motivo.strip() if motivo else None,
    )
    db.add(registro)
    logger.info(
        f"[Auditoría Crédito #{credito.id}] Transición: '{estado_anterior_str}' -> '{estado_nuevo_str}' "
        f"(Origen: {origen}, Usuario: {usuario_id})"
    )
    return registro


def registrar_cambio_estado_cliente(
    db: Session,
    cliente: Cliente,
    nuevo_estado: str | EstadoClienteEnum,
    usuario_id: Optional[int] = None,
    motivo: Optional[str] = None,
    origen: str = "MANUAL",
    forzar_registro: bool = False,
) -> Optional[HistorialEstadoCliente]:
    """
    Registra una transición de estado de un Cliente en la tabla de auditoría.
    Actualiza además el campo `cliente.estado` y `cliente.fecha_estado`.
    """
    estado_anterior_str = _to_estado_str(cliente.estado)
    estado_nuevo_str = _to_estado_str(nuevo_estado)

    if not forzar_registro and estado_anterior_str == estado_nuevo_str:
        return None

    if isinstance(nuevo_estado, EstadoClienteEnum):
        cliente.estado = nuevo_estado
    else:
        try:
            cliente.estado = EstadoClienteEnum(estado_nuevo_str)
        except ValueError:
            cliente.estado = estado_nuevo_str

    cliente.fecha_estado = date.today()

    registro = HistorialEstadoCliente(
        cliente_cuil=cliente.cuil,
        estado_anterior=estado_anterior_str,
        estado_nuevo=estado_nuevo_str,
        fecha_cambio=datetime.now(timezone.utc),
        usuario_id=usuario_id,
        origen=origen,
        motivo=motivo.strip() if motivo else None,
    )
    db.add(registro)
    logger.info(
        f"[Auditoría Cliente {cliente.cuil}] Transición: '{estado_anterior_str}' -> '{estado_nuevo_str}' "
        f"(Origen: {origen}, Usuario: {usuario_id})"
    )
    return registro
