import enum
import logging
from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    Enum,
    Numeric,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    DateTime,
    Boolean,
)
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, validates

from src.database import Base
from src.utils.dates import normalize_date

class PerfilTransaccional(Base):
    __tablename__ = "perfiles_transaccionales"
    __table_args__ = (UniqueConstraint("cuil_cliente", "periodo", name="uq_perfil_cliente_mes"),)
    
    id = Column(Integer, primary_key=True)
    cuil_cliente = Column(String(11), ForeignKey("clientes.cuil"), nullable=False)
    periodo = Column(Date, nullable=False)
    ingreso_bruto = Column(Numeric(14,2), nullable=False)
    ingreso_neto = Column(Numeric(14,2), nullable=False)
    asignacion_familiar = Column(Numeric(14,2), nullable=False)
    horas_extras = Column(Numeric(14,2), nullable=False)
    vacaciones = Column(Numeric(14,2), nullable=False)
    descuentos_voluntarios = Column(Numeric(14,2), nullable=False)
    otros = Column(Numeric(14,2), nullable=False)
    update_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @validates('periodo')
    def validate_periodo(self, key, value):
        if value:
            # Forzamos que siempre sea el día 1 del mes
            if isinstance(value, date):
                return value.replace(day=1)
            elif isinstance(value, str):
                # Si llega como string YYYY-MM-DD
                parsed_date = date.fromisoformat(value)
                return parsed_date.replace(day=1)
        return value

class TipoSueldo(enum.Enum):
    bruto = "BRUTO"
    neto = "NETO"

class ReglasPerfilTransaccional(Base):

    __tablename__ = "reglas_perfiles_transaccionales"
    
    id = Column(Integer, primary_key=True)
    id_socio_comercial = Column(Integer, ForeignKey("socios_comerciales.id"), nullable=False, unique=True)
    cupo = Column(Numeric(5,4), nullable=False)
    sueldo_tipo = Column(Enum(TipoSueldo), nullable=False)
    
    # Las siguientes variables se restan del sueldo elegido si la variables es verdadera
    asignacion_familiar = Column(Boolean, nullable=False, default=True)
    horas_extras = Column(Boolean, nullable=False, default=True)
    vacaciones = Column(Boolean, nullable=False, default=True)
    otros = Column(Boolean, nullable=False, default=True)

    # Si es True se descuenta antes de calcular el cupo, de lo contrario se descuenta del cupo
    descuentos_voluntarios = Column(Boolean, nullable=False, default=True)