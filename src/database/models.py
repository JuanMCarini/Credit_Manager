"""
Module: models.py
Description: Defines the SQLAlchemy ORM models for the Credit_Manager application.
Author: Juan Martín Carini
Date: 2026-05-08
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Session, relationship

from src.database import Base, SessionLocal
from src.utils.dates import normalize_date


class SexoEnum(enum.Enum):
    MASCULINO = "M"
    FEMENINO = "F"
    OTRO = "O"


class Empleador(Base):
    """
    Represents the employer or withholding agent (Agente de Retención)
    for payroll deduction loans (Código de Descuento).
    """

    __tablename__ = "empleadores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuit = Column(String(11), unique=True, nullable=True)
    razon_social = Column(String(150), nullable=False)

    # Relationships
    empleados = relationship("Cliente", back_populates="empleador")

    def __repr__(self):
        return f"<Empleador(cuit='{self.cuit}', razon_social='{self.razon_social}')>"


class Provincia(Base):
    """
    Represents a geographical province or state.
    """

    __tablename__ = "provincias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), unique=True, nullable=False)

    # Relationships
    clientes = relationship("Cliente", back_populates="provincia")

    def __repr__(self):
        return f"<Provincia(id={self.id}, nombre='{self.nombre}')>"


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

    # Foreign Keys linking to geographical tables
    id_provincia = Column(Integer, ForeignKey("provincias.id"), nullable=True)
    id_codigo_postal = Column(String(10), nullable=True)
    localidad = Column(String(100), nullable=True)

    # Contact Information
    telefono = Column(String(50), nullable=True)
    telefono_2 = Column(String(50), nullable=True)
    mail = Column(String(150), nullable=True)

    # Financial Data
    remuneracion = Column(Float, default=0.0)  # Monthly income for credit scoring

    # New ForeignKey linking to Empleador
    empleador_id = Column(Integer, ForeignKey("empleadores.id"), nullable=True)

    # Relationships
    creditos = relationship("Credito", back_populates="cliente")
    provincia = relationship("Provincia", back_populates="clientes")
    empleador = relationship("Empleador", back_populates="empleados")

    def __repr__(self):
        return f"<Cliente(cuil='{self.cuil}', apellido='{self.apellido}', nombre='{self.nombre}')>"


class SocioComercial(Base):
    """
    =============================================================================
    Model: SocioComercial
    Description: Represents business partners such as banks, investment funds,
                 or trusts (e.g., FCI Valiant, Fondosur).
    =============================================================================
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
    relaciones = relationship(
        "Relacion", back_populates="socio", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<SocioComercial(razon_social='{self.razon_social}', cuit='{self.cuit}')>"
        )

    @classmethod
    def create_socio(
        cls, razon_social: str, cuit: str, db: Session | None = None, **kwargs
    ) -> "SocioComercial":
        """
        =============================================================================
        Method: create_socio
        Description: Instantiates and persists a new commercial partner in the
                     database. Validates that the CUIT and Company Name do not
                     already exist to prevent unique constraint violations.
        Parameters:
            db (Session): Active SQLAlchemy database session.
            razon_social (str): The legal name of the company.
            cuit (str): The 11-digit Tax ID (without dashes).
            **kwargs: Additional optional attributes (mail, telefono, dia_corte, etc.).
        Returns:
            SocioComercial: The newly created business partner instance.
        Raises:
            ValueError: If a partner with the same CUIT or Razón Social already exists.
        =============================================================================
        """
        db = db or SessionLocal()
        cuit_str = str(cuit).strip()
        rs_str = str(razon_social).strip()

        # 1. Duplicate validation before insertion
        existe = (
            db.query(cls)
            .filter((cls.cuit == cuit_str) | (cls.razon_social == rs_str))
            .first()
        )

        if existe:
            raise ValueError(
                f"A Socio Comercial is already registered with CUIT '{cuit_str}' "
                f"or Razón Social '{rs_str}'."
            )

        try:
            # 2. Dynamic creation by unpacking additional attributes
            nuevo_socio = cls(razon_social=rs_str, cuit=cuit_str, **kwargs)
            db.add(nuevo_socio)
            db.commit()
            db.refresh(nuevo_socio)
            return nuevo_socio

        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Failed to register the new socio comercial: {e}")

    @classmethod
    def update_socio(
        cls, socio_id: int, db: Session | None = None, **kwargs
    ) -> "SocioComercial":
        """
        =============================================================================
        Method: update_socio
        Description: Modifies specific attributes of an existing commercial partner
                     based on its primary key. Ignores invalid attributes and
                     protects the primary key from being overwritten.
        Parameters:
            db (Session): Active SQLAlchemy database session.
            socio_id (int): Primary key of the commercial partner to modify.
            **kwargs: Key-value pairs of the attributes to update.
        Returns:
            SocioComercial: The updated business partner instance.
        Raises:
            ValueError: If the socio_id is not found in the database.
            RuntimeError: If the database transaction fails to commit.
        =============================================================================
        """
        db = db or SessionLocal()
        # 1. Retrieve the target socio
        socio = db.query(cls).filter_by(id=socio_id).first()
        if not socio:
            raise ValueError(f"No Socio Comercial was found with ID {socio_id}.")

        try:
            # 2. Iterate over arguments and update only valid attributes
            for key, value in kwargs.items():
                # We protect the ID so it cannot be altered accidentally
                if hasattr(socio, key) and key != "id":
                    setattr(socio, key, value)

            db.commit()
            db.refresh(socio)
            return socio

        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Failed to update socio comercial data: {e}")


class AnticiposSinAplicar(Base):
    __tablename__ = "anticipos_socios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(Date, nullable=False)
    socio_id = Column(Integer, ForeignKey("socios_comerciales.id"), nullable=False)
    monto = Column(Float, nullable=False)


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
    liquidaciones = relationship("LiquidacionCuotaCedida", back_populates="cartera")

    def __repr__(self):
        return f"<Cartera(nombre='{self.nombre}', socio_id={self.socio_id}, tipo={self.tipo_operacion}, fecha_compra={self.fecha_compra}, tna_desc={self.tna_descuento})>"


class OrigenCredito(enum.Enum):
    ORIGINADO = "ORIGINADO"
    COMPRADO = "COMPRADO"


class EstadoCredito(enum.Enum):
    """
    Possible states for a credit loan in the system.
    """

    APROBADO = "APROBADO"  # Credit approved but not disbursed
    RECHAZADO = "RECHAZADO"  # Credit rejected
    ACTIVO = "ACTIVO"  # Current loan with no arrears
    CANCELADO = "CANCELADO"  # Fully paid loan
    MOROSO = "MOROSO"  # Loan with overdue payments
    JUDICIAL = "JUDICIAL"  # Loan in legal recovery process


class TipoCredito(enum.Enum):
    """
    =============================================================================
    Enum: TipoCredito
    Description: Defines the allowed amortization systems and structural credit
                 types within the system, including isolated penalty debts.
    =============================================================================
    """

    FRANCES = "SISTEMA FRANCES"
    ALEMAN = "SISTEMA ALEMAN"
    PENALTY = "PENALTY"


class Credito(Base):
    """
    Core loan entity. Each loan can pass through multiple portfolios over time.
    """

    __tablename__ = "creditos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_externo = Column(String(50), index=True, nullable=True)
    cliente_cuil = Column(String(11), ForeignKey("clientes.cuil"), nullable=False)

    # SCENARIO 1: Socio Comercial that originated the credit (Mutual, Union, etc.)
    # If it's internally generated, it remains nullable=True.
    socio_originador_id = Column(
        Integer, ForeignKey("socios_comerciales.id"), nullable=True
    )

    # SCENARIO 2: If the credit belongs to a portfolio purchase.
    cartera_id = Column(Integer, ForeignKey("carteras.id"), nullable=True)

    capital = Column(Float, nullable=False)
    tna_c_iva = Column(Float, nullable=False)
    plazo = Column(Integer, nullable=False)
    fecha_emision = Column(Date, nullable=False)

    estado = Column(Enum(EstadoCredito), default=EstadoCredito.APROBADO)

    tipo_credito = Column(
        Enum(TipoCredito), nullable=False, default=TipoCredito.FRANCES
    )

    dia_vencimiento = Column(Integer, default=28, nullable=False)

    @hybrid_property
    def origen(self):
        """
        Dynamically determines the origin.
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

    def actualizar_estado(self) -> str:
        """
        =============================================================================
        Method: actualizar_estado
        Description: Evaluates the statuses of all associated installments to determine
                     the global credit status. Respects manual overrides for
                     RECHAZADO and JUDICIAL states, printing a warning if an automatic
                     update is attempted on them. Automates the flow for APROBADO,
                     ACTIVO, MORA, and CANCELADO.
        Returns:
            str: The newly assigned global status of the credit.
        =============================================================================
        """
        import logging  # Importado para la advertencia

        from src.database.models import EstadoCredito, EstadoCuota

        # 1. Guard Clause: Protect immutable manual states
        estados_manuales = [EstadoCredito.RECHAZADO, EstadoCredito.JUDICIAL]

        # Safe parsing of current state
        estado_actual = (
            self.estado
            if isinstance(self.estado, EstadoCredito)
            else EstadoCredito(self.estado)
        )

        if estado_actual in estados_manuales:
            # Print the warning. In production, it is ideal to use logging.warning()
            mensaje_alerta = f"⚠️ Warning: Automatic update attempt skipped for Credito ID {self.id}. State blocked: {estado_actual.value}."
            print(mensaje_alerta)
            logging.warning(mensaje_alerta)

            return estado_actual.value

        # 2. Filter the quotas that actively belong to the portfolio
        cuotas_activas = [c for c in self.cuotas if c.estado != EstadoCuota.NO_COMPRADA]

        if not cuotas_activas:
            # If all were sold/assigned, the local credit is considered cancelled
            self.estado = EstadoCredito.CANCELADO
            return self.estado.value

        # 3. Hierarchy evaluation for dynamic cycle
        # Rule 1: If any quota is overdue, the entire credit goes into arrears
        if any(c.estado == EstadoCuota.MOROSA for c in cuotas_activas):
            self.estado = EstadoCredito.MOROSO

        # Rule 2: If all are paid, the credit finished successfully
        elif all(c.estado == EstadoCuota.CANCELADA for c in cuotas_activas):
            self.estado = EstadoCredito.CANCELADO

        # Rule 3: If there are pending quotas but none overdue (also applies to APROBADO)
        else:
            self.estado = EstadoCredito.ACTIVO

        return (
            self.estado.value if isinstance(self.estado, EstadoCredito) else self.estado
        )

    @property
    def carteras_de_venta(self) -> list:
        """
        =============================================================================
        Property: carteras_de_venta
        Description: Dynamically aggregates all the unique sales portfolios (Carteras)
                     to which any of this credit's installments have been sold.
        =============================================================================
        """
        from src.database.models import TipoOperacionCartera

        ventas = set()
        for cuota in self.cuotas:
            for operacion in cuota.movimientos_cartera:
                if (
                    operacion.cartera
                    and operacion.cartera.tipo_operacion == TipoOperacionCartera.VENTA
                ):
                    ventas.add(operacion.cartera)
        return list(ventas)

    def __repr__(self):
        return (
            f"<Credito(id={self.id}, cliente='{self.cliente_cuil}', "
            f"monto={self.capital}, origen={self.origen.value})>"
        )


class EstadoCuota(enum.Enum):
    """
    =============================================================================
    Enum: EstadoCuota
    Description: Specifies the current state of an individual loan installment
                 within the core system, reflecting its financial lifecycle and
                 eligibility for assignment or accounting tracking.
    =============================================================================
    """

    NO_COMPRADA = "NO COMPRADA"  # Installments from own originated portfolios or not corresponding to a purchased cash flow
    PENDIENTE = "PENDIENTE"  # Active installment within the legal payment term and not yet expired
    MOROSA = "MOROSA"  # Installment whose due date has expired without registering the corresponding payment
    CANCELADA = "CANCELADA"  # Installment that has been fully settled and paid by the client or third party


class EstadoCuotaCedida(enum.Enum):
    """
    =============================================================================
    Enum: EstadoCuotaCedida
    Description: Specifies the assignment and collection status of a specific
                 installment when it is involved in a portfolio sale or
                 transfer to a third-party financial entity.
    =============================================================================
    """

    NO_VENDIDA = "NO VENDIDA"  # Available for sale (Internally originated)
    NO_COMPRADA = (
        "NO COMPRADA"  # Status for acquired installments that are not replicated
    )
    PENDIENTE = "PENDIENTE"  # Assigned to the buyer but not yet liquidated/collected
    MOROSA = "MOROSA"  # Assigned installment that incurred late default
    CANCELADA = "CANCELADA"  # Assigned installment that was already fully paid


class Cuota(Base):
    """
    Financial plan for a credit. Payment data is now handled by the Cobranza table.
    """

    __tablename__ = "cuotas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    credito_id = Column(Integer, ForeignKey("creditos.id"), nullable=False)
    nro_cuota = Column(Integer, nullable=False)

    fecha_vencimiento = Column(Date, nullable=False)
    capital = Column(Float, nullable=False)
    interes = Column(Float, nullable=False)
    iva = Column(Float, default=0.0)

    estado = Column(Enum(EstadoCuota), nullable=False, default=EstadoCuota.PENDIENTE)
    estado_cesion = Column(
        Enum(EstadoCuotaCedida, name="estadocuotacedida"),
        nullable=False,
        default=EstadoCuotaCedida.NO_VENDIDA,
    )

    # Relationships
    credito = relationship("Credito", back_populates="cuotas")
    movimientos_cartera = relationship("OperacionCartera", back_populates="cuota")
    cobranzas = relationship("Cobranza", back_populates="cuota")
    liquidaciones = relationship("LiquidacionCuotaCedida", back_populates="cuota")

    def actualizar_estado(self, fecha_evaluacion: str | datetime) -> str:
        """
        =============================================================================
        Method: actualizar_estado
        Description: Evaluates the total paid amounts against the expected totals
                     and the current date to determine the accurate status of the
                     installment. Bypasses execution if the debt was sold.
        Parameters:
            fecha_evaluacion (date): The reference date to check for delinquency.
        Returns:
            str: The updated status of the installment.
        =============================================================================
        """
        fecha_evaluacion = normalize_date(fecha_evaluacion)
        # 1. Guard clause: If the installment was never purchased, we don't touch it
        if self.estado == EstadoCuota.NO_COMPRADA:
            return self.estado.value

        # 2. Financial math with rounding to avoid floating point errors
        total_esperado = round(self.capital + self.interes + self.iva, 2)

        # We sum everything that came in through collections associated with this installment
        total_cobrado = round(sum(
            round(c.capital + c.interes + c.iva, 2) for c in self.cobranzas
        ), 2)

        # 3. State transition logic
        if total_cobrado >= total_esperado:
            self.estado = EstadoCuota.CANCELADA

        elif fecha_evaluacion > normalize_date(self.fecha_vencimiento):
            self.estado = EstadoCuota.MOROSA

        else:
            self.estado = EstadoCuota.PENDIENTE

        return self.estado.value

    def actualizar_estado_cedido(self, fecha_evaluacion: str | datetime) -> str:
        """
        =============================================================================
        Method: actualizar_estado
        Description: Evaluates the total paid amounts against the expected totals
                     and the current date to determine the accurate status of the
                     installment. Bypasses execution if the debt was sold.
        Parameters:
            fecha_evaluacion (date): The reference date to check for delinquency.
        Returns:
            str: The updated status of the installment.
        =============================================================================
        """
        fecha_evaluacion = normalize_date(fecha_evaluacion)
        # 1. Guard clause: If the installment was never purchased, we don't touch it
        if self.estado_cesion in [
            EstadoCuotaCedida.NO_COMPRADA,
            EstadoCuotaCedida.NO_VENDIDA,
        ]:
            return self.estado_cesion.value

        # 2. Financial math with rounding to avoid floating point errors
        total_esperado = round(self.capital + self.interes + self.iva, 2)

        # We sum everything that came in through collections associated with this installment
        total_cobrado = round(sum(
            round(c.capital + c.interes + c.iva, 2) for c in self.liquidaciones
        ), 2)

        # 3. State transition logic
        if total_cobrado >= total_esperado:
            self.estado_cesion = EstadoCuotaCedida.CANCELADA

        elif fecha_evaluacion > normalize_date(self.fecha_vencimiento):
            self.estado_cesion = EstadoCuotaCedida.MOROSA

        else:
            self.estado_cesion = EstadoCuotaCedida.PENDIENTE

        return self.estado_cesion.value

    def __repr__(self):
        return f"<Cuota(credito_id={self.credito_id}, nro={self.nro_cuota})>"


class OperacionCartera(Base):
    """
    Mapping table: Assigns a specific Installment (Cuota) to a Cartera batch.
    Allows granular tracking for partial repurchases.
    """

    __tablename__ = "operaciones_cartera"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Direct link to the individual installment instead of the whole credit
    cuota_id = Column(Integer, ForeignKey("cuotas.id"), nullable=False)
    cartera_id = Column(Integer, ForeignKey("carteras.id"), nullable=True)
    cuota_comercializada = Column(Boolean, default=False)
    fecha_registro = Column(Date, nullable=False)

    # Relationships
    cuota = relationship("Cuota", back_populates="movimientos_cartera")
    cartera = relationship("Cartera", back_populates="operaciones")


class TipoCobranzaEnum(enum.Enum):
    """
    Defines the financial nature of the collection event.
    """

    COMUN = "COMUN"
    ANTICIPO = "ANTICIPO"
    CA = "CANCELACION ANTICIPADA"
    BCA = "BONIFICACION POR CANCELACION ANTICIPADA"
    CNC = "CUOTA NO COMPRADA"
    PENALTY = "PENALTY"
    RECURSO = "RECURSO"
    AJUSTE = "AJUSTE"


class Cobranza(Base):
    """
    Records actual payment events or bonuses linked to specific installments.
    """

    __tablename__ = "cobranzas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuota_id = Column(Integer, ForeignKey("cuotas.id"), nullable=False)

    # Updated to use the Enum directly
    tipo_cobranza = Column(
        Enum(TipoCobranzaEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=TipoCobranzaEnum.COMUN.value,
    )

    capital = Column(Float, nullable=False)
    interes = Column(Float, nullable=False)
    iva = Column(Float, nullable=False)
    fecha = Column(Date, nullable=False)

    # Relationships
    cuota = relationship("Cuota", back_populates="cobranzas")

    @property
    def importe_total(self) -> float:
        """
        Calculates the total collected amount for this record.
        """
        return self.capital + self.interes + self.iva

    def __repr__(self):
        # Updated to reflect the new financial breakdown fields
        return f"<Cobranza(cuota_id={self.cuota_id}, tipo={self.tipo_cobranza}, total={self.importe_total})>"


class TipoLiquidacionEnum(enum.Enum):
    """
    Defines the financial nature of the payout/liquidation event to the portfolio buyer.
    """

    PENDIENTE = "PENDIENTE"
    NORMAL = "NORMAL"
    RECURSO = "RECURSO"
    CA = "CANCELACION ANTICIPADA"
    BCA = "BONIFICACION POR CANCELACION ANTICIPADA"
    IP = "INTERESES PERDIDOS"


class LiquidacionCuotaCedida(Base):
    """
    Records payments (rendiciones/liquidaciones) made to the partner that purchased the portfolio.
    Acts as a mirror to Cobranza but for liabilities.
    """

    __tablename__ = "liquidaciones_cuotas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuota_id = Column(Integer, ForeignKey("cuotas.id"), nullable=False)
    cartera_id = Column(Integer, ForeignKey("carteras.id"), nullable=False)

    tipo_liquidacion = Column(
        Enum(TipoLiquidacionEnum, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=TipoLiquidacionEnum.NORMAL.value,
    )

    capital = Column(Float, nullable=False, default=0.0)
    interes = Column(Float, nullable=False, default=0.0)
    iva = Column(Float, nullable=False, default=0.0)
    fecha_pago = Column(Date, nullable=False)

    # Relationships
    cuota = relationship("Cuota", back_populates="liquidaciones")
    cartera = relationship("Cartera", back_populates="liquidaciones")

    @property
    def importe_total(self) -> float:
        """
        Calculates the total rendered amount for this record.
        """
        return self.capital + self.interes + self.iva

    def __repr__(self):
        return f"<Liquidacion(cuota_id={self.cuota_id}, tipo={self.tipo_liquidacion}, total={self.importe_total})>"


class Relacion(Base):
    """
    =============================================================================
    Model: Relacion
    Description: Represents a cross-reference and data-homologation table. Stores
                 relational mappings between native primary keys and foreign
                 identifiers originating from external partner systems (e.g.,
                 Province IDs, Employer codes).
    =============================================================================
    """

    __tablename__ = "relaciones"

    # 1. Unique and auto-incremental primary key of the mapping record
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 2. Physical foreign key pointing to the commercial partner owning the external system
    socio_id = Column(Integer, ForeignKey("socios_comerciales.id"), nullable=False)

    # 3. Identifier of the mapped entity or table (e.g. "provincias", "empleadores")
    tabla = Column(String, nullable=False)

    # 4. Native or local ID of our relational system
    id_local = Column(Integer, nullable=False)

    # 5. ID or code assigned in the file/system of the external commercial partner
    id_foraneo = Column(
        String, nullable=False
    )  # String is used in case codes come with letters or leading zeros

    # 6. ORM relational attribute for object navigation
    socio = relationship("SocioComercial", back_populates="relaciones")

    # 7. Table-level integrity constraints
    __table_args__ = (
        # Prevents a single partner from having duplicated mapping of a local or foreign id in the same entity
        UniqueConstraint("socio_id", "tabla", "id_local", name="uq_socio_tabla_local"),
        UniqueConstraint(
            "socio_id", "tabla", "id_foraneo", name="uq_socio_tabla_foraneo"
        ),
    )

    @classmethod
    def add_single_mapping(
        cls,
        socio_id: int,
        tabla: str,
        id_local: int,
        id_foraneo: str | int,
        db: Session = SessionLocal(),
    ) -> "Relacion":
        """
        =============================================================================
        Method: add_single_mapping
        Description: Inserts a single relational mapping into the database.
                     Validates prior existence to prevent unique constraint violations
                     before attempting persistence.
        Parameters:
            socio_id (int): Primary key of the commercial partner.
            tabla (str): Name of the logical table being mapped.
            id_local (int): Native database identifier.
            id_foraneo (str | int): External identifier from the partner.
            db (Session): Active database session. Defaults to SessionLocal().
        Returns:
            Relacion: The newly created or pre-existing relationship instance.
        =============================================================================
        """
        # Lazy initialization of the session if not provided
        session = db if db else SessionLocal()
        id_foraneo_str = str(id_foraneo).strip()

        try:
            # 1. Verify previous existence to avoid violating uniqueness constraints
            existe = (
                session.query(cls)
                .filter_by(socio_id=socio_id, tabla=tabla, id_foraneo=id_foraneo_str)
                .first()
            )

            if existe:
                return existe

            # 2. Instantiate and persist the new record
            nueva_relacion = cls(
                socio_id=socio_id,
                tabla=tabla,
                id_local=int(id_local),
                id_foraneo=id_foraneo_str,
            )
            session.add(nueva_relacion)
            session.commit()
            session.refresh(nueva_relacion)

            return nueva_relacion

        except Exception as e:
            session.rollback()
            raise RuntimeError(f"Error saving the individual relationship: {e}")
        finally:
            # If the session was created within this method, it is closed to prevent leaks
            if not db:
                session.close()

    @classmethod
    def get_external_mapping_cache(
        cls, socio_id: int, entidad: str, db: Session = SessionLocal()
    ) -> dict:
        """
        =============================================================================
        Method: get_external_mapping_cache
        Description: Retrieves all mappings for a specific partner and table in a
                     single database trip, returning a dictionary for O(1) lookups.
        Parameters:
            socio_id (int): Primary key of the commercial partner.
            entidad (str): Name of the logical table being mapped.
            db (Session): Active database session. Defaults to SessionLocal().
        Returns:
            dict: A mapping dictionary formatted as {id_foraneo: id_local}.
        =============================================================================
        """
        session = db if db else SessionLocal()
        try:
            mapeos = (
                session.query(cls.id_foraneo, cls.id_local)
                .filter(cls.socio_id == socio_id, cls.tabla == entidad)
                .all()
            )
            return {m.id_foraneo: m.id_local for m in mapeos}
        finally:
            if not db:
                session.close()
