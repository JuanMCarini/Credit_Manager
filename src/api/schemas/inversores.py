from pydantic import BaseModel, Field, constr
from typing import Optional, List
from datetime import date, datetime
from src.database.models.deuda.movimientos import TipoMovimiento

# -----------------
# INVERSOR
# -----------------
class InversorBase(BaseModel):
    cuit: str = Field(..., max_length=11)
    razon_social: str = Field(..., max_length=100)
    domicilio_legal: Optional[str] = None
    mail: Optional[str] = None
    telefono: Optional[str] = None
    cbu: Optional[str] = None
    nro_cuenta_bancaria: Optional[str] = None
    nombre_banco: Optional[str] = None
    activo: bool = True

class InversorCreate(InversorBase):
    pass

class InversorResponse(InversorBase):
    id: int
    created_at: datetime
    update_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# -----------------
# CUENTA COMITENTE
# -----------------
class CuentaComitenteBase(BaseModel):
    id_bcbb: int
    conjunta: bool = False

class TitularidadCuentaComitenteBase(BaseModel):
    id_inversor: int
    orden: int = 1
    activo: bool = True

class TitularidadCuentaComitenteResponse(TitularidadCuentaComitenteBase):
    id: int
    inversor: InversorResponse

    class Config:
        orm_mode = True

class CuentaComitenteCreate(CuentaComitenteBase):
    titulares: List[TitularidadCuentaComitenteBase] = []

class CuentaComitenteResponse(CuentaComitenteBase):
    id: int
    created_at: datetime
    titulares: List[TitularidadCuentaComitenteResponse] = []

    class Config:
        orm_mode = True

# -----------------
# SERIE
# -----------------
class SerieBase(BaseModel):
    name: str = Field(..., max_length=100)
    fecha_suscripcion: date
    tna: float
    plazo: int

class SerieCreate(SerieBase):
    pass

class SerieResponse(SerieBase):
    id: int
    fecha_vencimiento: date
    created_at: datetime

    class Config:
        orm_mode = True

# -----------------
# MOVIMIENTO DEUDA
# -----------------
class MovimientoDeudaBase(BaseModel):
    id_cuenta_comitente: int
    id_serie: int
    fecha: datetime
    monto: float
    tipo_movimiento: TipoMovimiento

class MovimientoDeudaCreate(MovimientoDeudaBase):
    pass

class MovimientoDeudaResponse(MovimientoDeudaBase):
    id: int
    created_at: datetime
    cuenta_comitente: CuentaComitenteResponse
    serie: SerieResponse

    class Config:
        orm_mode = True
