# pyrefly: ignore [missing-import]
import pytest
from datetime import date
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from src.database import Base
from src.database.models import Cliente, SocioComercial, Cartera, Credito, TipoOperacionCartera


@pytest.fixture(scope="session")
def engine():
    """
    Creates an in-memory SQLite engine for the duration of the test session.
    Forces foreign keys to be respected.
    """
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    
    # Event listener to force SQLite Foreign Key checks
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        
    return engine


@pytest.fixture(scope="function")
def db_session(engine):
    """
    Creates and drops tables before and after each test, yielding an active session.
    """
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    # Register application database triggers (event listeners)
    # They are automatically registered at module level when we import src.database.events,
    # but we import them here explicitly to ensure they are active.
    from src.database import events  # noqa: F401

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def dummy_cliente(db_session):
    """
    Provides a persisted Cliente instance.
    """
    cliente = Cliente(
        cuil="20999999999",
        documento="99999999",
        apellido="Perez",
        nombre="Juan",
        fecha_nacimiento=date(1990, 1, 1),
    )
    db_session.add(cliente)
    db_session.commit()
    return cliente


@pytest.fixture
def dummy_socio(db_session):
    """
    Provides a persisted SocioComercial instance.
    """
    socio = SocioComercial(
        razon_social="Fideicomiso Test",
        cuit="30111111118",
        domicilio_legal="Calle Falsa 123",
        contacto_nombre="Carlos Socio",
        mail="carlos@test.com",
        telefono="123456",
        dia_corte=28,
    )
    db_session.add(socio)
    db_session.commit()
    return socio


@pytest.fixture
def dummy_cartera(db_session, dummy_socio):
    """
    Provides a persisted Cartera purchase instance.
    """
    cartera = Cartera(
        nombre="Cartera Compra Test",
        fecha_compra=date(2026, 5, 1),
        socio_id=dummy_socio.id,
        iva=True,
        recurso=True,
        tna_descuento=0.45,
        tipo_operacion=TipoOperacionCartera.COMPRA,
    )
    db_session.add(cartera)
    db_session.commit()
    return cartera
