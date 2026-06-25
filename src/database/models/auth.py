from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from src.database.connection import Base

class TipoRolEnum(str, enum.Enum):
    ADMINISTRADOR = "Administrador"
    AUDITOR = "Auditor / Solo Lectura"
    OPERADOR_COBRANZAS = "Operador de Cobranzas"
    OFICIAL_CREDITO = "Oficial de Crédito"

class Rol(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(Enum(TipoRolEnum), unique=True, nullable=False)
    descripcion = Column(String(255), nullable=True)

    usuarios = relationship("Usuario", back_populates="rol")

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    nombre_completo = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    rol = relationship("Rol", back_populates="usuarios")

    logs_auditoria = relationship("RegistroAuditoria", back_populates="usuario")

class RegistroAuditoria(Base):
    __tablename__ = "registros_auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True) # Nullable para acciones sin login o fallidas
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    accion = Column(String(255), nullable=False)
    endpoint = Column(String(255), nullable=False)
    metodo = Column(String(10), nullable=False) # POST, PUT, DELETE
    direccion_ip = Column(String(50), nullable=True)
    estado = Column(String(50), nullable=False) # Exito, Fallo
    detalles = Column(JSON, nullable=True) # Para guardar payloads u otra info relevante

    usuario = relationship("Usuario", back_populates="logs_auditoria")
