from sqlalchemy import (
    Date,
    DateTime,
    Column,
    Integer,
    String,
    Numeric
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
    
    created_at = Column(DateTime, default=func.now())
    update_at = Column(DateTime, default=func.now(), onupdate=func.now())

    movimientos = relationship("MovimientoDeuda", foreign_keys="[MovimientoDeuda.id_serie]", back_populates="serie", cascade="all, delete-orphan")

    @property
    def fecha_vencimiento(self):
        return self.fecha_suscripcion + timedelta(days=self.plazo)

