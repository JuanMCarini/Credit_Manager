from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import datetime


def validate_password_strength(v: str) -> str:
    if not v or len(v) < 10:
        raise ValueError("La contraseña debe tener al menos 10 caracteres.")
    if len(v) > 128:
        raise ValueError("La contraseña no puede superar los 128 caracteres.")
    if not any(c.isupper() for c in v):
        raise ValueError("La contraseña debe contener al menos una letra mayúscula.")
    if not any(c.islower() for c in v):
        raise ValueError("La contraseña debe contener al menos una letra minúscula.")
    if not any(c.isdigit() or not c.isalnum() for c in v):
        raise ValueError("La contraseña debe contener al menos un número o carácter especial.")
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
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UsuarioUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nombre_completo: Optional[str] = None
    rol_id: Optional[int] = None
    is_active: Optional[bool] = None


class UsuarioPasswordUpdate(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UsuarioMyPasswordUpdate(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def check_different_password(self) -> "UsuarioMyPasswordUpdate":
        if self.current_password == self.new_password:
            raise ValueError("La nueva contraseña no puede ser igual a la contraseña actual.")
        return self


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
