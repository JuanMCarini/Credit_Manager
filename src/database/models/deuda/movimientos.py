import enum
from sqlalchemy import (
    Enum,
    Column,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Date,
    Numeric,
    DateTime,
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
    fecha = Column(DateTime, nullable=False)
    monto = Column(Numeric(18, 2), nullable=False)
    tipo_movimiento = Column(Enum(TipoMovimiento), nullable=False)

    created_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    cuenta_comitente = relationship("CuentaComitente", back_populates="movimientos")
    serie = relationship("Serie", back_populates="movimientos")