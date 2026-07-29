from pydantic import BaseModel, EmailStr, field_validator
import re
from typing import Optional
from src.database.models.auth import TipoRolEnum

def validate_strong_password(v: str) -> str:
    if len(v) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres")
    if not re.search(r"[A-Z]", v):
        raise ValueError("La contraseña debe contener al menos una letra mayúscula")
    if not re.search(r"[a-z]", v):
        raise ValueError("La contraseña debe contener al menos una letra minúscula")
    if not re.search(r"\d", v):
        raise ValueError("La contraseña debe contener al menos un número")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
        raise ValueError("La contraseña debe contener al menos un carácter especial")
    return v

class UsuarioBase(BaseModel):
    email: EmailStr
    nombre_completo: str
    is_active: bool = True

class UsuarioCreate(UsuarioBase):
    password: str
    rol_id: int
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        return validate_strong_password(v)

class UsuarioUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nombre_completo: Optional[str] = None
    rol_id: Optional[int] = None
    is_active: Optional[bool] = None

class UsuarioPasswordUpdate(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        return validate_strong_password(v)

class UsuarioMyPasswordUpdate(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        return validate_strong_password(v)

class RolResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None

    class Config:
        from_attributes = True

class UsuarioResponse(UsuarioBase):
    id: int
    rol: RolResponse

    class Config:
        from_attributes = True

from datetime import datetime

class RegistroAuditoriaResponse(BaseModel):
    id: int
    timestamp: datetime
    accion: str
    endpoint: str
    metodo: str
    direccion_ip: Optional[str] = None
    estado: str

    class Config:
        from_attributes = True
