import enum
from sqlalchemy import Column, Integer, String, Numeric, Enum as SQLEnum, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from src.database import Base

class EstadoPosicionIva(enum.Enum):
    BORRADOR = "Borrador"
    GUARDADO = "Guardado"

class PosicionIva(Base):
    __tablename__ = "posiciones_iva"

    id = Column(Integer, primary_key=True, autoincrement=True)
    anio = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    
    iva_ventas = Column(Numeric(15, 2), nullable=False, default=0.0)
    iva_compras = Column(Numeric(15, 2), nullable=False, default=0.0)
    retenciones_bancarias = Column(Numeric(15, 2), nullable=False, default=0.0)
    percepciones_compras = Column(Numeric(15, 2), nullable=False, default=0.0)
    pagos_vep = Column(Numeric(15, 2), nullable=False, default=0.0)
    saldo_anterior = Column(Numeric(15, 2), nullable=False, default=0.0)
    saldo_a_pagar = Column(Numeric(15, 2), nullable=False, default=0.0)
    
    estado = Column(SQLEnum(EstadoPosicionIva), nullable=False, default=EstadoPosicionIva.BORRADOR)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('anio', 'mes', name='uix_posicion_iva_periodo'),
    )

    def __repr__(self):
        return f"<PosicionIva(anio={self.anio}, mes={self.mes}, saldo_a_pagar={self.saldo_a_pagar})>"
