from typing import Optional
from datetime import date
from pydantic import BaseModel
from src.database.models.creditos import TipoCredito

class CreditoCreate(BaseModel):
    cliente_cuil: str
    capital: float
    tna_c_iva: float
    plazo: int
    socio_originador_id: Optional[int] = None
    comision_id: Optional[int] = None
    fecha_emision: Optional[date] = None
    dia_vencimiento: int = 28
    tipo_credito: TipoCredito = TipoCredito.FRANCES

class CreditoEstadoUpdate(BaseModel):
    estado: str
