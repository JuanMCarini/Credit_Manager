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
    fecha_subida = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    socio = relationship("SocioComercial")

    def __repr__(self):
        return f"<DocumentoPapeleria(nombre_archivo='{self.nombre_archivo}', socio_id={self.socio_id})>"
