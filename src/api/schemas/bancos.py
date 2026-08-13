from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, date
from src.database.models.finance.bancos import CategoriaMovimiento, TipoMoneda

# =======================
# Banco Schemas
# =======================
class BancoBase(BaseModel):
    nombre_banco: str
    parser_type: Optional[str] = None

class BancoCreate(BancoBase):
    pass

class BancoUpdate(BancoBase):
    pass

class BancoResponse(BancoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# =======================
# Cuenta Schemas
# =======================
class CuentaBase(BaseModel):
    nombre: str
    banco_id: int
    nro: str
    cbu: str
    alias: str
    tipo_cuenta: str
    moneda: TipoMoneda

class CuentaCreate(CuentaBase):
    pass

class CuentaUpdate(BaseModel):
    nombre: Optional[str] = None
    banco_id: Optional[int] = None
    nro: Optional[str] = None
    cbu: Optional[str] = None
    alias: Optional[str] = None
    tipo_cuenta: Optional[str] = None
    moneda: Optional[TipoMoneda] = None

class CuentaResponse(CuentaBase):
    id: int
    created_at: datetime
    updated_at: datetime
    banco: Optional[BancoResponse] = None
    saldo: Optional[float] = None
    saldo_fci: Optional[float] = None
    saldo_plazo_fijo: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

# =======================
# Clasificacion Schemas
# =======================
class ClasificacionBase(BaseModel):
    name: str
    descripcion: Optional[str] = None

class ClasificacionCreate(ClasificacionBase):
    pass

class ClasificacionUpdate(BaseModel):
    name: Optional[str] = None
    descripcion: Optional[str] = None

class ClasificacionResponse(ClasificacionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# =======================
# Concepto Schemas
# =======================
class ConceptoBase(BaseModel):
    name: str
    tipo_movimiento: CategoriaMovimiento
    descripcion: Optional[str] = None
    clasificacion_id: Optional[int] = None
    is_system: bool = False

class ConceptoCreate(ConceptoBase):
    pass

class ConceptoUpdate(BaseModel):
    name: Optional[str] = None
    tipo_movimiento: Optional[CategoriaMovimiento] = None
    descripcion: Optional[str] = None
    clasificacion_id: Optional[int] = None

class ConceptoResponse(ConceptoBase):
    id: int
    created_at: datetime
    updated_at: datetime
    clasificacion: Optional[ClasificacionResponse] = None
    model_config = ConfigDict(from_attributes=True)

# =======================
# Movimiento Schemas
# =======================
class MovimientoBase(BaseModel):
    cuenta_id: int
    fecha: date
    nro_comprobante: Optional[str] = None
    monto: float
    concepto_id: Optional[int] = None
    descripcion: Optional[str] = None

class MovimientoCreate(MovimientoBase):
    pass

class MovimientoUpdate(BaseModel):
    cuenta_id: Optional[int] = None
    fecha: Optional[date] = None
    nro_comprobante: Optional[str] = None
    monto: Optional[float] = None
    concepto_id: Optional[int] = None
    descripcion: Optional[str] = None

class MovimientoBulkConceptoUpdate(BaseModel):
    movimiento_ids: List[int]
    concepto_id: int

class MovimientoResponse(MovimientoBase):
    id: int
    created_at: datetime
    updated_at: datetime
    concepto: Optional[ConceptoResponse] = None
    cuenta: Optional[CuentaResponse] = None
    monto_asignado: Optional[float] = 0.0
    saldo_disponible: Optional[float] = 0.0

    model_config = ConfigDict(from_attributes=True)
