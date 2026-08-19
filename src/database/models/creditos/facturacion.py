from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Numeric, Date, DateTime, func
from sqlalchemy.orm import relationship
from src.database import Base

class Factura(Base):
    """
    =============================================================================
    Model: Factura
    =============================================================================
    Guarda los comprobantes electrónicos emitidos en ARCA (ex AFIP)
    asociados a las cobranzas.
    """
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cobranza_id = Column(Integer, ForeignKey("cobranzas.id"), nullable=False, unique=True)
    
    punto_venta = Column(Integer, nullable=False, default=1)
    tipo_comprobante = Column(Integer, nullable=False) # ej. 6 (Factura B), 11 (Factura C)
    nro_comprobante = Column(Integer, nullable=False)
    
    fecha_emision = Column(Date, nullable=False)
    importe_total = Column(Numeric(15, 2), nullable=False)
    
    cae = Column(String(50), nullable=True)
    vencimiento_cae = Column(Date, nullable=True)
    
    cuit_cliente = Column(String(20), nullable=True)
    
    # Audit
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    cobranza = relationship("Cobranza", back_populates="factura")

    def __repr__(self):
        return f"<Factura(pv={self.punto_venta}, comp={self.nro_comprobante}, cae={self.cae})>"
