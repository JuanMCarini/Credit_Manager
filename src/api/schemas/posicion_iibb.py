from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime
from src.database.models.finance.posicion_iibb import EstadoPosicionIibb

class PosicionIibbBase(BaseModel):
    anio: int = Field(..., gt=2000)
    mes: int = Field(..., ge=1, le=12)
    iibb_ventas: Decimal = Field(default=0.0)
    retenciones_bancarias: Decimal = Field(default=0.0)
    percepciones_compras: Decimal = Field(default=0.0)
    pagos_vep: Decimal = Field(default=0.0)
    saldo_anterior: Decimal = Field(default=0.0)
    saldo_a_pagar: Decimal = Field(default=0.0)
    detalle_provincias: Optional[list] = Field(default=None)
    estado: EstadoPosicionIibb = Field(default=EstadoPosicionIibb.BORRADOR)

class PosicionIibbCreate(PosicionIibbBase):
    pass

class PosicionIibbUpdate(BaseModel):
    iibb_ventas: Optional[Decimal] = None
    retenciones_bancarias: Optional[Decimal] = None
    percepciones_compras: Optional[Decimal] = None
    pagos_vep: Optional[Decimal] = None
    saldo_anterior: Optional[Decimal] = None
    saldo_a_pagar: Optional[Decimal] = None
    detalle_provincias: Optional[list] = None
    estado: Optional[EstadoPosicionIibb] = None

class PosicionIibbResponse(PosicionIibbBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
