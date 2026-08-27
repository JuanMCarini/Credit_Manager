from sqlalchemy import (
    DateTime,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import Base



class Inversor(Base):
    """
    =============================================================================
    Model: Inversor
    =============================================================================
    """

    __tablename__ = "inversores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuit = Column(String(11), unique=True, nullable=False)
    razon_social = Column(String(100), unique=True, nullable=False)
    domicilio_legal = Column(String(200), nullable=True)
    mail = Column(String(150), nullable=True)
    telefono = Column(String(50), nullable=True)
    cbu = Column(String(22), nullable=True)
    nro_cuenta_bancaria = Column(String(50), nullable=True)
    nombre_banco = Column(String(100), nullable=True)
    activo = Column(Boolean, default=True)

    created_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    titularidades_assoc = relationship("TitularidadCuentaComitente", back_populates="inversor")
    movimientos_assoc = relationship("TitularidadMovimientoDeuda", back_populates="inversor")

class CuentaComitente(Base):
    """
    =============================================================================
    Model: Cuenta Comitente
    =============================================================================
    """

    __tablename__ = "cuentas_comitentes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_externo = Column(Integer, unique=True, nullable=True)
    conjunta = Column(Boolean, default=False)

    created_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    titulares_assoc = relationship("TitularidadCuentaComitente", back_populates="cuenta_comitente", order_by="TitularidadCuentaComitente.orden", cascade="all, delete-orphan")
    movimientos = relationship("MovimientoDeuda", back_populates="cuenta_comitente")

class TitularidadCuentaComitente(Base):
    """
    =============================================================================
    Model: Titularidad Cuenta Comitente
    =============================================================================
    """

    __tablename__ = "titularidad_cuenta_comitente"
    __table_args__ = (
        UniqueConstraint('id_cuenta_comitente', 'orden', name='uq_cuenta_comitente_orden'),
        UniqueConstraint('id_cuenta_comitente', 'id_inversor', name='uq_cuenta_comitente_inversor'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_cuenta_comitente = Column(Integer, ForeignKey("cuentas_comitentes.id"), nullable=False)
    id_inversor = Column(Integer, ForeignKey("inversores.id"), nullable=False)
    orden = Column(Integer, nullable=False, default=1)
    activo = Column(Boolean, default=True)

    created_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    cuenta_comitente = relationship("CuentaComitente", back_populates="titulares_assoc")
    inversor = relationship("Inversor", back_populates="titularidades_assoc")
