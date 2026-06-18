import enum
from datetime import date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    Numeric,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from src.database import Base


class TipoOperacionCartera(enum.Enum):
    COMPRA = "COMPRA"
    VENTA = "VENTA"
    RECOMPRA = "RECOMPRA"


class EstadoCartera(enum.Enum):
    PENDIENTE = "PENDIENTE"
    COMPRADA = "COMPRADA"
    VENDIDA = "VENDIDA"


class Cartera(Base):
    """
    =============================================================================
    Model: Cartera
    =============================================================================
    """

    __tablename__ = "carteras"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), unique=True, nullable=False)
    fecha_compra = Column(Date, nullable=False)

    socio_id = Column(Integer, ForeignKey("socios_comerciales.id"), nullable=False)

    iva = Column(Boolean, default=False)
    recurso = Column(Boolean, default=True)

    tna_descuento = Column(Numeric(15, 6), nullable=False)

    tipo_operacion = Column(
        Enum(TipoOperacionCartera), nullable=False, default=TipoOperacionCartera.COMPRA
    )
    estado = Column(
        Enum(EstadoCartera), nullable=False, default=EstadoCartera.PENDIENTE
    )
    fecha_generacion = Column(Date, nullable=False, default=date.today())

    # Relationships
    creditos_incluidos = relationship("Credito", back_populates="cartera")
    operaciones = relationship("OperacionCartera", back_populates="cartera")
    socio = relationship("SocioComercial", back_populates="carteras")
    liquidaciones = relationship("LiquidacionCuotaCedida", back_populates="cartera")

    def __repr__(self):
        return f"<Cartera(nombre='{self.nombre}', socio_id={self.socio_id}, tipo={self.tipo_operacion}, fecha_compra={self.fecha_compra}, tna_desc={self.tna_descuento})>"


class OperacionCartera(Base):
    """
    Mapping table: Assigns a specific Installment (Cuota) to a Cartera batch.
    Allows granular tracking for partial repurchases.
    """

    __tablename__ = "operaciones_cartera"

    id = Column(Integer, primary_key=True, autoincrement=True)

    cuota_id = Column(Integer, ForeignKey("cuotas.id"), nullable=False)
    cartera_id = Column(Integer, ForeignKey("carteras.id"), nullable=True)
    cuota_comercializada = Column(Boolean, default=False)
    fecha_registro = Column(Date, nullable=False)

    # Relationships
    cuota = relationship("Cuota", back_populates="movimientos_cartera")
    cartera = relationship("Cartera", back_populates="operaciones")
