from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from src.database.models.auth import TipoRolEnum

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class TokenData(BaseModel):
    email: Optional[str] = None
    rol: Optional[TipoRolEnum] = None

class UsuarioBase(BaseModel):
    email: EmailStr
    nombre_completo: str

class UsuarioCreate(UsuarioBase):
    password: str
    rol: TipoRolEnum

class UsuarioResponse(UsuarioBase):
    id: int
    is_active: bool
    rol_id: int

    class Config:
        from_attributes = True
