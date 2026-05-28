import os
import tempfile
from datetime import date
import pytest
import pandas as pd
from src.database.models import Credito, Cuota, EstadoCuota, TipoCredito, Cobranza, TipoCobranzaEnum
from src.logic.collections import CollectionManager


@pytest.fixture
def test_credito(db_session, dummy_cliente, dummy_cartera):
    """
    Creates a test credit with 3 installments.
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

    # Cuota 1
    c1 = Cuota(
        credito_id=credito.id,
        nro_cuota=1,
        fecha_vencimiento=date(2026, 6, 28),
        capital=100.00,
        interes=20.00,
        iva=4.20, # 21% of 20.00
        estado=EstadoCuota.PENDIENTE,
    )
    # Cuota 2
    c2 = Cuota(
        credito_id=credito.id,
        nro_cuota=2,
        fecha_vencimiento=date(2026, 7, 28),
        capital=105.00,
        interes=15.00,
        iva=3.15,
        estado=EstadoCuota.PENDIENTE,
    )
    # Cuota 3
    c3 = Cuota(
        credito_id=credito.id,
        nro_cuota=3,
        fecha_vencimiento=date(2026, 8, 28),
        capital=110.00,
        interes=10.00,
        iva=2.10,
        estado=EstadoCuota.PENDIENTE,
    )
    db_session.add_all([c1, c2, c3])
    db_session.commit()
    return credito


def test_process_standard_payment_exact(db_session, test_credito):
    """
    Tests paying exactly the amount of the first installment (124.20).
    """
    manager = CollectionManager(db_session)
    df_res = manager.process_standard_payment(
        identificador="CREDITO_ID",
        id_val=test_credito.id,
        amount=124.20,
        payment_date=date(2026, 6, 28),
    )
    
    # Assertions
    assert not df_res.empty
    
    # Reload installments to verify states
    cuotas = db_session.query(Cuota).filter_by(credito_id=test_credito.id).order_by(Cuota.nro_cuota).all()
    assert cuotas[0].estado == EstadoCuota.CANCELADA
    assert cuotas[1].estado == EstadoCuota.PENDIENTE
    assert cuotas[2].estado == EstadoCuota.PENDIENTE


def test_process_standard_payment_partial(db_session, test_credito):
    """
    Tests partial payment. Amount 50.00.
    Should cover:
    - IVA: 4.20
    - Interest: 20.00
    - Capital: 25.80
    """
    manager = CollectionManager(db_session)
    df_res = manager.process_standard_payment(
        identificador="CREDITO_ID",
        id_val=test_credito.id,
        amount=50.00,
        payment_date=date(2026, 6, 28),
    )
    
    assert not df_res.empty
    
    # Verify the created collection in DB
    cobranzas = db_session.query(Cobranza).join(Cuota).filter(Cuota.credito_id == test_credito.id).all()
    assert len(cobranzas) == 1
    c = cobranzas[0]
    assert c.iva == 4.20
    assert c.interes == 20.00
    assert c.capital == 25.80
    assert c.tipo_cobranza == TipoCobranzaEnum.COMUN


def test_process_standard_payment_overpayment_penalty(db_session, test_credito):
    """
    Tests paying more than the total outstanding debt.
    Debt is 124.20 + 123.15 + 122.10 = 369.45.
    If amount is 400.00, it should cover all installments and create a PENALTY
    credit of 30.55 for the client.
    """
    manager = CollectionManager(db_session)
    df_res = manager.process_standard_payment(
        identificador="CREDITO_ID",
        id_val=test_credito.id,
        amount=400.00,
        payment_date=date(2026, 6, 28),
    )
    
    assert not df_res.empty
    
    # All original installments should be cancelled
    cuotas = db_session.query(Cuota).filter_by(credito_id=test_credito.id).all()
    assert all(c.estado == EstadoCuota.CANCELADA for c in cuotas)
    
    # Verify penalty credit creation
    penalties = db_session.query(Credito).filter_by(
        cliente_cuil=test_credito.cliente_cuil,
        tipo_credito=TipoCredito.PENALTY.value
    ).all()
    assert len(penalties) == 1
    penalty_credit = penalties[0]
    
    # Verify the penalty installment
    penalty_cuota = db_session.query(Cuota).filter_by(credito_id=penalty_credit.id).first()
    assert penalty_cuota is not None
    assert penalty_cuota.estado == EstadoCuota.CANCELADA
    
    # Sum of capital + interest + iva in penalty cuota should equal the leftover (30.55)
    total_penalty = round(penalty_cuota.capital + penalty_cuota.interes + penalty_cuota.iva, 2)
    assert total_penalty == 30.55


def test_process_early_cancellation(db_session, test_credito):
    """
    Tests early cancellation. It waives interest for future installments.
    Standard payment on 2026-06-28:
    Cuota 1 is already due, so interest (20) + IVA (4.20) + Capital (100) are paid = 124.20.
    Cuota 2 and 3 are future, so their interest/IVA are waived, paying only capital (105 + 110 = 215).
    Total early cancellation amount to pay = 124.20 + 215.00 = 339.20.
    """
    manager = CollectionManager(db_session)
    df_res = manager.process_early_cancellation(
        identificador="CREDITO_ID",
        id_val=test_credito.id,
        amount=339.20,
        payment_date=date(2026, 6, 28),
    )
    
    assert not df_res.empty
    
    # All installments should be CANCELADA
    cuotas = db_session.query(Cuota).filter_by(credito_id=test_credito.id).order_by(Cuota.nro_cuota).all()
    assert all(c.estado == EstadoCuota.CANCELADA for c in cuotas)
    
    # Verify collections
    # Cuota 1: COMUN (124.20)
    # Cuota 2: CA (105.00 capital only, 0 interest, 0 iva)
    # Cuota 3: CA (110.00 capital only, 0 interest, 0 iva)
    c1_cobr = db_session.query(Cobranza).filter_by(cuota_id=cuotas[0].id).one()
    assert c1_cobr.tipo_cobranza == TipoCobranzaEnum.COMUN
    assert c1_cobr.capital == 100.00
    assert c1_cobr.interes == 20.00
    
    # For Cuota 2: expect a CA payment for capital and a BCA bonus for interest/IVA
    c2_ca = db_session.query(Cobranza).filter_by(cuota_id=cuotas[1].id, tipo_cobranza=TipoCobranzaEnum.CA).one()
    assert c2_ca.capital == 105.00
    assert c2_ca.interes == 0.00
    assert c2_ca.iva == 0.00

    c2_bca = db_session.query(Cobranza).filter_by(cuota_id=cuotas[1].id, tipo_cobranza=TipoCobranzaEnum.BCA).one()
    assert c2_bca.capital == 0.00
    assert c2_bca.interes == 15.00
    assert c2_bca.iva == 3.15


def test_process_massive_collection_atomic_rollback(db_session, test_credito):
    """
    Tests that a massive collection rollbacks the entire session if there is an error.
    Excel columns: A (CREDITO_ID), B (monto)
    Row 1: test_credito.id, 124.20 (Valid)
    Row 2: 99999, 50.00 (Invalid - non-existent credit ID)
    """
    # 1. Create a temporary Excel file
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    try:
        # Write columns without header
        df_excel = pd.DataFrame([
            [test_credito.id, 124.20],
            [99999, 50.00]
        ])
        
        # Save using openpyxl (requires no headers, so we set header=False, index=False)
        # Note: process_massive_collection will load A, B columns and rename them to ident, monto.
        # Since we use usecols="A,B", we need to write standard Excel columns.
        df_excel.to_excel(path, header=False, index=False)
        
        # 2. Call the manager
        manager = CollectionManager(db_session)
        
        # Expecting a ValueError due to invalid row
        with pytest.raises(ValueError) as excinfo:
            manager.process_massive_collection(
                identificador="CREDITO_ID",
                id_column="A",
                amount_column="B",
                payment_date=date(2026, 6, 28),
                path=path,
            )
            
        assert "Se encontraron problemas al procesar las siguientes filas" in str(excinfo.value)
        
        # 3. Verify rollback: Cuota 1 should STILL be PENDIENTE (no partial commit occurred)
        cuota1 = db_session.query(Cuota).filter_by(credito_id=test_credito.id, nro_cuota=1).one()
        assert cuota1.estado == EstadoCuota.PENDIENTE
        
        cobranzas = db_session.query(Cobranza).all()
        assert len(cobranzas) == 0
        
    finally:
        if os.path.exists(path):
            os.remove(path)
