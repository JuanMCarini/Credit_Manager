import enum
from datetime import date

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func
)
from sqlalchemy.orm import Session, relationship

from src.database import Base, SessionLocal


class SocioComercial(Base):
    """
    =============================================================================
    Model: SocioComercial
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
    comisiones_originadas = relationship(
        "TasaYComision", foreign_keys="[TasaYComision.socio_originador_id]", back_populates="socio_originador"
    )
    comisiones_intermediarias = relationship(
        "TasaYComision", foreign_keys="[TasaYComision.socio_intermediario_id]", back_populates="socio_intermediario"
    )
    empleadores = relationship("Empleador", back_populates="socio_comercial")
    politicas_crediticias = relationship("PoliticaCrediticia", back_populates="socio_originador")
    def __repr__(self):
        return (
            f"<SocioComercial(razon_social='{self.razon_social}', cuit='{self.cuit}')>"
        )

    @classmethod
    def create_socio(
        cls, razon_social: str, cuit: str, db: Session | None = None, **kwargs
    ) -> "SocioComercial":
        db = db or SessionLocal()
        cuit_str = str(cuit).strip()
        rs_str = str(razon_social).strip()

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
        db = db or SessionLocal()
        socio = db.query(cls).filter_by(id=socio_id).first()
        if not socio:
            raise ValueError(f"No Socio Comercial was found with ID {socio_id}.")

        try:
            for key, value in kwargs.items():
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
    monto = Column(Numeric(15, 2), nullable=False)


class Relacion(Base):
    """
    =============================================================================
    Model: Relacion
    =============================================================================
    """

    __tablename__ = "relaciones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    socio_id = Column(Integer, ForeignKey("socios_comerciales.id"), nullable=False)
    tabla = Column(String, nullable=False)
    id_local = Column(Integer, nullable=False)
    id_foraneo = Column(String, nullable=False)

    socio = relationship("SocioComercial", back_populates="relaciones")

    __table_args__ = (
        UniqueConstraint("socio_id", "tabla", "id_local", name="uq_socio_tabla_local"),
        UniqueConstraint("socio_id", "tabla", "id_foraneo", name="uq_socio_tabla_foraneo"),
    )

    @classmethod
    def add_single_mapping(
        cls,
        socio_id: int,
        tabla: str,
        id_local: int,
        id_foraneo: str | int,
        db: Session | None = None,
    ) -> "Relacion":
        session = db if db else SessionLocal()
        id_foraneo_str = str(id_foraneo).strip()

        try:
            existe = (
                session.query(cls)
                .filter_by(socio_id=socio_id, tabla=tabla, id_foraneo=id_foraneo_str)
                .first()
            )
            if existe:
                return existe

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
            if not db:
                session.close()

    @classmethod
    def get_external_mapping_cache(
        cls, socio_id: int, entidad: str, db: Session | None = None
    ) -> dict:
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


class EstadoComisionEnum(enum.Enum):
    ACTIVA = "ACTIVA"
    INACTIVA = "INACTIVA"
    SEMIACTIVA = "SEMI ACTIVA"


class TasaYComision(Base):
    """
    =============================================================================
    Model: TasaYComision
    =============================================================================
    """

    __tablename__ = "tasas_y_comisiones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(Date, nullable=False)
    estado = Column(Enum(EstadoComisionEnum, values_callable=lambda obj: [e.value for e in obj]), nullable=False, default=EstadoComisionEnum.ACTIVA.value)

    socio_originador_id = Column(Integer, ForeignKey("socios_comerciales.id"), nullable=False)
    socio_intermediario_id = Column(Integer, ForeignKey("socios_comerciales.id"), nullable=False)

    plazo = Column(Integer, nullable=False, default=12)
    tna_c_iva = Column(Numeric(15, 6), nullable=False, default=0.0)

    colocacion_originador = Column(Numeric(15, 6), nullable=False, default=0.0)
    colocacion_intermediario = Column(Numeric(15, 6), nullable=False, default=0.0)

    cobranza_originador = Column(Numeric(15, 6), nullable=False, default=0.0)
    cobranza_intermediario = Column(Numeric(15, 6), nullable=False, default=0.0)

    colocacion_propia = Column(Numeric(15, 6), nullable=False, default=0.0)

    socio_originador = relationship("SocioComercial", foreign_keys=[socio_originador_id], back_populates="comisiones_originadas")
    socio_intermediario = relationship("SocioComercial", foreign_keys=[socio_intermediario_id], back_populates="comisiones_intermediarias")
    creditos = relationship("Credito", back_populates="comision")


class PoliticaCrediticia(Base):
    __tablename__ = "politicas_crediticias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(Date, nullable=False, server_default=func.now(), onupdate=func.now())
    socio_originador_id = Column(Integer, ForeignKey("socios_comerciales.id"), nullable=True)

    edad_minima_hombre = Column(Integer, nullable=False)
    edad_maxima_hombre = Column(Integer, nullable=False)
    edad_minima_mujer = Column(Integer, nullable=False)
    edad_maxima_mujer = Column(Integer, nullable=False)
    edad_minima_jubilado = Column(Integer, nullable=False)
    edad_maxima_jubilado = Column(Integer, nullable=False)
    antiguedad_empleado = Column(Integer, nullable=False)
    antiguedad_jubilado = Column(Integer, nullable=False)

    socio_originador = relationship("SocioComercial", foreign_keys=[socio_originador_id], back_populates="politicas_crediticias")
