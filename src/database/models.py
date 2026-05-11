"""
Module: models.py
Description: Defines the SQLAlchemy ORM models for the Credit_Manager application.
Author: Juan Martín Carini
Date: 2026-05-08
"""

import enum

from sqlalchemy import Boolean, Column, Date, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from .connection import Base


class SexoEnum(enum.Enum):
    MASCULINO = "M"
    FEMENINO = "F"
    OTRO = "O"


class Cliente(Base):
    """
    Represents a client in the credit portfolio management system.
    """

    __tablename__ = "clientes"

    # Primary Key & Identification
    cuil = Column(
        String(11), primary_key=True, unique=True, nullable=False
    )  # Unique worker identification number
    documento = Column(String(10), unique=True, nullable=False)

    # Personal Information
    apellido = Column(String(100), nullable=False)
    nombre = Column(String(100), nullable=False)
    fecha_nacimiento = Column(Date, nullable=True)
    sexo = Column(Enum(SexoEnum), nullable=True)

    # Address details
    calle = Column(String(150), nullable=True)
    calle_nro = Column(Integer, nullable=True)
    piso = Column(String(10), nullable=True)
    depto = Column(String(10), nullable=True)
    id_provincia = Column(Integer, nullable=True)
    id_codigo_postal = Column(String(20), nullable=True)
    localidad = Column(String(100), nullable=True)

    # Contact Information
    telefono = Column(String(50), nullable=True)
    telefono_2 = Column(String(50), nullable=True)
    mail = Column(String(150), nullable=True)

    # Financial Data
    remuneracion = Column(Float, default=0.0)  # Monthly income for credit scoring

    # Relationships
    creditos = relationship("Credito", back_populates="cliente")

    def __repr__(self):
        return f"<Cliente(cuil='{self.cuil}', apellido='{self.apellido}', nombre='{self.nombre}')>"


class SocioComercial(Base):
    """
    Represents business partners such as banks, investment funds, or trusts.
    """

    __tablename__ = "socios_comerciales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    razon_social = Column(String(150), unique=True, nullable=False)
    cuit = Column(String(11), unique=True, nullable=False)  # Tax ID without dashes
    domicilio_legal = Column(String(200), nullable=True)
    contacto_nombre = Column(String(100), nullable=True)
    mail = Column(String(150), nullable=True)
    telefono = Column(String(50), nullable=True)
    dia_corte = Column(Integer, default=28)

    # Relationships
    carteras = relationship("Cartera", back_populates="socio")
    creditos_originados = relationship("Credito", back_populates="socio_originador")

    def __repr__(self):
        return (
            f"<SocioComercial(razon_social='{self.razon_social}', cuit='{self.cuit}')>"
        )


class TipoOperacionCartera(enum.Enum):
    """
    Defines the type of wholesale portfolio transaction.
    Origination is excluded as it is a 1-to-1 retail process.
    """

    COMPRA = "COMPRA"
    VENTA = "VENTA"
    RECOMPRA = "RECOMPRA"


class Cartera(Base):
    """
    Represents a purchased portfolio or fund.
    """

    __tablename__ = "carteras"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), unique=True, nullable=False)
    fecha_compra = Column(Date, nullable=False)

    # New ForeignKey linking to SocioComercial
    socio_id = Column(Integer, ForeignKey("socios_comerciales.id"), nullable=False)

    # Financial and Tax Flags
    iva = Column(Boolean, default=False)  # True if interest includes VAT (IVA)
    recurso = Column(Boolean, default=True)  # True if the sale is 'Con Recurso'

    # Valuation parameters
    tna_descuento = Column(
        Float, nullable=False
    )  # Annual nominal discount rate for purchase valuation

    # Field to define the nature of this batch
    tipo_operacion = Column(
        Enum(TipoOperacionCartera), nullable=False, default=TipoOperacionCartera.COMPRA
    )

    # Relationships
    creditos_incluidos = relationship("Credito", back_populates="cartera")
    operaciones = relationship("OperacionCartera", back_populates="cartera")
    socio = relationship("SocioComercial", back_populates="carteras")

    def __repr__(self):
        return f"<Cartera(nombre='{self.nombre}', socio_id={self.socio_id}, tipo={self.tipo_operacion}, fecha_compra={self.fecha_compra}, tna_desc={self.tna_descuento})>"


class OrigenCredito(enum.Enum):
    ORIGINADO = "ORIGINADO"
    COMPRADO = "COMPRADO"


class EstadoCredito(enum.Enum):
    """
    Possible states for a credit loan in the system.
    """

    APROBADO = "APROBADO"  # Credito aprobado pero no liquidado
    RECHAZADO = "RECHAZADO"  # Credito rechazado
    ACTIVO = "ACTIVO"  # Current loan with no arrears
    CANCELADO = "CANCELADO"  # Fully paid loan
    MORA = "MORA"  # Loan with overdue payments
    JUDICIAL = "JUDICIAL"  # Loan in legal recovery process


class Credito(Base):
    """
    Core loan entity. Each loan can pass through multiple portfolios over time.
    """

    __tablename__ = "creditos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_cuil = Column(String(11), ForeignKey("clientes.cuil"), nullable=False)

    # ESCENARIO 1: Socio Comercial que originó el crédito (Mutual, Sindicato, etc.)
    # Si es generación propia, queda nullable=True.
    socio_originador_id = Column(
        Integer, ForeignKey("socios_comerciales.id"), nullable=True
    )

    # ESCENARIO 2: Si el crédito pertenece a una compra de cartera.
    cartera_id = Column(Integer, ForeignKey("carteras.id"), nullable=True)

    capital = Column(Float, nullable=False)
    tna_c_iva = Column(Float, nullable=False)
    plazo = Column(Integer, nullable=False)
    fecha_emision = Column(Date, nullable=False)

    estado = Column(Enum(EstadoCredito), default=EstadoCredito.APROBADO)

    dia_vencimiento = Column(Integer, default=28, nullable=False)

    @hybrid_property
    def origen(self):
        """
        Determina el origen de forma dinámica.
        """
        if self.cartera_id is not None:
            return OrigenCredito.COMPRADO
        return OrigenCredito.ORIGINADO

    # Relationships
    cliente = relationship("Cliente", back_populates="creditos")
    cuotas = relationship(
        "Cuota", back_populates="credito", cascade="all, delete-orphan"
    )
    socio_originador = relationship(
        "SocioComercial", back_populates="creditos_originados"
    )
    cartera = relationship("Cartera", back_populates="creditos_incluidos")

    def __repr__(self):
        return (
            f"<Credito(id={self.id}, cliente='{self.cliente_cuil}', "
            f"monto={self.capital}, origen={self.origen.value})>"
        )


class Cuota(Base):
    """
    Financial plan for a credit. Payment data is now handled by the Cobranza table.
    """

    __tablename__ = "cuotas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    credito_id = Column(Integer, ForeignKey("creditos.id"), nullable=False)
    numero_cuota = Column(Integer, nullable=False)

    fecha_vencimiento = Column(Date, nullable=False)
    capital = Column(Float, nullable=False)
    interes = Column(Float, nullable=False)
    iva_interes = Column(Float, default=0.0)

    # Relationships
    credito = relationship("Credito", back_populates="cuotas")
    movimientos_cartera = relationship("OperacionCartera", back_populates="cuota")
    cobranzas = relationship("Cobranza", back_populates="cuota")

    def __repr__(self):
        return f"<Cuota(credito_id={self.credito_id}, nro={self.numero_cuota})>"


class OperacionCartera(Base):
    """
    Mapping table: Assigns a specific Installment (Cuota) to a Cartera batch.
    Allows granular tracking for partial repurchases.
    """

    __tablename__ = "operaciones_cartera"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Direct link to the individual installment instead of the whole credit
    cuota_id = Column(Integer, ForeignKey("cuotas.id"), nullable=False)
    cartera_id = Column(Integer, ForeignKey("carteras.id"), nullable=False)

    fecha_registro = Column(Date, nullable=False)

    # Relationships
    cuota = relationship("Cuota", back_populates="movimientos_cartera")
    cartera = relationship("Cartera", back_populates="operaciones")


class TipoCobranzaEnum(enum.Enum):
    """
    Defines the financial nature of the collection event.
    """

    COMUN = "COMUN"
    CA = "CANCELACION ANTICIPADA"
    BCA = "BONIFICACION POR CANCELACION ANTICIPADA"


class Cobranza(Base):
    """
    Records actual payment events or bonuses linked to specific installments.
    """

    __tablename__ = "cobranzas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuota_id = Column(Integer, ForeignKey("cuotas.id"), nullable=False)

    # Updated to use the Enum directly
    tipo_cobranza = Column(
        Enum(TipoCobranzaEnum), nullable=False, default=TipoCobranzaEnum.COMUN
    )

    capital = Column(Float, nullable=False)
    interes = Column(Float, nullable=False)
    iva = Column(Float, nullable=False)
    fecha = Column(Date, nullable=False)

    # Relationships
    cuota = relationship("Cuota", back_populates="cobranzas")

    def __repr__(self):
        # Updated to reflect the new financial breakdown fields
        total = self.capital + self.interes + self.iva
        return f"<Cobranza(cuota_id={self.cuota_id}, tipo={self.tipo_cobranza}, total={total})>"
