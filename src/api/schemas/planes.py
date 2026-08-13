from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from src.database.models.finance.planes import SistemaMatematico, Denominador
from src.api.schemas.bancos import ConceptoResponse
from src.api.schemas.comprobantes import ProveedorResponse

class PlanBase(BaseModel):
    id_origen: str
    fecha: date
    proveedor_id: int
    concepto_id: Optional[int] = None
    capital: Decimal
    anticipo: Decimal
    vencimiento_anticipo: Optional[date] = None
    plazo: int
    valor_cuota: Decimal
    primer_vencimiento: date
    sistema: SistemaMatematico
    denominador: Denominador
    tna: Optional[Decimal] = Decimal('0.0')

class PlanCreate(PlanBase):
    pass

class PlanResponse(PlanBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    proveedor: Optional[ProveedorResponse] = None
    concepto: Optional[ConceptoResponse] = None

    model_config = ConfigDict(from_attributes=True)
