from typing import Optional, List
from datetime import date
from pydantic import BaseModel

class CobranzaIndividual(BaseModel):
    identificador: str
    id_val: str
    monto: float
    fecha_pago: Optional[date] = None
    fecha_corte: Optional[date] = None
    anticipada: bool = False

class CobranzaRecurso(BaseModel):
    identificador: str
    id_val: str
    monto: float
    fecha_pago: Optional[date] = None

class CobranzaMasiva(BaseModel):
    identificador: str
    id_val: str
    cuotas: List[int]
    monto_total: float
    fecha_pago: Optional[date] = None

class ProcesoUpdate(BaseModel):
    estado: str
    descripcion: Optional[str] = None

class CobranzaResponse(BaseModel):
    ID: int
    Proceso_ID: Optional[str] = None
    Fecha_Emision: str
    Credito_ID: Optional[str] = None
    Cliente_CUIL: Optional[str] = None
    Cuota_Nro: str
    Fecha_Vencimiento: str
    Tipo: str
    Capital: float
    Interes: float
    IVA: float
    Total: float

    class Config:
        populate_by_name = True
        alias_generator = lambda string: string.replace('_', ' ')

class CobranzaListResponse(BaseModel):
    items: List[CobranzaResponse]
    total: int
