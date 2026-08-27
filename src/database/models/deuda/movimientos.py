import enum
from sqlalchemy import (
    Enum,
    Column,
    ForeignKey,
    Integer,
    String,
    Numeric,
    DateTime,
    UniqueConstraint,
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import Base

class TipoMovimiento(enum.Enum):
    SUSCRIPCION = "Suscripción"
    RESCATE = "Rescate"
    VENCIMIENTO = "Vencimiento"
    RETIRO_INTERESES = "Retiro de intereses"
    RENOVACION = "Renovación"

class MovimientoDeuda(Base):

    __tablename__ = "movimientos_deuda"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cuenta_comitente = Column(Integer, ForeignKey("cuentas_comitentes.id"), nullable=False)
    id_serie = Column(Integer, ForeignKey("series.id"), nullable=False)
    id_serie_destino = Column(Integer, ForeignKey("series.id"), nullable=True)
    fecha = Column(DateTime, nullable=False)
    monto = Column(Numeric(18, 2), nullable=False)
    tipo_movimiento = Column(Enum(TipoMovimiento), nullable=False)
    observaciones = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    cuenta_comitente = relationship("CuentaComitente", back_populates="movimientos")
    serie = relationship("Serie", foreign_keys=[id_serie], back_populates="movimientos")
    serie_destino = relationship("Serie", foreign_keys=[id_serie_destino], back_populates="movimientos_destino")
    titulares_assoc = relationship("TitularidadMovimientoDeuda", back_populates="movimiento", cascade="all, delete-orphan")


class TitularidadMovimientoDeuda(Base):
    """
    =============================================================================
    Model: Titularidad Movimiento Deuda
    =============================================================================
    """

    __tablename__ = "titularidad_movimiento_deuda"
    __table_args__ = (
        UniqueConstraint('id_movimiento_deuda', 'id_inversor', name='uq_movimiento_deuda_inversor'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_movimiento_deuda = Column(Integer, ForeignKey("movimientos_deuda.id"), nullable=False)
    id_inversor = Column(Integer, ForeignKey("inversores.id"), nullable=False)

    created_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    movimiento = relationship("MovimientoDeuda", back_populates="titulares_assoc")
    inversor = relationship("Inversor", back_populates="movimientos_assoc")