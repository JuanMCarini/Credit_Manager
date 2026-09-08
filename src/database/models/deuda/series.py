from sqlalchemy import (
    Date,
    DateTime,
    Column,
    Integer,
    String,
    Numeric,
    Boolean,
    ForeignKey
)

from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import timedelta
from src.database import Base


class Serie(Base):
    __tablename__ = "series"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    fecha_suscripcion = Column(Date, nullable=False)
    tna = Column(Numeric(10, 2), nullable=False)
    plazo = Column(Integer, nullable=False)
    comision = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    movimientos = relationship("MovimientoDeuda", foreign_keys="[MovimientoDeuda.id_serie]", back_populates="serie", cascade="all, delete-orphan")

    @property
    def fecha_vencimiento(self):
        return self.fecha_suscripcion + timedelta(days=self.plazo)

class Comision(Base):
    __tablename__ = "comisiones_deuda"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(Date, nullable=False)
    id_socio_comercial = Column(ForeignKey('socios_comerciales.id'), nullable=False)
    porcentaje = Column(Numeric(10, 2), nullable=False)
    
    created_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    socio_comercial = relationship("SocioComercial", foreign_keys="[Comision.id_socio_comercial]")

class ComisionesSerie(Base):
    __tablename__ = "comisiones_series"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_serie = Column(ForeignKey('series.id'), nullable=False)
    id_comision = Column(ForeignKey('comisiones_deuda.id'), nullable=False)

    created_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    comision = relationship("Comision", foreign_keys="[ComisionesSerie.id_comision]")
    serie = relationship("Serie", foreign_keys="[ComisionesSerie.id_serie]")