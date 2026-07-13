from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base

class DocumentoPapeleria(Base):
    """
    =============================================================================
    Model: DocumentoPapeleria
    =============================================================================
    """
    __tablename__ = "documentos_papeleria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    socio_id = Column(Integer, ForeignKey("socios_comerciales.id"), nullable=True)
    nombre_archivo = Column(String(255), nullable=False)
    ruta_archivo = Column(String(500), nullable=False)
    tipo_archivo = Column(String(50), nullable=True)
    orden = Column(Integer, default=0, nullable=False)
    fecha_subida = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    socio = relationship("SocioComercial")
    variables = relationship("DocumentoVariable", back_populates="documento", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DocumentoPapeleria(nombre_archivo='{self.nombre_archivo}', socio_id={self.socio_id})>"


class DocumentoVariable(Base):
    """
    =============================================================================
    Model: DocumentoVariable
    Mapea un placeholder de un documento Word a un campo del sistema.
    =============================================================================
    """
    __tablename__ = "documentos_variables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(Integer, ForeignKey("documentos_papeleria.id", ondelete="CASCADE"), nullable=False)
    placeholder = Column(String(100), nullable=False)
    system_field = Column(String(255), nullable=False)

    documento = relationship("DocumentoPapeleria", back_populates="variables")

    def __repr__(self):
        return f"<DocumentoVariable(placeholder='{self.placeholder}', system_field='{self.system_field}', documento_id={self.documento_id})>"
