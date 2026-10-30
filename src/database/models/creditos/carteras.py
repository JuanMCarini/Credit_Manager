import enum
from datetime import date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Numeric,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from src.database import Base


class TipoOperacionCartera(str, enum.Enum):
    COMPRA = "COMPRA"
    VENTA = "VENTA"
    RECOMPRA = "RECOMPRA"


class EstadoCartera(str, enum.Enum):
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
    fecha_generacion = Column(Date, nullable=False, default=date.today)

    # Relationships
    creditos_incluidos = relationship("Credito", back_populates="cartera")
    operaciones = relationship("OperacionCartera", back_populates="cartera")
    socio = relationship("SocioComercial", back_populates="carteras")
    liquidaciones = relationship("LiquidacionCuotaCedida", back_populates="cartera")
    documentos = relationship("DocumentoCartera", back_populates="cartera", cascade="all, delete-orphan")

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


class DocumentoCartera(Base):
    """
    Model: DocumentoCartera
    Attached documents and signed contracts for a Cartera batch.
    """

    __tablename__ = "documentos_cartera"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cartera_id = Column(Integer, ForeignKey("carteras.id", ondelete="CASCADE"), nullable=False)
    nombre_archivo = Column(String(255), nullable=False)
    ruta_archivo = Column(String(500), nullable=False)
    tipo_archivo = Column(String(50), nullable=False)
    fecha_subida = Column(DateTime, default=func.now(), nullable=False)
    es_contrato_firmado = Column(Boolean, default=True, nullable=False)

    # Relationships
    cartera = relationship("Cartera", back_populates="documentos")

    def __repr__(self):
        return f"<DocumentoCartera(id={self.id}, cartera_id={self.cartera_id}, nombre_archivo='{self.nombre_archivo}')>"
