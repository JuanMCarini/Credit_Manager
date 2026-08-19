import enum
from sqlalchemy import (
    Column,
    Date,
    Enum,
    Numeric,
    ForeignKey,
    Integer,
    String,
    event,
    select,
    func
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from src.database import Base


class EstadoCheque(enum.Enum):
    PENDIENTE = "PENDIENTE"
    DEPOSITADO = "DEPOSITADO"
    RECHAZADO = "RECHAZADO"
    ACREDITADO = "ACREDITADO"
    VENDIDO = "VENDIDO"
    COMPRADO = "COMPRADO"


class CalificacionEmisor(enum.Enum):
    EXCELENTE = "EXCELENTE"
    BUENO = "BUENO"
    REGULAR = "REGULAR"
    MALO = "MALO"
    RECHAZADO = "RECHAZADO"


class OperadorCheque(Base):
    """
    =============================================================================
    Model: OperadorCheque
    =============================================================================
    """

    __tablename__ = "operadores_cheques"

    cuit = Column(String(11), primary_key=True, unique=True, nullable=False)
    razon_social = Column(String(150), nullable=False)
    calificacion = Column(Enum(CalificacionEmisor), nullable=True)
    telefono = Column(String(50), nullable=True)
    email = Column(String(150), nullable=True)

    # Relaciones
    cheques = relationship("Cheque", back_populates="emisor")
    operaciones = relationship("OperacionCheque", back_populates="operador")


def insert_default_operador(target, connection, **kw):
    from src.config import COMPANY_DATA
    connection.execute(
        target.insert(),
        {
            "cuit": COMPANY_DATA.cuit,
            "razon_social": COMPANY_DATA.razon_social,
            "calificacion": CalificacionEmisor.EXCELENTE.value,
            "telefono": COMPANY_DATA.telefono,
            "email": COMPANY_DATA.email_contacto
        }
    )

event.listen(OperadorCheque.__table__, 'after_create', insert_default_operador)


class Cheque(Base):
    """
    =============================================================================
    Model: Cheque
    =============================================================================
    """

    __tablename__ = "cheques"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha_emision = Column(Date, nullable=False)
    fecha_pago = Column(Date, nullable=False)
    numero = Column(String(20), nullable=False)
    monto = Column(Numeric(15, 2), nullable=False)
    
    emisor_cuit = Column(String(11), ForeignKey("operadores_cheques.cuit"), nullable=False)
    banco_id = Column(Integer, ForeignKey("bancos.id"), nullable=False)
    cliente_cuil = Column(String(11), ForeignKey("clientes.cuil"), nullable=False)
    
    estado = Column(Enum(EstadoCheque), default=EstadoCheque.PENDIENTE)
    
    # Relaciones
    emisor = relationship("OperadorCheque", back_populates="cheques")
    banco = relationship("Banco")
    operaciones = relationship("OperacionCheque", back_populates="cheque")

    @hybrid_property
    def beneficiario(self):
        if self.operaciones:
            ultima_op = max(self.operaciones, key=lambda x: (x.fecha_operacion, x.id))
            return ultima_op.operador
        else:
            return self.emisor

    @beneficiario.expression
    def beneficiario(cls):
        # Subconsulta para obtener el CUIT del operador en la última operación
        ultima_op_subq = (
            select(OperacionCheque.operador_cuil)
            .where(OperacionCheque.cheque_id == cls.id)
            .order_by(OperacionCheque.fecha_operacion.desc(), OperacionCheque.id.desc())
            .limit(1)
            .scalar_subquery()
        )
        # Retorna el CUIT de la última operación o el CUIT del emisor si no hay operaciones
        return func.coalesce(ultima_op_subq, cls.emisor_cuit)

class TipoOperacionCheque(enum.Enum):
    COMPRA = "COMPRA"
    VENTA = "VENTA"

class OperacionCheque(Base):
    """
    =============================================================================
    Model: OperacionCheque
    =============================================================================
    """

    __tablename__ = "operaciones_cheques"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha_operacion = Column(Date, nullable=False)
    cheque_id = Column(Integer, ForeignKey("cheques.id"), nullable=False)
    operador_cuil = Column(String(11), ForeignKey("operadores_cheques.cuit"), nullable=False)
    tipo_operacion = Column(Enum(TipoOperacionCheque), nullable=False)
    tna_descuento = Column(Numeric(15, 10), nullable=False) # tasa nominal anual 130% seria 1.3000
    plazo_dias = Column(Integer, nullable=False)
    dias_castigo = Column(Integer, nullable=False, default=0)
    porcentaje_gastos = Column(Numeric(15, 10), nullable=False, default=0.028)

    # Relaciones
    cheque = relationship("Cheque", back_populates="operaciones")
    operador = relationship("OperadorCheque", back_populates="operaciones")

    @hybrid_property
    def gastos(self):
        gastos = float(self.cheque.monto) * float(self.porcentaje_gastos)
        return round(gastos, 2)

    @hybrid_property
    def intereses(self):
        dias_totales = self.plazo_dias + self.dias_castigo
        # El valor actual es el capital que rinde al descontarlo
        valor_actual = float(self.cheque.monto) / (1 + (float(self.tna_descuento) / 365) * dias_totales)
        # Los intereses son la diferencia entre el valor nominal del cheque y su valor actual
        intereses = float(self.cheque.monto) - valor_actual
        return round(intereses, 2)

    @hybrid_property
    def iva(self):
        return round((self.intereses + self.gastos) * 0.21, 2)

    @hybrid_property
    def monto_descontado(self): 
        return self.intereses + self.gastos + self.iva

    @hybrid_property
    def importe_neto_recibir(self):
        return float(self.cheque.monto) - self.monto_descontado

    @hybrid_property
    def tir_diaria(self):
        dias_totales = self.plazo_dias + self.dias_castigo
        if dias_totales <= 0 or self.importe_neto_recibir <= 0:
            return 0.0
        return (float(self.cheque.monto) / float(self.importe_neto_recibir)) ** (1 / dias_totales) - 1

    @hybrid_property
    def tem(self):
        return ((1 + self.tir_diaria) ** 30) - 1

    @hybrid_property
    def tea(self):
        return ((1 + self.tir_diaria) ** 365) - 1