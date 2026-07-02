from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel
from src.database.models.creditos import TipoCredito

class TransferenciaCreate(BaseModel):
    cbu: str
    monto: float
    cuit: str
    razon_social: str

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
    transferencias: Optional[List[TransferenciaCreate]] = []

class CreditoEstadoUpdate(BaseModel):
    estado: str

class DocumentoLegajoOut(BaseModel):
    id: int
    credito_id: int
    nombre_archivo: str
    ruta_archivo: str
    tipo_archivo: str
    fecha_subida: datetime
    transferencia_id: Optional[int] = None

    class Config:
        from_attributes = True
