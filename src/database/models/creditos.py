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
)
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from src.database import Base
from src.utils.dates import normalize_date


class OrigenCredito(enum.Enum):
    ORIGINADO = "ORIGINADO"
    COMPRADO = "COMPRADO"


class EstadoCredito(enum.Enum):
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    ACTIVO = "ACTIVO"
    CANCELADO = "CANCELADO"
    MOROSO = "MOROSO"
    JUDICIAL = "JUDICIAL"


class TipoCredito(enum.Enum):
    FRANCES = "SISTEMA FRANCES"
    ALEMAN = "SISTEMA ALEMAN"
    PENALTY = "PENALTY"

    @property
    def id(self) -> int:
        mapping = {
            "SISTEMA FRANCES": 1,
            "SISTEMA ALEMAN": 2,
            "PENALTY": 3,
        }
        return mapping[self.value]


class Credito(Base):
    """
    =============================================================================
    Model: Credito
    =============================================================================
    """

    __tablename__ = "creditos"

    __table_args__ = (
        UniqueConstraint(
            "id_externo",
            "socio_originador_id",
            name="uq_credito_id_externo_socio",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_externo = Column(String(50), index=True, nullable=True)
    cliente_cuil = Column(String(11), ForeignKey("clientes.cuil"), nullable=False)

    socio_originador_id = Column(
        Integer, ForeignKey("socios_comerciales.id"), nullable=True
    )
    cartera_id = Column(Integer, ForeignKey("carteras.id"), nullable=True)
    comision_id = Column(Integer, ForeignKey("tasas_y_comisiones.id"), nullable=True)

    capital = Column(Numeric(15, 2), nullable=False)
    tna_c_iva = Column(Numeric(15, 6), nullable=False)
    plazo = Column(Integer, nullable=False)
    fecha_emision = Column(Date, nullable=False)

    estado = Column(Enum(EstadoCredito), default=EstadoCredito.APROBADO)
    tipo_credito = Column(Enum(TipoCredito), nullable=False, default=TipoCredito.FRANCES)
    dia_vencimiento = Column(Integer, default=28, nullable=False)

    @hybrid_property
    def origen(self):
        if self.cartera_id is not None:
            return OrigenCredito.COMPRADO
        return OrigenCredito.ORIGINADO

    # Relationships
    cliente = relationship("Cliente", back_populates="creditos")
    cuotas = relationship(
        "Cuota", back_populates="credito", cascade="all, delete-orphan", lazy="selectin"
    )
    socio_originador = relationship(
        "SocioComercial", back_populates="creditos_originados"
    )
    cartera = relationship("Cartera", back_populates="creditos_incluidos")
    comision = relationship("TasaYComision", back_populates="creditos")
    transferencias = relationship("Transferencia", back_populates="credito", cascade="all, delete-orphan")
    documentos_legajo = relationship("DocumentoLegajo", back_populates="credito", cascade="all, delete-orphan")

    def actualizar_estado(self) -> str:
        estados_manuales = [EstadoCredito.RECHAZADO, EstadoCredito.JUDICIAL]
        estado_actual = (
            self.estado
            if isinstance(self.estado, EstadoCredito)
            else EstadoCredito(self.estado)
        )

        if estado_actual in estados_manuales:
            mensaje_alerta = f"⚠️ Warning: Automatic update attempt skipped for Credito ID {self.id}. State blocked: {estado_actual.value}."
            print(mensaje_alerta)
            logging.warning(mensaje_alerta)
            return estado_actual.value

        cuotas_activas = [c for c in self.cuotas if c.estado != EstadoCuota.NO_COMPRADA]

        if not cuotas_activas:
            self.estado = EstadoCredito.CANCELADO
            return self.estado.value

        if any(c.estado == EstadoCuota.MOROSA for c in cuotas_activas):
            self.estado = EstadoCredito.MOROSO
        elif all(c.estado == EstadoCuota.CANCELADA for c in cuotas_activas):
            self.estado = EstadoCredito.CANCELADO
        else:
            self.estado = EstadoCredito.ACTIVO

        return (
            self.estado.value if isinstance(self.estado, EstadoCredito) else self.estado
        )

    @property
    def carteras_de_venta(self) -> list:
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

    def validar_politicas(self, db_session) -> bool:
        """
        =============================================================================
        Method: validar_politicas
        Description: Verifica que el cliente cumpla con las condiciones de la 
                     política crediticia activa (del socio, o la general).
        Returns:
            bool: True si cumple todas las condiciones.
        Raises:
            ValueError: Si alguna condición no se cumple o faltan datos.
        =============================================================================
        """
        from src.database.models import PoliticaCrediticia, SexoEnum
        from datetime import date

        # 1. Obtener la política (específica del socio, o la general de fallback)
        politica = None
        if self.socio_originador_id:
            politica = db_session.query(PoliticaCrediticia).filter_by(socio_originador_id=self.socio_originador_id).order_by(PoliticaCrediticia.fecha.desc()).first()
        
        if not politica:
            politica = db_session.query(PoliticaCrediticia).filter_by(socio_originador_id=None).order_by(PoliticaCrediticia.fecha.desc()).first()

        if not politica:
            raise ValueError("No se encontraron políticas crediticias configuradas en el sistema.")

        # 2. Validar que el cliente tenga los datos necesarios
        cliente = self.cliente
        if not cliente:
            raise ValueError("El crédito debe tener un cliente asignado para validar las políticas.")
        if not cliente.fecha_nacimiento:
            raise ValueError("El cliente no tiene una fecha de nacimiento registrada.")

        # 3. Calcular edad y antigüedad
        hoy = date.today()
        edad = hoy.year - cliente.fecha_nacimiento.year - ((hoy.month, hoy.day) < (cliente.fecha_nacimiento.month, cliente.fecha_nacimiento.day))

        antiguedad_anios = 0
        if cliente.fecha_ingreso:
            antiguedad_anios = hoy.year - cliente.fecha_ingreso.year - ((hoy.month, hoy.day) < (cliente.fecha_ingreso.month, cliente.fecha_ingreso.day))

        # Determinar si es jubilado en base al tipo de empleador (es_pasivo = True)
        es_jubilado = False
        if cliente.empleador and cliente.empleador.es_pasivo:
            es_jubilado = True

        # 4. Validar Edad
        if es_jubilado:
            if edad < politica.edad_minima_jubilado or edad > politica.edad_maxima_jubilado:
                raise ValueError(f"La edad del jubilado ({edad}) no está en el rango permitido ({politica.edad_minima_jubilado}-{politica.edad_maxima_jubilado}).")
        else:
            if cliente.sexo == SexoEnum.MASCULINO:
                if edad < politica.edad_minima_hombre or edad > politica.edad_maxima_hombre:
                    raise ValueError(f"La edad ({edad}) no está en el rango permitido para hombres ({politica.edad_minima_hombre}-{politica.edad_maxima_hombre}).")
            elif cliente.sexo == SexoEnum.FEMENINO:
                if edad < politica.edad_minima_mujer or edad > politica.edad_maxima_mujer:
                    raise ValueError(f"La edad ({edad}) no está en el rango permitido para mujeres ({politica.edad_minima_mujer}-{politica.edad_maxima_mujer}).")
            else:
                # Si el sexo es OTRO, aplicamos la regla más restrictiva de ambos
                min_edad = max(politica.edad_minima_hombre, politica.edad_minima_mujer)
                max_edad = min(politica.edad_maxima_hombre, politica.edad_maxima_mujer)
                if edad < min_edad or edad > max_edad:
                    raise ValueError(f"La edad ({edad}) no está en el rango permitido ({min_edad}-{max_edad}).")

        # 5. Validar Antigüedad
        if not cliente.fecha_ingreso:
            # Si requiere antigüedad y no tiene fecha de ingreso
            if (es_jubilado and politica.antiguedad_jubilado > 0) or (not es_jubilado and politica.antiguedad_empleado > 0):
                raise ValueError("El cliente no tiene fecha de ingreso registrada y la política exige antigüedad.")
        else:
            if es_jubilado:
                if antiguedad_anios < politica.antiguedad_jubilado:
                    raise ValueError(f"La antigüedad ({antiguedad_anios} años) es menor al mínimo para jubilados ({politica.antiguedad_jubilado} años).")
            else:
                if antiguedad_anios < politica.antiguedad_empleado:
                    raise ValueError(f"La antigüedad ({antiguedad_anios} años) es menor al mínimo para empleados ({politica.antiguedad_empleado} años).")

        return True

    def __repr__(self):
        return (
            f"<Credito(id={self.id}, cliente='{self.cliente_cuil}', "
            f"monto={self.capital}, origen={self.origen.value})>"
        )


class EstadoCuota(enum.Enum):
    NO_COMPRADA = "NO COMPRADA"
    PENDIENTE = "PENDIENTE"
    MOROSA = "MOROSA"
    CANCELADA = "CANCELADA"


class EstadoCuotaCedida(enum.Enum):
    NO_VENDIDA = "NO VENDIDA"
    NO_COMPRADA = "NO COMPRADA"
    PENDIENTE = "PENDIENTE"
    MOROSA = "MOROSA"
    CANCELADA = "CANCELADA"


class Cuota(Base):
    """
    =============================================================================
    Model: Cuota
    =============================================================================
    """

    __tablename__ = "cuotas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    credito_id = Column(Integer, ForeignKey("creditos.id"), nullable=False)
    nro_cuota = Column(Integer, nullable=False)

    fecha_vencimiento = Column(Date, nullable=False)
    capital = Column(Numeric(15, 2), nullable=False)
    interes = Column(Numeric(15, 2), nullable=False)
    iva = Column(Numeric(15, 2), default=0.0)

    estado = Column(Enum(EstadoCuota), nullable=False, default=EstadoCuota.PENDIENTE)
    estado_cesion = Column(
        Enum(EstadoCuotaCedida, name="estadocuotacedida"),
        nullable=False,
        default=EstadoCuotaCedida.NO_VENDIDA,
    )

    # Relationships
    credito = relationship("Credito", back_populates="cuotas")
    movimientos_cartera = relationship("OperacionCartera", back_populates="cuota", lazy="selectin")
    cobranzas = relationship("Cobranza", back_populates="cuota")
    liquidaciones = relationship("LiquidacionCuotaCedida", back_populates="cuota")

    def actualizar_estado(self, fecha_evaluacion: str | datetime) -> str:
        fecha_evaluacion = normalize_date(fecha_evaluacion)
        if self.estado == EstadoCuota.NO_COMPRADA:
            return self.estado.value

        total_esperado = round(self.capital + self.interes + self.iva, 2)
        total_cobrado = round(sum(
            round(c.capital + c.interes + c.iva, 2) for c in self.cobranzas
        ), 2)

        if total_cobrado >= total_esperado:
            self.estado = EstadoCuota.CANCELADA
        elif fecha_evaluacion > normalize_date(self.fecha_vencimiento):
            self.estado = EstadoCuota.MOROSA
        else:
            self.estado = EstadoCuota.PENDIENTE

        return self.estado.value

    def actualizar_estado_cedido(self, fecha_evaluacion: str | datetime) -> str:
        fecha_evaluacion = normalize_date(fecha_evaluacion)
        if self.estado_cesion in [
            EstadoCuotaCedida.NO_COMPRADA,
            EstadoCuotaCedida.NO_VENDIDA,
        ]:
            return self.estado_cesion.value

        total_esperado = round(self.capital + self.interes + self.iva, 2)
        total_cobrado = round(sum(
            round(c.capital + c.interes + c.iva, 2) for c in self.liquidaciones
        ), 2)

        if total_cobrado >= total_esperado:
            self.estado_cesion = EstadoCuotaCedida.CANCELADA
        elif fecha_evaluacion > normalize_date(self.fecha_vencimiento):
            self.estado_cesion = EstadoCuotaCedida.MOROSA
        else:
            self.estado_cesion = EstadoCuotaCedida.PENDIENTE

        return self.estado_cesion.value

    def __repr__(self):
        return f"<Cuota(credito_id={self.credito_id}, nro={self.nro_cuota}, estado={self.estado}, estado_cesion={self.estado_cesion})>"


class Transferencia(Base):
    __tablename__ = "transferencias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cbu = Column(String(22), nullable=False)
    monto = Column(Numeric(15, 2), nullable=False)
    cuit = Column(String(11), nullable=False)
    credito_id = Column(Integer, ForeignKey("creditos.id"), nullable=False)
    razon_social = Column(String(255), nullable=False)

    credito = relationship("Credito", back_populates="transferencias")

    def __repr__(self):
        return f"<Transferencia(cbu={self.cbu}, monto={self.monto}, cuit={self.cuit}, credito_id={self.credito_id}, razon_social={self.razon_social})>"


class DocumentoLegajo(Base):
    __tablename__ = "documentos_legajo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    credito_id = Column(Integer, ForeignKey("creditos.id"), nullable=False)
    nombre_archivo = Column(String(255), nullable=False)
    ruta_archivo = Column(String(500), nullable=False)
    tipo_archivo = Column(String(50), nullable=False)
    fecha_subida = Column(DateTime, default=func.now(), nullable=False)

    credito = relationship("Credito", back_populates="documentos_legajo")

    def __repr__(self):
        return f"<DocumentoLegajo(id={self.id}, credito_id={self.credito_id}, nombre_archivo={self.nombre_archivo})>"