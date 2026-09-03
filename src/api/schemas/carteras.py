from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field

class VentaCarteraRequest(BaseModel):
    nombre_cartera: str
    fecha_venta: date
    tna_descuento: float
    cuit_comprador: str
    razon_social_comprador: str
    mora: bool = False
    recurso: bool = True
    iva: bool = False
    fecha_emision_desde: Optional[date] = None
    fecha_emision_hasta: Optional[date] = None
    fecha_vencimiento_desde: Optional[date] = None
    fecha_vencimiento_hasta: Optional[date] = None
    creditos_excluidos: List[int] = Field(default_factory=list)
    cartera_id: Optional[int] = None
    usar_cuotas_guardadas: bool = False
    cuotas_completas: bool = False
    socio_originador_id: Optional[List[int]] = None

class UpdateCarteraRequest(BaseModel):
    nombre: Optional[str] = None
    fecha_compra: Optional[date] = None
    tna_descuento: Optional[float] = None
    recurso: Optional[bool] = None
    iva: Optional[bool] = None
    estado: Optional[str] = None
