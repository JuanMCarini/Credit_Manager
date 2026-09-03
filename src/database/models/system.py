from sqlalchemy import Column, String, Boolean
from src.database.connection import Base

class ModuloSistema(Base):
    __tablename__ = "modulos_sistema"

    codigo = Column(String(50), primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
