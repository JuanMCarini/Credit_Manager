from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from src.database.models.finance.comprobantes import CategoriaImpositiva, TipoDocumento, Personeria, TipoComprobante
from src.api.schemas.bancos import ConceptoResponse

# -------------------------------------------------------------------
# Proveedor Schemas
# -------------------------------------------------------------------
class ProveedorBase(BaseModel):
    razon_social: str = Field(..., max_length=100)
    tipo_documento: TipoDocumento
    nro_documento: str = Field(..., max_length=11)
    personeria: Personeria
    provincia_id: int
    localidad: Optional[str] = Field(None, max_length=100)
    domicilio: Optional[str] = Field(None, max_length=255)
    piso: Optional[str] = Field(None, max_length=10)
    depto: Optional[str] = Field(None, max_length=10)
    codigo_postal: Optional[str] = Field(None, max_length=10)
    telefono: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    categoria_impositiva: CategoriaImpositiva
    concepto_id: Optional[int] = None

class ProveedorCreate(ProveedorBase):
    pass

class ProveedorUpdate(BaseModel):
    razon_social: Optional[str] = Field(None, max_length=100)
    tipo_documento: Optional[TipoDocumento] = None
    nro_documento: Optional[str] = Field(None, max_length=11)
    personeria: Optional[Personeria] = None
    provincia_id: Optional[int] = None
    localidad: Optional[str] = Field(None, max_length=100)
    domicilio: Optional[str] = Field(None, max_length=255)
    piso: Optional[str] = Field(None, max_length=10)
    depto: Optional[str] = Field(None, max_length=10)
    codigo_postal: Optional[str] = Field(None, max_length=10)
    telefono: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    categoria_impositiva: Optional[CategoriaImpositiva] = None
    concepto_id: Optional[int] = None

class ProveedorResponse(ProveedorBase):
    id: int
    created_at: datetime
    updated_at: datetime
    concepto: Optional[ConceptoResponse] = None

    model_config = ConfigDict(from_attributes=True)

# -------------------------------------------------------------------
# Comprobante Schemas
# -------------------------------------------------------------------
class ComprobanteBase(BaseModel):
    proveedor_id: int
    tipo_comprobante: TipoComprobante
    punto_venta: int
    numero_comprobante: int
    fecha_contable: date
    fecha_emision: date
    fecha_vencimiento: Optional[date] = None
    concepto_id: Optional[int] = None
    importe_no_gravado: Decimal = Field(default=Decimal('0.0'))
    importe_exento: Decimal = Field(default=Decimal('0.0'))
    neto_gravado_21: Decimal = Field(default=Decimal('0.0'))
    neto_gravado_105: Decimal = Field(default=Decimal('0.0'))
    neto_gravado_27: Decimal = Field(default=Decimal('0.0'))
    iva_21: Decimal = Field(default=Decimal('0.0'))
    iva_105: Decimal = Field(default=Decimal('0.0'))
    iva_27: Decimal = Field(default=Decimal('0.0'))
    percepcion_iva: Decimal = Field(default=Decimal('0.0'))
    percepcion_iibb: Decimal = Field(default=Decimal('0.0'))
    percepcion_ganancias: Decimal = Field(default=Decimal('0.0'))
    otros_impuestos: Decimal = Field(default=Decimal('0.0'))
    importe_cancelado: Decimal = Field(default=Decimal('0.0'))
    importe_total: Optional[Decimal] = None

class ComprobanteCreate(ComprobanteBase):
    pass

class ComprobanteUpdate(BaseModel):
    proveedor_id: Optional[int] = None
    tipo_comprobante: Optional[TipoComprobante] = None
    punto_venta: Optional[int] = None
    numero_comprobante: Optional[int] = None
    fecha_contable: Optional[date] = None
    fecha_emision: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    concepto_id: Optional[int] = None
    importe_no_gravado: Optional[Decimal] = None
    importe_exento: Optional[Decimal] = None
    neto_gravado_21: Optional[Decimal] = None
    neto_gravado_105: Optional[Decimal] = None
    neto_gravado_27: Optional[Decimal] = None
    iva_21: Optional[Decimal] = None
    iva_105: Optional[Decimal] = None
    iva_27: Optional[Decimal] = None
    percepcion_iva: Optional[Decimal] = None
    percepcion_iibb: Optional[Decimal] = None
    percepcion_ganancias: Optional[Decimal] = None
    otros_impuestos: Optional[Decimal] = None
    importe_cancelado: Optional[Decimal] = None
    importe_total: Optional[Decimal] = None

class CancelacionBase(BaseModel):
    importe: Decimal
    fecha_cancelacion: date
    movimiento_id: Optional[int] = None

class CancelacionCreate(CancelacionBase):
    pass

class CancelacionResponse(CancelacionBase):
    id: int
    comprobante_id: int
    created_at: datetime
    updated_at: datetime
    movimiento_info: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)

class ComprobanteResponse(ComprobanteBase):
    id: int
    importe_total: Decimal
    estado: str
    archivo_pdf: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    proveedor: Optional[ProveedorResponse] = None
    concepto: Optional[ConceptoResponse] = None
    cancelaciones: Optional[List[CancelacionResponse]] = []

    model_config = ConfigDict(from_attributes=True)
