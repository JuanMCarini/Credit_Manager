from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import date

class LiquidacionResponse(BaseModel):
    id: int
    cuota_id: int
    cartera_id: int
    cobranza_id: Optional[int] = None
    tipo_liquidacion: str
    capital: float
    interes: float
    iva: float
    importe_total: float
    fecha_pago: Optional[date] = None
    cancelada: bool

    class Config:
        from_attributes = True

class LiquidacionProcessRequest(BaseModel):
    id_val: Union[int, str, List[Union[int, str]]]
    identificador: str = "CLIENTE ID" # "CLIENTE ID" or "CLIENTE CUIT"
    fecha_corte: Optional[date] = None
    fecha_vencimiento_desde: Optional[date] = None
    fecha_vencimiento_hasta: Optional[date] = None

class LiquidacionPreviewResponse(BaseModel):
    cuota_id: int
    cartera_id: int
    tipo_liquidacion: str
    capital: float
    interes: float
    iva: float
    cobranza_id: Optional[int] = None

class CompradorResponse(BaseModel):
    id: int
    razon_social: str
    cuit: str
