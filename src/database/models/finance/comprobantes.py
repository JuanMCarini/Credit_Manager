import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Numeric, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from src.database import Base

class CategoriaImpositiva(enum.Enum):
    CONSUMIDOR_FINAL = "CONSUMIDOR FINAL"
    RESPONSABLE_INSCRIPTO = "RESPONSABLE INSCRIPTO"
    MONOTRIBUTISTA = "MONOTRIBUTISTA"
    EXENTO = "EXENTO"
    IVA_NO_ALCANZADO = "IVA NO ALCANZADO"
    ESTATAL = "ORGANISMO ESTATAL"

class TipoDocumento(enum.Enum):
    CUIT = "CUIT"
    CUIL = "CUIL"
    DNI = "DNI"

class Personeria(enum.Enum):
    FISICA = "FISICA"
    JURIDICA = "JURIDICA"

class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    razon_social = Column(String(100), nullable=False)
    tipo_documento = Column(SQLEnum(TipoDocumento), nullable=False)
    nro_documento = Column(String(11), unique=True, nullable=False)
    personeria = Column(SQLEnum(Personeria), nullable=False)
    provincia_id = Column(ForeignKey("provincias.id"), nullable=False)
    localidad = Column(String(100), nullable=True)
    domicilio = Column(String(255), nullable=True)
    piso = Column(String(10), nullable=True)
    depto = Column(String(10), nullable=True)
    codigo_postal = Column(String(10), nullable=True)
    telefono = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    categoria_impositiva = Column(SQLEnum(CategoriaImpositiva), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    comprobantes = relationship("Comprobante", back_populates="proveedor")
    provincia = relationship("Provincia")
    concepto_id = Column(Integer, ForeignKey("conceptos.id"), nullable=True)
    concepto = relationship("Concepto")

class TipoComprobante(enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    E = "E"
    M = "M"
    TICKET = "TICKET"
    NOTA_DEBITO_A = "NOTA_DEBITO_A"
    NOTA_DEBITO_B = "NOTA_DEBITO_B"
    NOTA_CREDITO_A = "NOTA_CREDITO_A"
    NOTA_CREDITO_B = "NOTA_CREDITO_B"
    RECIBO = "RECIBO"
    CUOTA = "CUOTA"

class Comprobante(Base):
    __tablename__ = "comprobantes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proveedor_id = Column(ForeignKey("proveedores.id"), nullable=False)
    tipo_comprobante = Column(SQLEnum(TipoComprobante), nullable=False)
    punto_venta = Column(Integer, nullable=False)
    numero_comprobante = Column(Integer, nullable=False)
    
    # Relaciones
    proveedor = relationship("Proveedor", back_populates="comprobantes")
    concepto_id = Column(Integer, ForeignKey("conceptos.id"), nullable=True)
    concepto = relationship("Concepto")
    plan_pago_id = Column(Integer, ForeignKey("planes.id"), nullable=True)
    plan_pago = relationship("Plan", back_populates="cuotas")
    fecha_contable = Column(Date, nullable=False)
    fecha_emision = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)
    
    # Importes e Impuestos
    importe_no_gravado = Column(Numeric(12, 2), default=0.0)
    importe_exento = Column(Numeric(12, 2), default=0.0)
    neto_gravado_21 = Column(Numeric(12, 2), default=0.0)
    neto_gravado_105 = Column(Numeric(12, 2), default=0.0)
    neto_gravado_27 = Column(Numeric(12, 2), default=0.0)
    iva_21 = Column(Numeric(12, 2), default=0.0)
    iva_105 = Column(Numeric(12, 2), default=0.0)
    iva_27 = Column(Numeric(12, 2), default=0.0)
    percepcion_iva = Column(Numeric(12, 2), default=0.0)
    percepcion_iibb = Column(Numeric(12, 2), default=0.0)
    percepcion_ganancias = Column(Numeric(12, 2), default=0.0)
    otros_impuestos = Column(Numeric(12, 2), default=0.0)
    importe_total = Column(Numeric(12, 2), nullable=False, default=0.0)

    __table_args__ = (
        UniqueConstraint('proveedor_id', 'tipo_comprobante', 'punto_venta', 'numero_comprobante', name='uix_comprobante_unico'),
    )

    @validates('neto_gravado_21', 'neto_gravado_105', 'neto_gravado_27')
    def calcular_iva_automatico(self, key, value):
        from decimal import Decimal
        if value is not None:
            # Ensure value is a Decimal
            val = Decimal(str(value))
            if key == 'neto_gravado_21':
                self.iva_21 = round(val * Decimal('0.21'), 2)
            elif key == 'neto_gravado_105':
                self.iva_105 = round(val * Decimal('0.105'), 2)
            elif key == 'neto_gravado_27':
                self.iva_27 = round(val * Decimal('0.27'), 2)
        return value

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Estado del comprobante
    importe_cancelado = Column(Numeric(12, 2), nullable=False, default=0.0)
    fecha_cancelacion = Column(Date, nullable=True)
    estado = Column(SQLEnum('pendiente', 'pagado', 'parcial', name='estado_comprobante_enum'), nullable=False, default='pendiente')

    @validates('importe_cancelado', 'importe_total')
    def calcular_estado(self, key, value):
        # We need both values to determine status
        # Since this is a validator for BOTH keys, one is updated by `value` and the other is `self.X`
        cancelado = value if key == 'importe_cancelado' else getattr(self, 'importe_cancelado', 0)
        total = value if key == 'importe_total' else getattr(self, 'importe_total', 0)
        
        cancelado = cancelado or 0
        total = total or 0
        
        if total > 0 and cancelado >= total:
            self.estado = 'pagado'
        elif cancelado > 0:
            self.estado = 'parcial'
        else:
            self.estado = 'pendiente'
            
        return value

    # Archivo Adjunto (PDF)
    archivo_pdf = Column(String(255), nullable=True)

    # Relación a cancelaciones (pagos parciales)
    cancelaciones = relationship("CancelacionComprobante", back_populates="comprobante", cascade="all, delete-orphan")


class CancelacionComprobante(Base):
    __tablename__ = "cancelaciones_comprobante"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comprobante_id = Column(ForeignKey("comprobantes.id", ondelete="CASCADE"), nullable=False)
    importe = Column(Numeric(12, 2), nullable=False)
    fecha_cancelacion = Column(Date, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    comprobante = relationship("Comprobante", back_populates="cancelaciones")