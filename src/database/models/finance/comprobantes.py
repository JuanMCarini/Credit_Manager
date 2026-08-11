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
    localidad_id = Column(ForeignKey("localidades.id"), nullable=True)
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
    localidad = relationship("Localidad")

class TipoComprobante(enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    E = "E"
    M = "M"
    TICKET = "TICKET"
    NOTA_DEBITO = "NOTA_DEBITO"
    NOTA_CREDITO = "NOTA_CREDITO"
    RECIBO = "RECIBO"

class Comprobante(Base):
    __tablename__ = "comprobantes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    proveedor_id = Column(ForeignKey("proveedores.id"), nullable=False)
    tipo_comprobante = Column(SQLEnum(TipoComprobante), nullable=False)
    punto_venta = Column(Integer, nullable=False)
    numero_comprobante = Column(Integer, nullable=False)
    
    # Relaciones
    proveedor = relationship("Proveedor", back_populates="comprobantes")
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
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('proveedor_id', 'tipo_comprobante', 'punto_venta', 'numero_comprobante', name='uix_comprobante_unico'),
    )

    def calcular_total(self):
        """Calcula el importe total sumando todos los conceptos."""
        self.importe_total = round(
            (self.importe_no_gravado or 0) +
            (self.importe_exento or 0) +
            (self.neto_gravado_21 or 0) +
            (self.neto_gravado_105 or 0) +
            (self.neto_gravado_27 or 0) +
            (self.iva_21 or 0) +
            (self.iva_105 or 0) +
            (self.iva_27 or 0) +
            (self.percepcion_iva or 0) +
            (self.percepcion_iibb or 0) +
            (self.percepcion_ganancias or 0) +
            (self.otros_impuestos or 0), 2
        )

    @validates('neto_gravado_21', 'neto_gravado_105', 'neto_gravado_27')
    def calcular_iva_automatico(self, key, value):
        if value is not None:
            if key == 'neto_gravado_21':
                self.iva_21 = round(value * 0.21, 2)
            elif key == 'neto_gravado_105':
                self.iva_105 = round(value * 0.105, 2)
            elif key == 'neto_gravado_27':
                self.iva_27 = round(value * 0.27, 2)
        return value