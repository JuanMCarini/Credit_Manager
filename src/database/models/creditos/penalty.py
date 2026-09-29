import enum

from sqlalchemy import (
    Column,
    Enum,
    Numeric,
    ForeignKey,
    Integer,
    DateTime,
    UniqueConstraint)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.database import Base


class TipoInteres(enum.Enum):
    DIRECTO = "DIRECTO"
    ANUAL = "ANUAL"

class Penalty(Base):
    __tablename__ = "penalties"

    __table_args__ = (
        UniqueConstraint('socio_originador_id', 'plazo_hasta', name='uix_socio_plazo'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    socio_originador_id = Column(Integer, ForeignKey("socios_comerciales.id"),nullable=True)
    tna_c_iva = Column(Numeric(15, 6), nullable=False, default=0.0)
    plazo_hasta = Column(Integer, nullable=False, default=0)
    tipo_calculo = Column(Enum(TipoInteres, values_callable=lambda obj: [e.value for e in obj]), default=TipoInteres.DIRECTO.value, nullable=False)

    create_at = Column(DateTime(timezone=True), default=func.now())
    update_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    socio_originador = relationship("SocioComercial", back_populates="penalties")
