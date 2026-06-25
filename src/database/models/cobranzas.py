import enum
from datetime import date, datetime

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
)
from sqlalchemy.orm import relationship

from src.database import Base


class TipoProcesoEnum(enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    MASIVO_CSV = "MASIVO_CSV"
    LIQUIDACIONES_INDIVIDUALES = "LIQUIDACIONES_INDIVIDUALES"
    LIQUIDACIONES_MASIVAS = "LIQUIDACIONES_MASIVAS"
    RECURSO = "RECURSO"


class EstadoProcesoEnum(enum.Enum):
    COMPLETADO = "COMPLETADO"
    REVERTIDO = "REVERTIDO"
    PROCESANDO = "PROCESANDO"
    PENDIENTE = "PENDIENTE"
    FALLIDO = "FALLIDO"


class Proceso(Base):
    """
    =============================================================================
    Model: Proceso
    =============================================================================
    Representa un agrupador o 'lote' lógico para la ingesta de pagos.
    Envuelve tanto a cobranzas aisladas como a importaciones masivas.
    
    Parameters:
    - tipo: Define el origen (e.g. INDIVIDUAL, MASIVO_CSV).
    - estado: Estado de ejecución (e.g. COMPLETADO, REVERTIDO).
    - fecha_ejecucion: Timestamp de cuando se ejecutó o ingirió.
    """

    __tablename__ = "procesos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    tipo = Column(
        Enum(TipoProcesoEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=TipoProcesoEnum.INDIVIDUAL.value,
    )
    
    estado = Column(
        Enum(EstadoProcesoEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=EstadoProcesoEnum.COMPLETADO.value,
    )
    
    descripcion = Column(String, nullable=True)
    
    fecha_ejecucion = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relación 1:N con Cobranza.
    # MANDATORIO: cascade="all, delete-orphan" garantiza que la eliminación del
    # proceso borre automáticamente las cobranzas asociadas, manteniendo la integridad
    # referencial sin dejar registros huérfanos. Si alguna Cobranza tiene 
    # liquidaciones asociadas, el motor abortará la operación por integridad foránea.
    cobranzas = relationship(
        "Cobranza", 
        back_populates="proceso", 
        cascade="all, delete-orphan"
    )
    liquidaciones = relationship(
        "LiquidacionCuotaCedida",
        back_populates="proceso",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Proceso(id={self.id}, tipo={self.tipo}, estado={self.estado})>"


class TipoCobranzaEnum(enum.Enum):
    COMUN = "COMUN"
    ANTICIPO = "ANTICIPO"
    CA = "CANCELACION ANTICIPADA"
    BCA = "BONIFICACION POR CANCELACION ANTICIPADA"
    CNC = "CUOTA NO COMPRADA"
    PENALTY = "PENALTY"
    RECURSO = "RECURSO"
    AJUSTE = "AJUSTE"


class Cobranza(Base):
    """
    =============================================================================
    Model: Cobranza
    =============================================================================
    """

    __tablename__ = "cobranzas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuota_id = Column(Integer, ForeignKey("cuotas.id"), nullable=False)
    proceso_id = Column(Integer, ForeignKey("procesos.id"), nullable=True)

    tipo_cobranza = Column(
        Enum(TipoCobranzaEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=TipoCobranzaEnum.COMUN.value,
    )

    capital = Column(Numeric(15, 2), nullable=False)
    interes = Column(Numeric(15, 2), nullable=False)
    iva = Column(Numeric(15, 2), nullable=False)
    fecha = Column(Date, nullable=False)

    # Relationships
    cuota = relationship("Cuota", back_populates="cobranzas")
    proceso = relationship("Proceso", back_populates="cobranzas")
    liquidaciones = relationship("LiquidacionCuotaCedida", back_populates="cobranza")

    @property
    def importe_total(self) -> float:
        return self.capital + self.interes + self.iva

    def __repr__(self):
        return f"<Cobranza(cuota_id={self.cuota_id}, tipo={self.tipo_cobranza}, total={self.importe_total})>"


class TipoLiquidacionEnum(enum.Enum):
    PENDIENTE = "PENDIENTE"
    NORMAL = "NORMAL"
    RECURSO = "RECURSO"
    CA = "CANCELACION ANTICIPADA"
    BCA = "BONIFICACION POR CANCELACION ANTICIPADA"
    IP = "INTERESES PERDIDOS"


class LiquidacionCuotaCedida(Base):
    """
    Records payments (rendiciones/liquidaciones) made to the partner that purchased the portfolio.
    Acts as a mirror to Cobranza but for liabilities.
    """

    __tablename__ = "liquidaciones_cuotas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuota_id = Column(Integer, ForeignKey("cuotas.id"), nullable=False)
    cartera_id = Column(Integer, ForeignKey("carteras.id"), nullable=False)
    cobranza_id = Column(Integer, ForeignKey("cobranzas.id"), nullable=True)
    proceso_id = Column(Integer, ForeignKey("procesos.id"), nullable=True)

    tipo_liquidacion = Column(
        Enum(TipoLiquidacionEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=TipoLiquidacionEnum.NORMAL.value,
    )

    capital = Column(Numeric(15, 2), nullable=False, default=0.0)
    interes = Column(Numeric(15, 2), nullable=False, default=0.0)
    iva = Column(Numeric(15, 2), nullable=False, default=0.0)
    fecha_pago = Column(Date, nullable=True)
    cancelada = Column(Boolean, nullable=False, default=False)

    # Relationships
    cuota = relationship("Cuota", back_populates="liquidaciones")
    cartera = relationship("Cartera", back_populates="liquidaciones")
    cobranza = relationship("Cobranza", back_populates="liquidaciones")
    proceso = relationship("Proceso", back_populates="liquidaciones")

    @property
    def importe_total(self) -> float:
        return self.capital + self.interes + self.iva

    def __repr__(self):
        return f"<Liquidacion(cuota_id={self.cuota_id}, tipo={self.tipo_liquidacion}, total={self.importe_total})>"
