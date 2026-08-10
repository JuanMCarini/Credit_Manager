import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base

class CategoriaMovimiento(enum.Enum):
    INGRESO = "Ingreso"
    EGRESO = "Egreso"
    SUSCRIPCION_FCI = "Suscripción FCI"
    RESCATE_FCI = "Rescate FCI"
    PLAZO_FIJO_INGRESOS = "Ingresos a plazo fijo"
    PLAZO_FIJO_EGRESOS = "Egresos de plazo fijo"

class Banco(Base):
    __tablename__ = "bancos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_banco = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relación a Cuentas
    cuentas = relationship("Cuenta", back_populates="banco")

class Cuenta(Base):
    __tablename__ = "cuentas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), unique=True, nullable=False)
    banco_id = Column(Integer, ForeignKey("bancos.id"), nullable=False)
    nro = Column(String(20), unique=False, nullable=False)
    cbu = Column(String(22), nullable=False, unique=True)
    alias = Column(String(50), nullable=False, unique=True)
    tipo_cuenta = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    banco = relationship("Banco", back_populates="cuentas")
    movimientos = relationship("Movimiento", back_populates="cuenta")

    @property
    def saldo(self) -> float:
        # Sumamos o restamos dependiendo del tipo de movimiento
        total = 0.0
        for mov in self.movimientos:
            if mov.concepto.tipo_movimiento in (CategoriaMovimiento.INGRESO, CategoriaMovimiento.RESCATE_FCI, CategoriaMovimiento.PLAZO_FIJO_EGRESOS):
                total += mov.monto
            elif mov.concepto.tipo_movimiento in (CategoriaMovimiento.EGRESO, CategoriaMovimiento.SUSCRIPCION_FCI, CategoriaMovimiento.PLAZO_FIJO_INGRESOS):
                total -= mov.monto
        return total

    @property
    def saldo_fci(self) -> float:
        # Sumamos o restamos dependiendo del tipo de movimiento
        total = 0.0
        for mov in self.movimientos:
            if mov.concepto.tipo_movimiento == CategoriaMovimiento.RESCATE_FCI:
                total -= mov.monto
            elif mov.concepto.tipo_movimiento == CategoriaMovimiento.SUSCRIPCION_FCI:
                total += mov.monto
        return total

    @property
    def saldo_plazo_fijo(self) -> float:
        # Sumamos o restamos dependiendo del tipo de movimiento
        total = 0.0
        for mov in self.movimientos:
            if mov.concepto.tipo_movimiento == CategoriaMovimiento.PLAZO_FIJO_INGRESOS:
                total += mov.monto
            elif mov.concepto.tipo_movimiento == CategoriaMovimiento.PLAZO_FIJO_EGRESOS:
                total -= mov.monto
        return total

class Concepto(Base):
    __tablename__ = "conceptos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    tipo_movimiento = Column(SQLEnum(CategoriaMovimiento), nullable=False)
    descripcion = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relación a Movimientos
    movimientos = relationship("Movimiento", back_populates="concepto")

class Movimiento(Base):
    __tablename__ = "movimientos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuenta_id = Column(Integer, ForeignKey("cuentas.id"), nullable=False)
    fecha = Column(Date, nullable=False)
    monto = Column(Float, nullable=False)
    concepto_id = Column(Integer, ForeignKey("conceptos.id"), nullable=False)
    descripcion = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    concepto = relationship("Concepto", back_populates="movimientos")
    cuenta = relationship("Cuenta", back_populates="movimientos")
