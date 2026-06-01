import pytest
from datetime import date
from src.database.models import (
    Credito,
    Cuota,
    EstadoCuota,
    EstadoCuotaCedida,
    TipoCredito,
    LiquidacionCuotaCedida,
    TipoLiquidacionEnum,
)
from src.logic.settlements import SettlementManager


@pytest.fixture
def test_credito_cedido(db_session, dummy_cliente, dummy_cartera):
    """
    Creates a test credit with 3 sold installments and corresponding settlements.
    """
    credito = Credito(
        cliente_cuil=dummy_cliente.cuil,
        cartera_id=dummy_cartera.id,
        capital=1000.00,
        tna_c_iva=0.60,
        plazo=3,
        fecha_emision=date(2026, 5, 10),
        tipo_credito=TipoCredito.FRANCES,
        dia_vencimiento=28,
    )
    db_session.add(credito)
    db_session.flush()

    c1 = Cuota(
        credito_id=credito.id,
        nro_cuota=1,
        fecha_vencimiento=date(2026, 6, 28),
        capital=100.00,
        interes=20.00,
        iva=4.20,
        estado=EstadoCuota.PENDIENTE,
        estado_cesion=EstadoCuotaCedida.PENDIENTE,
    )
    c2 = Cuota(
        credito_id=credito.id,
        nro_cuota=2,
        fecha_vencimiento=date(2026, 7, 28),
        capital=105.00,
        interes=15.00,
        iva=3.15,
        estado=EstadoCuota.PENDIENTE,
        estado_cesion=EstadoCuotaCedida.PENDIENTE,
    )
    c3 = Cuota(
        credito_id=credito.id,
        nro_cuota=3,
        fecha_vencimiento=date(2026, 8, 28),
        capital=110.00,
        interes=10.00,
        iva=2.10,
        estado=EstadoCuota.PENDIENTE,
        estado_cesion=EstadoCuotaCedida.PENDIENTE,
    )
    db_session.add_all([c1, c2, c3])
    db_session.flush()

    # Create uncancelled liquidations (settlements)
    liq1 = LiquidacionCuotaCedida(
        cuota_id=c1.id,
        cartera_id=dummy_cartera.id,
        tipo_liquidacion=TipoLiquidacionEnum.NORMAL,
        capital=100.00,
        interes=20.00,
        iva=4.20,
        cancelada=False,
    )
    liq2 = LiquidacionCuotaCedida(
        cuota_id=c2.id,
        cartera_id=dummy_cartera.id,
        tipo_liquidacion=TipoLiquidacionEnum.NORMAL,
        capital=105.00,
        interes=15.00,
        iva=3.15,
        cancelada=False,
    )
    liq3 = LiquidacionCuotaCedida(
        cuota_id=c3.id,
        cartera_id=dummy_cartera.id,
        tipo_liquidacion=TipoLiquidacionEnum.NORMAL,
        capital=110.00,
        interes=10.00,
        iva=2.10,
        cancelada=False,
    )
    db_session.add_all([liq1, liq2, liq3])
    db_session.commit()

    return credito, [c1, c2, c3], [liq1, liq2, liq3]


def test_canceled_settlements_all(db_session, test_credito_cedido):
    """
    Tests canceling all outstanding settlements by passing amount=0.
    """
    credito, cuotas, liqs = test_credito_cedido
    manager = SettlementManager(db_session)

    # Cancel all (amount=0)
    df_res = manager.canceled_settlements(fecha_pago=date(2026, 6, 28), amount=0)

    assert len(df_res) == 3

    # Reload from DB and verify
    db_session.expire_all()
    updated_liqs = db_session.query(LiquidacionCuotaCedida).all()
    assert len(updated_liqs) == 3
    assert all(l.cancelada for l in updated_liqs)
    assert all(l.fecha_pago == date(2026, 6, 28) for l in updated_liqs)

    updated_cuotas = (
        db_session.query(Cuota).filter(Cuota.credito_id == credito.id).all()
    )
    assert len(updated_cuotas) == 3
    assert all(c.estado_cesion == EstadoCuotaCedida.CANCELADA for c in updated_cuotas)


def test_canceled_settlements_partial(db_session, test_credito_cedido):
    """
    Tests canceling settlements partially by passing a positive amount.
    First settlement sum: 124.20.
    Second settlement sum: 123.15.
    Total: 247.35.
    If we pass amount = 150.00, it should cancel only the first one (124.20 < 150.00).
    The remaining amount will be 25.80, which is less than the second (123.15), so second and third are skipped.
    """
    credito, cuotas, liqs = test_credito_cedido
    manager = SettlementManager(db_session)

    # Cancel with amount=150.00
    df_res = manager.canceled_settlements(
        fecha_pago=date(2026, 6, 28), amount=150.00
    )

    assert len(df_res) == 3

    # Reload and verify
    db_session.expire_all()

    # First settlement should be canceled
    liq1_db = db_session.get(LiquidacionCuotaCedida, liqs[0].id)
    assert liq1_db.cancelada is True
    assert liq1_db.fecha_pago == date(2026, 6, 28)

    # Second and third should remain uncancelled
    liq2_db = db_session.get(LiquidacionCuotaCedida, liqs[1].id)
    assert liq2_db.cancelada is False
    assert liq2_db.fecha_pago is None

    liq3_db = db_session.get(LiquidacionCuotaCedida, liqs[2].id)
    assert liq3_db.cancelada is False
    assert liq3_db.fecha_pago is None

    # Verify Cuota assignment states
    c1_db = db_session.get(Cuota, cuotas[0].id)
    assert c1_db.estado_cesion == EstadoCuotaCedida.CANCELADA

    c2_db = db_session.get(Cuota, cuotas[1].id)
    assert c2_db.estado_cesion == EstadoCuotaCedida.PENDIENTE
