import enum
import datetime
import numpy_financial as npf

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Numeric, Enum as SQLEnum, event
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from src.database import Base
from src.database.models.finance.comprobantes import Comprobante, TipoComprobante
from dateutil.relativedelta import relativedelta

class SistemaMatematico(enum.Enum):
    DIRECTO = "Amortización lineal directa (cuotas fijas)"
    FRANCES = "Sistema Francés"

class Denominador(enum.Enum):
    MENSUAL = "12"
    DIARIO = "365/30"

class Plan(Base):
    __tablename__ = "planes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_origen = Column(String(100), unique=True, nullable=False)
    fecha = Column(Date, nullable=False)
    proveedor_id = Column(ForeignKey("proveedores.id"), nullable=False)
    concepto_id = Column(ForeignKey("conceptos.id"), nullable=True)
    capital = Column(Numeric(12, 2), nullable=False)
    anticipo = Column(Numeric(12, 2), nullable=False)
    vencimiento_anticipo = Column(Date, nullable=True)
    plazo = Column(Integer, nullable=False) # Sin tener en cuenta el anticipo.
    valor_cuota = Column(Numeric(12, 2), nullable=False)
    primer_vencimiento = Column(Date, nullable=False)
    sistema = Column(SQLEnum(SistemaMatematico), nullable=False)
    denominador = Column(SQLEnum(Denominador), nullable=False)
    tna = Column(Numeric(12, 2), nullable=False)
    
    @validates("tna")
    def tasa(self, key, value):
        try:
            if self.sistema == SistemaMatematico.DIRECTO:
                return (self.valor_cuota*self.plazo/(self.capital - self.anticipo) - 1 ) / self.plazo * float(self.denominador.value)
            elif self.sistema == SistemaMatematico.FRANCES:
                return float(npf.rate(nper=self.plazo, pmt=self.valor_cuota, pv=-(self.capital - self.anticipo))*float(self.denominador.value))
        except Exception:
            pass
        return value

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    proveedor = relationship("Proveedor")
    concepto = relationship("Concepto")
    cuotas = relationship("Comprobante", back_populates="plan_pago", cascade="all, delete-orphan")

    @property
    def cuotas_pendientes(self):
        return [c for c in self.cuotas if c.estado != 'pagado']

@event.listens_for(Plan, 'after_insert')
def generar_comprobantes_cuotas(mapper, connection, target):

    comprobantes_data = []
    
    # Si hay anticipo, se genera su comprobante (cuota 0)
    if target.anticipo and target.anticipo > 0:
        comprobantes_data.append({
            "proveedor_id": target.proveedor_id,
            "concepto_id": target.concepto_id,
            "plan_pago_id": target.id,
            "tipo_comprobante": TipoComprobante.CUOTA.name, 
            "punto_venta": target.proveedor_id,
            "numero_comprobante": target.id*1000,
            "fecha_contable": target.fecha,
            "fecha_emision": target.fecha,
            "fecha_vencimiento": target.vencimiento_anticipo,
            "importe_total": target.anticipo,
            "estado": "pendiente",
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now()
        })
        
    # Se genera un comprobante por cada cuota, desplazando el vencimiento 1 mes con relativedelta
    for i in range(1, target.plazo+1):
        comprobantes_data.append({
            "proveedor_id": target.proveedor_id,
            "concepto_id": target.concepto_id,
            "plan_pago_id": target.id,
            "tipo_comprobante": TipoComprobante.CUOTA.name,
            "punto_venta": target.proveedor_id,
            "numero_comprobante": target.id*1000+i,
            "fecha_contable": target.fecha,
            "fecha_emision": target.fecha,
            "fecha_vencimiento": target.primer_vencimiento + relativedelta(months=i-1),
            "importe_total": target.valor_cuota,
            "estado": "pendiente",
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now()
        })
        
    if comprobantes_data:
        connection.execute(Comprobante.__table__.insert(), comprobantes_data)

