from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database.connection import Base


class HistorialEstadoCredito(Base):
    """
    =============================================================================
    Model: HistorialEstadoCredito
    Description: Registra las transiciones de estados de los créditos (APROBADO,
                 FIRMADO, ACTIVO, INCOBRABLE, JUDICIAL, RECHAZADO, etc.) para auditoría.
    =============================================================================
    """
    __tablename__ = "historial_estados_credito"

    id = Column(Integer, primary_key=True, autoincrement=True)
    credito_id = Column(Integer, ForeignKey("creditos.id", ondelete="CASCADE"), nullable=False, index=True)
    estado_anterior = Column(String(50), nullable=True)
    estado_nuevo = Column(String(50), nullable=False, index=True)
    fecha_cambio = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    origen = Column(String(50), default="MANUAL", nullable=False)
    motivo = Column(String(255), nullable=True)

    # Relationships
    credito = relationship("Credito", back_populates="historial_estados")
    usuario = relationship("Usuario")

    def __repr__(self):
        return (
            f"<HistorialEstadoCredito(id={self.id}, credito_id={self.credito_id}, "
            f"anterior='{self.estado_anterior}', nuevo='{self.estado_nuevo}', fecha='{self.fecha_cambio}')>"
        )


class HistorialEstadoCliente(Base):
    """
    =============================================================================
    Model: HistorialEstadoCliente
    Description: Registra las transiciones de estados de los clientes (ACTIVO,
                 MOROSO, INCOBRABLE, INACTIVO) para auditoría.
    =============================================================================
    """
    __tablename__ = "historial_estados_cliente"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_cuil = Column(String(11), ForeignKey("clientes.cuil", ondelete="CASCADE"), nullable=False, index=True)
    estado_anterior = Column(String(50), nullable=True)
    estado_nuevo = Column(String(50), nullable=False, index=True)
    fecha_cambio = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    origen = Column(String(50), default="MANUAL", nullable=False)
    motivo = Column(String(255), nullable=True)

    # Relationships
    cliente = relationship("Cliente", back_populates="historial_estados")
    usuario = relationship("Usuario")

    def __repr__(self):
        return (
            f"<HistorialEstadoCliente(id={self.id}, cliente_cuil='{self.cliente_cuil}', "
            f"anterior='{self.estado_anterior}', nuevo='{self.estado_nuevo}', fecha='{self.fecha_cambio}')>"
        )
