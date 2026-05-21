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
        cls, razon_social: str, cuit: str, db: Session = SessionLocal(), **kwargs
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
        cuit_str = str(cuit).strip()
        rs_str = str(razon_social).strip()

        # 1. Validación de duplicados antes de insertar
        existe = (
            db.query(cls)
            .filter((cls.cuit == cuit_str) | (cls.razon_social == rs_str))
            .first()
        )

        if existe:
            raise ValueError(
                f"Ya existe un Socio Comercial registrado con el CUIT '{cuit_str}' "
                f"o la Razón Social '{rs_str}'."
            )

        try:
            # 2. Creación dinámica desempaquetando los atributos adicionales
            nuevo_socio = cls(razon_social=rs_str, cuit=cuit_str, **kwargs)
            db.add(nuevo_socio)
            db.commit()
            db.refresh(nuevo_socio)
            return nuevo_socio

        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Fallo al registrar el nuevo socio comercial: {e}")

    @classmethod
    def update_socio(
        cls, socio_id: int, db: Session = SessionLocal(), **kwargs
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
        =============================================================================
        """
        # 1. Recuperar el socio objetivo
        socio = db.query(cls).filter_by(id=socio_id).first()
        if not socio:
            raise ValueError(
                f"No se encontró ningún Socio Comercial con el ID {socio_id}."
            )

        try:
            # 2. Iterar sobre los argumentos y actualizar solo los atributos válidos
            for key, value in kwargs.items():
                # Protegemos el ID para que no pueda ser alterado accidentalmente
                if hasattr(socio, key) and key != "id":
                    setattr(socio, key, value)

            db.commit()
            db.refresh(socio)
            return socio

        except Exception as e:
            db.rollback()
            raise RuntimeError(
                f"Fallo al actualizar los datos del socio comercial: {e}"
            )


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

    tipo_credito = Column(
        Enum(TipoCredito), nullable=False, default=TipoCredito.FRANCES
    )

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

        # 1. Cláusula de Guardia: Proteger estados manuales inmutables
        estados_manuales = [EstadoCredito.RECHAZADO, EstadoCredito.JUDICIAL]

        # Parseo seguro del estado actual
        estado_actual = (
            self.estado
            if isinstance(self.estado, EstadoCredito)
            else EstadoCredito(self.estado)
        )

        if estado_actual in estados_manuales:
            # Imprimimos la advertencia. En producción, es ideal usar logging.warning()
            mensaje_alerta = f"⚠️ Advertencia: Intento de actualización automática omitido para el Crédito ID {self.id}. Estado bloqueado: {estado_actual.value}."
            print(mensaje_alerta)
            logging.warning(mensaje_alerta)

            return estado_actual.value

        # 2. Filtrar las cuotas que pertenecen activamente a la cartera
        cuotas_activas = [c for c in self.cuotas if c.estado != EstadoCuota.NO_COMPRADA]

        if not cuotas_activas:
            # Si todas fueron vendidas/cedidas, el crédito local se considera cancelado
            self.estado = EstadoCredito.CANCELADO
            return self.estado.value

        # 3. Evaluación de jerarquía para el ciclo dinámico
        # Regla 1: Si hay alguna cuota morosa, el crédito entero entra en mora
        if any(c.estado == EstadoCuota.MOROSA for c in cuotas_activas):
            self.estado = EstadoCredito.MOROSO

        # Regla 2: Si todas están pagas, el crédito finalizó con éxito
        elif all(c.estado == EstadoCuota.CANCELADA for c in cuotas_activas):
            self.estado = EstadoCredito.CANCELADO

        # Regla 3: Si hay cuotas pendientes pero ninguna vencida (aplica también a APROBADO)
        else:
            self.estado = EstadoCredito.ACTIVO

        return (
            self.estado.value if isinstance(self.estado, EstadoCredito) else self.estado
        )

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

    NO_COMPRADA = "NO COMPRADA"  # Cuotas de carteras originadas propias o que no corresponden a un flujo comprado
    PENDIENTE = "PENDIENTE"  # Cuota vigente que se encuentra dentro del plazo legal de pago y aún no venció
    MOROSA = "MOROSA"  # Cuota cuyo vencimiento ha expirado sin registrar el pago correspondiente
    CANCELADA = "CANCELADA"  # Cuota que ha sido totalmente liquidada y cancelada por el cliente o tercero


class EstadoCuotaCedida(enum.Enum):
    """
    =============================================================================
    Enum: EstadoCuotaCedida
    Description: Specifies the assignment and collection status of a specific
                 installment when it is involved in a portfolio sale or
                 transfer to a third-party financial entity.
    =============================================================================
    """

    NO_VENDIDA = "NO VENDIDA"  # Disponible para la venta (Originada propia)
    NO_COMPRADA = "NO COMPRADA"  # Estado para cuotas adquiridas que no se replican
    PENDIENTE = "PENDIENTE"  # Cedida al comprador pero aún no liquidada/cobrada
    MOROSA = "MOROSA"  # Cuota cedida que incurrió en mora tardía
    CANCELADA = "CANCELADA"  # Cuota cedida que ya fue totalmente pagada


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
        # 1. Cláusula de guardia: Si la cuota nunca fue comprada, no la tocamos
        if self.estado == EstadoCuota.NO_COMPRADA:
            return self.estado.value

        # 2. Matemática financiera con redondeo para evitar errores de coma flotante
        total_esperado = round(self.capital + self.interes + self.iva, 2)

        # Sumamos todo lo que ingresó por cobranzas asociadas a esta cuota
        total_cobrado = sum(
            round(c.capital + c.interes + c.iva, 2) for c in self.cobranzas
        )

        # 3. Lógica de transición de estados
        if total_cobrado >= total_esperado:
            self.estado = EstadoCuota.CANCELADA

        elif fecha_evaluacion > normalize_date(self.fecha_vencimiento):
            self.estado = EstadoCuota.MOROSA

        else:
            self.estado = EstadoCuota.PENDIENTE

        return self.estado.value

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

    # 1. Clave primaria única y auto-incremental del registro de mapeo
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 2. Clave foránea física apuntando al socio comercial dueño del sistema externo
    socio_id = Column(Integer, ForeignKey("socios_comerciales.id"), nullable=False)

    # 3. Identificador de la entidad o tabla mapeada (ej. "provincias", "empleadores")
    tabla = Column(String, nullable=False)

    # 4. ID nativo o local de nuestro sistema relacional
    id_local = Column(Integer, nullable=False)

    # 5. ID o código asignado en el archivo/sistema del socio comercial externo
    id_foraneo = Column(
        String, nullable=False
    )  # Se usa String por si vienen códigos con letras o ceros a la izquierda

    # 6. Atributo relacional ORM para navegación de objetos
    socio = relationship("SocioComercial", back_populates="relaciones")

    # 7. Restricciones de integridad a nivel de tabla
    __table_args__ = (
        # Previene que un mismo socio tenga duplicado el mapeo de un id local o foráneo en la misma entidad
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
        # Inicialización perezosa de la sesión si no se provee
        session = db if db else SessionLocal()
        id_foraneo_str = str(id_foraneo).strip()

        try:
            # 1. Verificar existencia previa para no violar restricciones de unicidad
            existe = (
                session.query(cls)
                .filter_by(socio_id=socio_id, tabla=tabla, id_foraneo=id_foraneo_str)
                .first()
            )

            if existe:
                return existe

            # 2. Instanciar y persistir el nuevo registro
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
            raise RuntimeError(f"Error al guardar la relación individual: {e}")
        finally:
            # Si la sesión fue creada dentro de este método, se cierra para evitar fugas
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
