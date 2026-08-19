from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from src.database import Base

class RepetPerson(Base):
    """
    Cache local de personas físicas reportadas en el RePET.
    """
    __tablename__ = "repet_personas"

    id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(255), index=True, nullable=False)
    nombre_normalizado = Column(String(255), index=True, nullable=False)
    documento = Column(String(50), nullable=True, index=True)
    json_data = Column(Text, nullable=True) # Guarda info adicional para mostrar detalles
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RepetEntity(Base):
    """
    Cache local de entidades/empresas reportadas en el RePET.
    """
    __tablename__ = "repet_entidades"

    id = Column(Integer, primary_key=True, index=True)
    razon_social = Column(String(255), index=True, nullable=False)
    razon_social_normalizada = Column(String(255), index=True, nullable=False)
    cuit = Column(String(50), nullable=True, index=True)
    json_data = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RepetAuditLog(Base):
    """
    Registro de auditoría (Pista de Auditoría) exigido por la UIF
    para demostrar debida diligencia en búsquedas en las listas.
    """
    __tablename__ = "repet_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    searched_name = Column(String(255), nullable=False)
    is_match = Column(Boolean, nullable=False, default=False)
    match_score = Column(Float, nullable=True)
    matched_record_id = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)  # Usuario interno que ejecutó la acción
