from datetime import date
import pytest
from src.database.models import Credito, Cuota, EstadoCuota, TipoCredito, Cobranza, TipoCobranzaEnum


@pytest.fixture
def test_credito_single_cuota(db_session, dummy_cliente, dummy_cartera):
    """
    Provides a credit with exactly one installment.
    """
    credito = Credito(
        cliente_cuil=dummy_cliente.cuil,
        cartera_id=dummy_cartera.id,
        capital=120.00,
        tna_c_iva=0.00,
        plazo=1,
        fecha_emision=date(2026, 5, 10),
        tipo_credito=TipoCredito.FRANCES,
        dia_vencimiento=28,
    )
    db_session.add(credito)
    db_session.flush()

    cuota = Cuota(
        credito_id=credito.id,
        nro_cuota=1,
        fecha_vencimiento=date(2026, 6, 28),
        capital=100.00,
        interes=20.00,
        iva=4.20,
        estado=EstadoCuota.PENDIENTE,
    )
    db_session.add(cuota)
    db_session.commit()
    return credito, cuota


def test_auto_adjust_rounding_error_within_threshold(db_session, test_credito_single_cuota):
    """
    Tests that a payment leaving a difference of $0.02 (under $0.05 threshold)
    triggers the automatic creation of a correcting AJUSTE collection and cancels the installment.
    """
    credito, cuota = test_credito_single_cuota
    
    # We pay 124.18 instead of 124.20. Difference is 0.02.
    cobranza = Cobranza(
        cuota_id=cuota.id,
        tipo_cobranza=TipoCobranzaEnum.COMUN.value,
        capital=99.98,  # $0.02 short
        interes=20.00,
        iva=4.20,
        fecha=date(2026, 6, 28)
    )
    db_session.add(cobranza)
    
    # Trigger flush (before_flush event listener will execute here)
    db_session.flush()
    
    # Assertions:
    # 1. A new AJUSTE Cobranza should have been appended automatically
    all_cobr = db_session.query(Cobranza).filter_by(cuota_id=cuota.id).all()
    assert len(all_cobr) == 2
    
    ajuste_cobr = [c for c in all_cobr if c.tipo_cobranza == TipoCobranzaEnum.AJUSTE][0]
    assert ajuste_cobr.capital == 0.02
    assert ajuste_cobr.interes == 0.00
    assert ajuste_cobr.iva == 0.00
    
    # 2. Cuota state must now be CANCELADA
    assert cuota.estado == EstadoCuota.CANCELADA


def test_auto_adjust_rounding_error_outside_threshold(db_session, test_credito_single_cuota):
    """
    Tests that a payment leaving a difference of $0.10 (over $0.05 threshold)
    does NOT trigger automatic adjustment and the installment remains PENDIENTE.
    """
    credito, cuota = test_credito_single_cuota
    
    # We pay 124.10 instead of 124.20. Difference is 0.10.
    cobranza = Cobranza(
        cuota_id=cuota.id,
        tipo_cobranza=TipoCobranzaEnum.COMUN.value,
        capital=99.90,  # $0.10 short
        interes=20.00,
        iva=4.20,
        fecha=date(2026, 6, 28)
    )
    db_session.add(cobranza)
    
    db_session.flush()
    
    # Assertions:
    # 1. Only our single payment should be present
    all_cobr = db_session.query(Cobranza).filter_by(cuota_id=cuota.id).all()
    assert len(all_cobr) == 1
    
    # 2. Cuota state must still be PENDIENTE
    assert cuota.estado == EstadoCuota.PENDIENTE
