from datetime import date
import pytest
from src.logic.creditos.amortization import AmortizationEngine
from src.database.models import Cuota


def test_generate_french_schedule_standard():
    """
    Test a standard schedule generation.
    Checks that all returned items are Cuota instances, the plazo count is correct,
    and the sum of capital equals the original borrowed amount.
    """
    capital = 10000.00
    tna = 0.60
    plazo = 12
    fecha_emision = date(2026, 5, 10)
    
    schedule = AmortizationEngine.generate_french_schedule(
        credito_id=1,
        capital=capital,
        tna_c_iva=tna,
        plazo=plazo,
        fecha_emision=fecha_emision,
        dia_vencimiento=28,
    )
    
    assert len(schedule) == plazo
    assert all(isinstance(c, Cuota) for c in schedule)
    
    # Capital should sum up to exactly the original amount
    total_capital = sum(c.capital for c in schedule)
    assert round(total_capital, 2) == capital


def test_generate_french_schedule_rounding():
    """
    Test with odd capital and rates to check that the engine successfully
    reaches exactly zero balance at the final installment.
    """
    capital = 33333.33
    tna = 0.53421
    plazo = 5
    fecha_emision = date(2026, 5, 15)
    
    schedule = AmortizationEngine.generate_french_schedule(
        credito_id=1,
        capital=capital,
        tna_c_iva=tna,
        plazo=plazo,
        fecha_emision=fecha_emision,
        dia_vencimiento=28,
    )
    
    total_capital = sum(c.capital for c in schedule)
    assert round(total_capital, 2) == capital


def test_generate_french_schedule_forced_date_logic():
    """
    Test that the due dates of installments are forced correctly to the 28th
    of the target months.
    """
    capital = 50000.00
    tna = 0.45
    plazo = 3
    
    # Scenario A: fecha_emision day <= dia_corte (day 15 <= 28)
    # gracia will be decremented by 1 (default grace=2 becomes 1)
    # First installment should be emission + 1 + 1 month = emission + 2 months
    fecha_emision_a = date(2026, 5, 15)
    schedule_a = AmortizationEngine.generate_french_schedule(
        credito_id=1,
        capital=capital,
        tna_c_iva=tna,
        plazo=plazo,
        fecha_emision=fecha_emision_a,
        dia_vencimiento=28,
        gracia=2,
        dia_corte=28,
    )
    
    # May + (1 + 1) = July
    assert schedule_a[0].fecha_vencimiento == date(2026, 7, 28)
    assert schedule_a[1].fecha_vencimiento == date(2026, 8, 28)
    assert schedule_a[2].fecha_vencimiento == date(2026, 9, 28)
    
    # Scenario B: fecha_emision day > dia_corte (day 29 > 28)
    # gracia is kept at 2.
    # First installment should be emission + 2 + 1 month = emission + 3 months
    fecha_emision_b = date(2026, 5, 29)
    schedule_b = AmortizationEngine.generate_french_schedule(
        credito_id=1,
        capital=capital,
        tna_c_iva=tna,
        plazo=plazo,
        fecha_emision=fecha_emision_b,
        dia_vencimiento=28,
        gracia=2,
        dia_corte=28,
    )
    # May + (2 + 1) = August
    assert schedule_b[0].fecha_vencimiento == date(2026, 8, 28)


def test_originate_uses_gracia_from_tasa_y_comision(db_session, dummy_cliente, dummy_socio):
    """
    Verifica que TasaYComision.gracia diferencie grillas de un mismo socio originador
    y propague los meses de gracia al cronograma de cuotas al originar un crédito,
    además de verificar la idempotencia de ensure_tasas_comisiones_schema.
    """
    from src.database.models.socios import TasaYComision, ensure_tasas_comisiones_schema
    from src.logic.creditos.origination import LoanOriginator

    # 1. ensure_tasas_comisiones_schema debe ser idempotente sobre el schema actual
    bind_engine = db_session.get_bind()
    ensure_tasas_comisiones_schema(bind_engine)

    # 2. Dos grillas del mismo socio originador y mismo plazo con distinta gracia (2 vs 3 meses)
    tasa_g2 = TasaYComision(
        fecha=date(2026, 1, 1),
        socio_originador_id=dummy_socio.id,
        socio_intermediario_id=dummy_socio.id,
        plazo=6,
        gracia=2,
        tna_c_iva=0.50,
    )
    tasa_g3 = TasaYComision(
        fecha=date(2026, 1, 1),
        socio_originador_id=dummy_socio.id,
        socio_intermediario_id=dummy_socio.id,
        plazo=6,
        gracia=3,
        tna_c_iva=0.50,
    )
    db_session.add_all([tasa_g2, tasa_g3])
    db_session.commit()

    originator = LoanOriginator(db_session=db_session)
    cred_g2, _ = originator.originate(
        client_cuil=dummy_cliente.cuil,
        capital=10000.0,
        tna_c_iva=0.50,
        term=6,
        partner_id=dummy_socio.id,
        issuance_date=date(2026, 5, 15),
        due_day=28,
        comision_id=tasa_g2.id,
        strict_policy=False,
    )
    cred_g3, _ = originator.originate(
        client_cuil=dummy_cliente.cuil,
        capital=10000.0,
        tna_c_iva=0.50,
        term=6,
        partner_id=dummy_socio.id,
        issuance_date=date(2026, 5, 15),
        due_day=28,
        comision_id=tasa_g3.id,
        strict_policy=False,
    )

    cuotas_g2 = sorted(cred_g2.cuotas, key=lambda c: c.nro_cuota)
    cuotas_g3 = sorted(cred_g3.cuotas, key=lambda c: c.nro_cuota)

    # dummy_socio tiene dia_corte=28; fecha_emision=2026-05-15 <= 28 -> gracia efectiva = gracia - 1
    assert cuotas_g2[0].fecha_vencimiento == date(2026, 7, 28)
    assert cuotas_g3[0].fecha_vencimiento == date(2026, 8, 28)
