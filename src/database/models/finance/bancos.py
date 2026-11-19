import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, Float, Numeric, Enum as SQLEnum, Boolean, inspect, text
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
from src.database import Base

class CategoriaMovimiento(enum.Enum):
    INGRESO = "Ingreso"
    EGRESO = "Egreso"
    SUSCRIPCION_FCI = "Suscripción FCI"
    RESCATE_FCI = "Rescate FCI"
    PLAZO_FIJO_INGRESOS = "Ingresos a plazo fijo"
    PLAZO_FIJO_EGRESOS = "Egresos de plazo fijo"

class Banco(Base):
    __tablename__ = "bancos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_banco = Column(String(100), nullable=False)
    parser_type = Column(String(50), nullable=True)
    socio_id = Column(Integer, ForeignKey("socios_comerciales.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    cuentas = relationship("Cuenta", back_populates="banco")
    socio = relationship("SocioComercial")

class TipoMoneda(enum.Enum):
    PESOS = "Pesos Argentinos $"
    DOLARES = "Dólares Estadounidenses USD"
    EUROS = "Euros EUR"

class Cuenta(Base):
    __tablename__ = "cuentas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), unique=True, nullable=False)
    banco_id = Column(Integer, ForeignKey("bancos.id"), nullable=False)
    nro = Column(String(20), unique=False, nullable=False)
    cbu = Column(String(22), nullable=False, unique=True)
    alias = Column(String(50), nullable=False, unique=True)
    tipo_cuenta = Column(String(20), nullable=False)
    moneda = Column(SQLEnum(TipoMoneda), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    banco = relationship("Banco", back_populates="cuentas")
    movimientos = relationship("Movimiento", back_populates="cuenta", order_by="Movimiento.fecha")

    @property
    def saldo(self) -> float:
        # Sumamos o restamos dependiendo del tipo de movimiento
        total = 0.0
        for mov in self.movimientos:
            if not mov.concepto:
                continue
            monto = float(mov.monto)
            if mov.concepto.tipo_movimiento in (CategoriaMovimiento.INGRESO, CategoriaMovimiento.RESCATE_FCI, CategoriaMovimiento.PLAZO_FIJO_EGRESOS):
                total += monto
            elif mov.concepto.tipo_movimiento in (CategoriaMovimiento.EGRESO, CategoriaMovimiento.SUSCRIPCION_FCI, CategoriaMovimiento.PLAZO_FIJO_INGRESOS):
                total -= monto
        return round(total, 2)

    @property
    def saldo_fci(self) -> float:
        # Sumamos o restamos dependiendo del tipo de movimiento
        total = 0.0
        for mov in self.movimientos:
            if not mov.concepto:
                continue
            monto = float(mov.monto)
            if mov.concepto.tipo_movimiento == CategoriaMovimiento.RESCATE_FCI:
                total -= monto
            elif mov.concepto.tipo_movimiento == CategoriaMovimiento.SUSCRIPCION_FCI:
                total += monto

            total = max(0.0, total)

        return round(total, 2)

    @property
    def saldo_plazo_fijo(self) -> float:
        # Sumamos o restamos dependiendo del tipo de movimiento
        total = 0.0
        for mov in self.movimientos:
            if not mov.concepto:
                continue
            monto = float(mov.monto)
            if mov.concepto.tipo_movimiento == CategoriaMovimiento.PLAZO_FIJO_INGRESOS:
                total += monto
            elif mov.concepto.tipo_movimiento == CategoriaMovimiento.PLAZO_FIJO_EGRESOS:
                total -= monto

            total = max(0.0, total)

        return round(total, 2)

class Concepto(Base):
    __tablename__ = "conceptos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    tipo_movimiento = Column(SQLEnum(CategoriaMovimiento), nullable=False)
    descripcion = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    clasificacion_id = Column(Integer, ForeignKey("clasificaciones.id"), nullable=True)

    # Relación a Movimientos y Clasificaciones
    movimientos = relationship("Movimiento", back_populates="concepto")
    clasificacion = relationship("Clasificacion", back_populates="conceptos")

class Clasificacion(Base):
    __tablename__ = "clasificaciones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    descripcion = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    conceptos = relationship("Concepto", back_populates="clasificacion", cascade="all, delete-orphan")

class Movimiento(Base):
    __tablename__ = "movimientos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cuenta_id = Column(Integer, ForeignKey("cuentas.id"), nullable=False)
    fecha = Column(Date, nullable=False)
    nro_comprobante = Column(String(20), nullable=True)
    monto = Column(Numeric(15, 2), nullable=False)
    concepto_id = Column(Integer, ForeignKey("conceptos.id"), nullable=True)
    descripcion = Column(String(255), nullable=True)
    info_adicional = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    concepto = relationship("Concepto", back_populates="movimientos")
    cuenta = relationship("Cuenta", back_populates="movimientos")
    cheques = relationship("Cheque", back_populates="movimiento")

    @property
    def cheque_id(self):
        return self.cheques[0].id if self.cheques else None


def find_socio_for_banco(db: Session, banco: Banco):
    """Busca el SocioComercial existente vinculado a un Banco (sin crear uno nuevo) y asegura banco.socio_id."""
    from src.database.models.socios import SocioComercial

    if banco.socio_id:
        socio = db.query(SocioComercial).filter(SocioComercial.id == banco.socio_id).first()
        if socio:
            return socio

    nombre_lower = (banco.nombre_banco or "").strip().lower()
    if not nombre_lower:
        return None

    socio = db.query(SocioComercial).filter(func.lower(SocioComercial.razon_social) == nombre_lower).first()
    if socio:
        banco.socio_id = socio.id
        db.flush()
        return socio

    keyword = nombre_lower
    for prefix in ("banco de la ", "banco de ", "banco del ", "banco "):
        if keyword.startswith(prefix):
            keyword = keyword[len(prefix):].strip()
            break

    if len(keyword) >= 3:
        matches = (
            db.query(SocioComercial)
            .filter(SocioComercial.razon_social.ilike(f"%{keyword}%"))
            .all()
        )
        if len(matches) == 1:
            socio = matches[0]
            banco.socio_id = socio.id
            db.flush()
            return socio

    return None


get_or_create_socio_for_banco = find_socio_for_banco


def ensure_bancos_schema(engine) -> None:
    """Asegura de forma idempotente la columna `socio_id` (ON DELETE SET NULL) en `bancos` y la restricción actualizada en `relaciones`."""
    try:
        inspector = inspect(engine)
        if inspector.has_table("bancos"):
            existing_cols = {col["name"] for col in inspector.get_columns("bancos")}
            if "socio_id" not in existing_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text("ALTER TABLE bancos ADD COLUMN socio_id INTEGER REFERENCES socios_comerciales(id) ON DELETE SET NULL")
                    )
            elif engine.dialect.name == "postgresql":
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE bancos DROP CONSTRAINT IF EXISTS bancos_socio_id_fkey"))
                    conn.execute(
                        text(
                            "ALTER TABLE bancos ADD CONSTRAINT bancos_socio_id_fkey "
                            "FOREIGN KEY (socio_id) REFERENCES socios_comerciales(id) ON DELETE SET NULL"
                        )
                    )
        if inspector.has_table("movimientos"):
            mov_cols = {col["name"] for col in inspector.get_columns("movimientos")}
            if "info_adicional" not in mov_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text("ALTER TABLE movimientos ADD COLUMN info_adicional VARCHAR(255)")
                    )
        if inspector.has_table("relaciones") and engine.dialect.name == "postgresql":
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE relaciones DROP CONSTRAINT IF EXISTS uq_socio_tabla_local")
                )
    except Exception as exc:
        print(f"⚠️ Warning al verificar esquema de bancos/relaciones: {exc}")

