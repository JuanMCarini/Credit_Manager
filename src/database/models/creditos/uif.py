import enum
from datetime import date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    Numeric,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship, validates

from src.database import Base

class FactoRiesgo(Base):

    __tablename__ = "factores_riesgo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(50), unique=True, nullable=False)
    detalle = Column(String(255), nullable=False)
    peso = Column(Numeric(10, 4), nullable=False)

    multiplicadores = relationship(
        "MultiplicadoresRiesgo",
        back_populates="factor_riesgo",
        cascade="all, delete-orphan",
    )

class MultiplicadoresRiesgo(Base):
    __tablename__ = "multiplicadores_riesgo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(50), unique=True, nullable=False)
    id_riesgo = Column(Integer, ForeignKey("factores_riesgo.id"), nullable=False)
    detalle = Column(String(255), nullable=False)
    multiplicador = Column(Numeric(10, 2), nullable=False)
    variable = Column(Numeric(10, 2), nullable=True)

    factor_riesgo = relationship(
        "FactoRiesgo",
        back_populates="multiplicadores",
    )