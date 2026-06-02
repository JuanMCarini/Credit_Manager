# pyrefly: ignore [missing-import]
import pytest
from datetime import date
from sqlalchemy.exc import IntegrityError
from src.database.models import Cliente, Credito, SocioComercial, EstadoCredito

def test_valid_cuil_dni_match(db_session):
    """
    Test that a valid matching CUIL and DNI (where DNI is contained in CUIL) is accepted.
    """
    cliente = Cliente(
        cuil="20340672926",
        documento="34067292",
        apellido="DOMINGUEZ",
        nombre="HUGO",
    )
    db_session.add(cliente)
    db_session.commit()
    
    # Assert successfully persisted
    db_client = db_session.query(Cliente).filter_by(cuil="20340672926").first()
    assert db_client is not None
    assert db_client.documento == "34067292"

def test_invalid_cuil_dni_mismatch(db_session):
    """
    Test that a mismatched CUIL and DNI raises a ValueError.
    """
    # Mismatch when setting document first
    with pytest.raises(ValueError, match="must be contained within CUIL"):
        cliente = Cliente(
            documento="12345678",
            cuil="20999999999",
            apellido="DOMINGUEZ",
            nombre="HUGO",
        )

    # Mismatch when setting CUIL first
    with pytest.raises(ValueError, match="must be contained within CUIL"):
        cliente = Cliente(
            cuil="20999999999",
            documento="12345678",
            apellido="DOMINGUEZ",
            nombre="HUGO",
        )


def test_credito_unique_constraint_id_externo_socio(db_session, dummy_cliente, dummy_socio):
    """
    Test that composite unique constraint on (id_externo, socio_originador_id) is enforced.
    """
    c1 = Credito(
        id_externo="EXT-100",
        cliente_cuil=dummy_cliente.cuil,
        socio_originador_id=dummy_socio.id,
        capital=1000.0,
        tna_c_iva=0.45,
        plazo=12,
        fecha_emision=date(2026, 6, 1),
        estado=EstadoCredito.ACTIVO
    )
    db_session.add(c1)
    db_session.commit()

    c2 = Credito(
        id_externo="EXT-100",
        cliente_cuil=dummy_cliente.cuil,
        socio_originador_id=dummy_socio.id,
        capital=2000.0,
        tna_c_iva=0.45,
        plazo=12,
        fecha_emision=date(2026, 6, 1),
        estado=EstadoCredito.ACTIVO
    )
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        db_session.commit()
