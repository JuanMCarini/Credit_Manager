from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field
from src.database.models.creditos.clientes import SexoEnum, EstadoClienteEnum

class ReferidoCreate(BaseModel):
    nombre: str = Field(..., max_length=100)
    apellido: str = Field(..., max_length=100)
    telefono: Optional[str] = None
    email: Optional[str] = None

class ClienteCreate(BaseModel):
    cuil: str = Field(..., max_length=11, description="CUIL sin guiones (11 dígitos)")
    documento: str = Field(..., max_length=10)
    apellido: str = Field(..., max_length=100)
    nombre: str = Field(..., max_length=100)
    fecha_nacimiento: Optional[date] = None
    sexo: Optional[SexoEnum] = None
    estado_civil: Optional[str] = None
    nacionalidad: Optional[str] = None
    legajo: Optional[str] = None
    estado: Optional[EstadoClienteEnum] = EstadoClienteEnum.ACTIVO
    cbu: Optional[str] = None
    cuenta_bancaria: Optional[str] = None
    banco: Optional[str] = None
    calle: Optional[str] = None
    calle_nro: Optional[int] = None
    piso: Optional[str] = None
    depto: Optional[str] = None
    id_provincia: Optional[int] = None
    id_codigo_postal: Optional[str] = None
    localidad: Optional[str] = None
    telefono: Optional[str] = None
    telefono_2: Optional[str] = None
    mail: Optional[str] = None
    fecha_ingreso: Optional[date] = None
    remuneracion: float = 0.0
    empleador_id: Optional[int] = None
    cargo: Optional[str] = None
    pep: bool = False
    repet: bool = False
    referidos: List[ReferidoCreate] = []
