from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date
from src.database.models.cheques.main import EstadoCheque, CalificacionEmisor, TipoOperacionCheque

class OperadorChequeBase(BaseModel):
    cuit: str = Field(max_length=11)
    razon_social: str = Field(max_length=150)
    calificacion: Optional[CalificacionEmisor] = None
    telefono: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=150)

class OperadorChequeCreate(OperadorChequeBase):
    pass

class OperadorChequeResponse(OperadorChequeBase):
    model_config = ConfigDict(from_attributes=True)

class ChequeBase(BaseModel):
    fecha_emision: date
    fecha_pago: date
    numero: str = Field(max_length=20)
    monto: float
    emisor_cuit: str = Field(max_length=11)
    banco_id: int
    imagen_path: Optional[str] = None

class ChequeCreate(ChequeBase):
    pass

class ChequeResponse(ChequeBase):
    id: int
    estado: EstadoCheque
    es_propio: bool = False
    emisor: OperadorChequeResponse
    beneficiario: OperadorChequeResponse

    model_config = ConfigDict(from_attributes=True)

class OperacionChequeBase(BaseModel):
    fecha_operacion: date
    operador_cuil: str = Field(max_length=11)
    tipo_operacion: TipoOperacionCheque
    tna_descuento: float
    dias_castigo: int = 0
    porcentaje_gastos: float = 0.028

class OperacionChequeCreate(OperacionChequeBase):
    pass

class OperacionChequeResponse(OperacionChequeBase):
    id: int
    cheque_id: int
    plazo_dias: int
    gastos: float
    intereses: float
    iva: float
    monto_descontado: float
    importe_neto_recibir: float
    tir_diaria: float
    tem: float
    tea: float
    
    model_config = ConfigDict(from_attributes=True)
