import enum
from datetime import date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import relationship

from src.database import Base


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

    tipo_cobranza = Column(
        Enum(TipoCobranzaEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=TipoCobranzaEnum.COMUN.value,
    )

    capital = Column(Float, nullable=False)
    interes = Column(Float, nullable=False)
    iva = Column(Float, nullable=False)
    fecha = Column(Date, nullable=False)

    # Relationships
    cuota = relationship("Cuota", back_populates="cobranzas")
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

    tipo_liquidacion = Column(
        Enum(TipoLiquidacionEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=TipoLiquidacionEnum.NORMAL.value,
    )

    capital = Column(Float, nullable=False, default=0.0)
    interes = Column(Float, nullable=False, default=0.0)
    iva = Column(Float, nullable=False, default=0.0)
    fecha_pago = Column(Date, nullable=True)
    cancelada = Column(Boolean, nullable=False, default=False)

    # Relationships
    cuota = relationship("Cuota", back_populates="liquidaciones")
    cartera = relationship("Cartera", back_populates="liquidaciones")
    cobranza = relationship("Cobranza", back_populates="liquidaciones")

    @property
    def importe_total(self) -> float:
        return self.capital + self.interes + self.iva

    def __repr__(self):
        return f"<Liquidacion(cuota_id={self.cuota_id}, tipo={self.tipo_liquidacion}, total={self.importe_total})>"
