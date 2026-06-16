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

class CobranzaMasiva(BaseModel):
    identificador: str
    id_val: str
    cuotas: List[int]
    monto_total: float
    fecha_pago: Optional[date] = None

class ProcesoUpdate(BaseModel):
    estado: str
    descripcion: Optional[str] = None
