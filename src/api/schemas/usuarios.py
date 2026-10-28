from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from datetime import datetime


class UsuarioBase(BaseModel):
    email: EmailStr
    nombre_completo: str
    is_active: bool = True


class UsuarioCreate(UsuarioBase):
    password: str
    rol_id: int


class UsuarioUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nombre_completo: Optional[str] = None
    rol_id: Optional[int] = None
    is_active: Optional[bool] = None


class UsuarioPasswordUpdate(BaseModel):
    password: str


class UsuarioMyPasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class RolResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UsuarioResponse(UsuarioBase):
    id: int
    rol: RolResponse

    model_config = ConfigDict(from_attributes=True)


class RegistroAuditoriaResponse(BaseModel):
    id: int
    timestamp: datetime
    accion: str
    endpoint: str
    metodo: str
    direccion_ip: Optional[str] = None
    estado: str

    model_config = ConfigDict(from_attributes=True)
