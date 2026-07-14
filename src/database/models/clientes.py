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


class SexoEnum(enum.Enum):
    MASCULINO = "M"
    FEMENINO = "F"
    OTRO = "O"


class EstadoClienteEnum(enum.Enum):
    ACTIVO = "ACTIVO"
    MOROSO = "MOROSO"
    INCOBRABLE = "INCOBRABLE"
    INACTIVO = "INACTIVO"


class Empleador(Base):
    """
    Represents the employer or withholding agent (Agente de Retención)
    for payroll deduction loans (Código de Descuento).
    """

    __tablename__ = "empleadores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuit = Column(String(11), unique=True, nullable=True)
    razon_social = Column(String(150), nullable=False)
    es_pasivo = Column(Boolean, default=False)  # True para Jubilados/Pensionados
    domicilio_calle = Column(String(150), nullable=True)
    domicilio_nro = Column(Integer, nullable=True)
    domicilio_piso = Column(String(10), nullable=True)
    domicilio_depto = Column(String(10), nullable=True)
    id_provincia = Column(Integer, ForeignKey("provincias.id"), nullable=True)
    provincia = relationship("Provincia")
    id_codigo_postal = Column(String(10), nullable=True)
    localidad = Column(String(100), nullable=True)
    telefono = Column(String(50), nullable=True)

    # Relationships
    empleados = relationship("Cliente", back_populates="empleador")

    socio_comercial_id = Column(
        Integer, ForeignKey("socios_comerciales.id"), nullable=True
    )
    socio_comercial = relationship("SocioComercial", back_populates="empleadores")

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
    =============================================================================
    Model: Cliente
    =============================================================================
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
    estado_civil = Column(String(50), nullable=True)
    nacionalidad = Column(String(100), nullable=True)

    # Employment details / Status
    legajo = Column(String(50), nullable=True)
    estado = Column(Enum(EstadoClienteEnum), nullable=True)
    fecha_estado = Column(Date, nullable=True, default=date.today, onupdate=date.today)

    # Banking details
    cbu = Column(String(22), nullable=True)
    cuenta_bancaria = Column(String(50), nullable=True)
    banco = Column(String(100), nullable=True)

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

    # New ForeignKey linking to Empleador
    empleador_id = Column(Integer, ForeignKey("empleadores.id"), nullable=True)
    cargo = Column(String(100), nullable=True)

    # Employment details / Status
    fecha_ingreso = Column(Date, nullable=True)
    remuneracion = Column(Numeric(15, 2), default=0.0)  # Monthly income for credit scoring

    # Compliance columns
    pep = Column(Boolean, default=False)
    repet = Column(Boolean, default=False)
    
    # Relationships
    creditos = relationship("Credito", back_populates="cliente")
    provincia = relationship("Provincia", back_populates="clientes")
    empleador = relationship("Empleador", back_populates="empleados")
    referidos = relationship("Referido", back_populates="cliente", cascade="all, delete-orphan")

    @validates("cuil", "documento")
    def validate_cuil_dni(self, key, value):
        if value is None:
            return value
        
        clean_value = "".join(filter(str.isdigit, str(value)))
        
        if key == "cuil":
            if self.documento:
                clean_doc = "".join(filter(str.isdigit, str(self.documento)))
                if clean_doc not in clean_value:
                    raise ValueError(
                        f"Validation error: Documento '{clean_doc}' must be contained within CUIL '{clean_value}'."
                    )
        elif key == "documento":
            if self.cuil:
                clean_cuil = "".join(filter(str.isdigit, str(self.cuil)))
                if clean_value not in clean_cuil:
                    raise ValueError(
                        f"Validation error: Documento '{clean_value}' must be contained within CUIL '{clean_cuil}'."
                    )
        return value

    def actualizar_estado(self) -> str:
        from src.database.models.creditos import EstadoCredito
        
        creditos_cli = self.creditos
        if not creditos_cli:
            self.estado = EstadoClienteEnum.INACTIVO
            return self.estado.value
        
        estados_str = []
        for cred in creditos_cli:
            e = cred.estado
            if isinstance(e, EstadoCredito):
                estados_str.append(e.value)
            else:
                estados_str.append(str(e))

        if "JUDICIAL" in estados_str:
            self.estado = EstadoClienteEnum.INCOBRABLE
        elif "MOROSO" in estados_str:
            self.estado = EstadoClienteEnum.MOROSO
        else:
            all_cancelado = all(e == "CANCELADO" for e in estados_str)
            if all_cancelado:
                self.estado = EstadoClienteEnum.INACTIVO
            else:
                self.estado = EstadoClienteEnum.ACTIVO

        return self.estado.value if isinstance(self.estado, EstadoClienteEnum) else self.estado

    def __repr__(self):
        return f"<Cliente(cuil='{self.cuil}', apellido='{self.apellido}', nombre='{self.nombre}')>"


class Referido(Base):
    """
    Represents a referral made by a client.
    """

    __tablename__ = "referidos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cliente_cuil = Column(String(11), ForeignKey("clientes.cuil"), nullable=False)
    
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    telefono = Column(String(50), nullable=True)
    email = Column(String(150), nullable=True)

    # Relationships
    cliente = relationship("Cliente", back_populates="referidos")

    def __repr__(self):
        return f"<Referido(nombre='{self.nombre}', apellido='{self.apellido}', cliente_cuil='{self.cliente_cuil}')>"

